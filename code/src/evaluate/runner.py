"""End-to-end benchmark evaluation runner."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.evaluate.costs import build_cost_payload
from src.evaluate.dataset_loader import load_evaluate_entries, select_entry_fields
from src.evaluate.metric_runner import build_validation_metrics
from src.evaluate.run_io import (
    build_initial_run_metadata,
    build_raw_result_entry,
    ensure_evaluate_run_dir,
    get_benchmark_raw_output_path,
    get_benchmark_summary_output_path,
)
from src.evaluate.summary import build_benchmark_summary
from src.evaluate.sparql_extraction import extract_sparql_query
from src.query.inference_session import (
    generate_response_with_session,
    prepare_inference_session,
)
from src.query.prompt_builder import (
    append_ace_context_to_prompt,
    build_final_prompt_for_question,
)
from src.sparql.execution import detect_sparql_query_type, execute_sparql_query
from src.sparql.prefixes import prepend_orkg_prefixes

from tools.pgmr.evaluate_model_outputs import postprocess_pgmr_query
from tools.pgmr.restore_and_execute_predictions import (
    build_entry_mapping,
    detect_basic_query_status,
    load_memory_mapping,
    restore_pgmr_query,
)
from pathlib import Path
from src.evaluate.kg_memory import load_allowed_orkg_refs


SUPPORTED_QUERY_FORMS = {"select", "ask"}

ENTRY_METADATA_FIELDS = (
    "id",
    "uid",
    "source_id",
    "source_dataset",
    "family",
    "split",
    "language",
    "query_type",
    "special_types",
    "answer_type",
    "query_shape",
    "number_of_patterns",
    "query_components",
    "complexity_level",
    "ambiguity_risk",
    "lexical_gap_risk",
    "hallucination_risk",
    "human_or_generated",
    "review_status",
    "gold_status",
)


def _format_prompt_value(value: Any) -> str:
    if value is None:
        return "none"

    if isinstance(value, list):
        values = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(values) if values else "none"

    text = str(value).strip()
    return text if text else "none"


def _build_pgmr_lite_meta_prompt(entry: dict[str, Any]) -> str:
    """Build the compact metadata prompt used by pgmr_lite_meta runs."""
    return (
        "task: text_to_pgmr_sparql\n"
        f"family: {_format_prompt_value(entry.get('family'))}\n"
        f"answer_type: {_format_prompt_value(entry.get('answer_type'))}\n"
        f"query_shape: {_format_prompt_value(entry.get('query_shape'))}\n"
        f"special_types: {_format_prompt_value(entry.get('special_types'))}\n"
        f"complexity_level: {_format_prompt_value(entry.get('complexity_level'))}\n"
        f"question: {_format_prompt_value(entry.get('question'))}\n"
        "pgmr_sparql:"
    )


def _aggregate_costs(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate token/cost payloads stored on per-example results."""
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_total_tokens = 0
    total_cached_tokens = 0
    total_estimated_cost_usd = 0.0
    priced_items = 0

    for result in results:
        cost_payload = result.get("cost") or {}
        usage = cost_payload.get("usage") or {}

        total_prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        total_completion_tokens += int(usage.get("completion_tokens", 0) or 0)
        total_total_tokens += int(usage.get("total_tokens", 0) or 0)
        total_cached_tokens += int(usage.get("cached_tokens", 0) or 0)

        estimated_cost_usd = cost_payload.get("estimated_cost_usd")
        if isinstance(estimated_cost_usd, (int, float)):
            total_estimated_cost_usd += float(estimated_cost_usd)
            priced_items += 1

    return {
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_total_tokens,
        "total_cached_tokens": total_cached_tokens,
        "total_estimated_cost_usd": round(total_estimated_cost_usd, 6),
        "priced_items": priced_items,
        "mean_cost_per_priced_item_usd": (
            round(total_estimated_cost_usd / priced_items, 6)
            if priced_items > 0
            else None
        ),
    }


def _prepare_and_execute_query(
    query: str | None,
    endpoint_url: str | None,
) -> tuple[str | None, dict[str, Any]]:
    """Prepare prefixes, detect query form, and optionally execute a query."""
    if not isinstance(query, str) or not query.strip():
        return None, {
            "status": "skipped",
            "reason": "no_query",
        }

    try:
        query_with_prefixes = prepend_orkg_prefixes(query)
        query_form = detect_sparql_query_type(query_with_prefixes)
    except Exception as exc:
        return None, {
            "status": "error",
            "error": f"query_preparation_failed: {exc}",
        }

    if not endpoint_url:
        return query_form, {
            "status": "skipped",
            "reason": "no_endpoint_configured",
            "result_type": query_form,
            "query_with_prefixes": query_with_prefixes,
        }

    if query_form not in SUPPORTED_QUERY_FORMS:
        return query_form, {
            "status": "skipped",
            "reason": f"unsupported_query_type:{query_form}",
            "result_type": query_form,
            "query_with_prefixes": query_with_prefixes,
        }

    try:
        response_json = execute_sparql_query(
            query=query_with_prefixes,
            endpoint_url=endpoint_url,
        )
        return query_form, {
            "status": "ok",
            "result_type": query_form,
            "query_with_prefixes": query_with_prefixes,
            "response_json": response_json,
        }
    except Exception as exc:
        return query_form, {
            "status": "error",
            "error": str(exc),
            "result_type": query_form,
            "query_with_prefixes": query_with_prefixes,
        }


def _build_prediction_query_from_model_output(
    *,
    raw_model_output: str,
    entry: dict[str, Any],
    prediction_format: str,
    pgmr_memory_mapping: dict[str, str] | None,
) -> dict[str, Any]:
    """Convert raw model text into the query that should be evaluated."""
    if prediction_format != "pgmr_lite":
        extracted_query = extract_sparql_query(raw_model_output)
        return {
            "extracted_query": extracted_query,
            "has_extracted_query": extracted_query is not None,
            "extraction_status": "ok" if extracted_query is not None else "empty",
            "pgmr_postprocessed_query": None,
            "pgmr_restored_query": None,
            "pgmr_restore_status": None,
            "pgmr_missing_mapping_tokens": [],
            "pgmr_remaining_tokens": [],
            "pgmr_basic_status": None,
        }

    pgmr_postprocessed_query = postprocess_pgmr_query(raw_model_output)

    # PGMR-lite predictions must be restored before SPARQL execution/metrics.
    entry_mapping = build_entry_mapping(entry, pgmr_memory_mapping or {})
    pgmr_restored_query, pgmr_missing_mapping_tokens = restore_pgmr_query(
        pgmr_postprocessed_query,
        entry_mapping,
    )
    pgmr_restored_query = postprocess_pgmr_query(pgmr_restored_query)

    pgmr_basic_status = detect_basic_query_status(pgmr_restored_query)
    pgmr_remaining_tokens = pgmr_basic_status.get("remaining_pgmr_tokens", [])

    if pgmr_missing_mapping_tokens:
        pgmr_restore_status = "missing_mapping"
    elif pgmr_remaining_tokens:
        pgmr_restore_status = "remaining_pgmr_tokens"
    else:
        pgmr_restore_status = "ok"

    extracted_query = pgmr_restored_query if pgmr_restore_status == "ok" else None

    return {
        "extracted_query": extracted_query,
        "has_extracted_query": extracted_query is not None,
        "extraction_status": f"pgmr_restore:{pgmr_restore_status}",
        "pgmr_postprocessed_query": pgmr_postprocessed_query,
        "pgmr_restored_query": pgmr_restored_query,
        "pgmr_restore_status": pgmr_restore_status,
        "pgmr_missing_mapping_tokens": pgmr_missing_mapping_tokens,
        "pgmr_remaining_tokens": pgmr_remaining_tokens,
        "pgmr_basic_status": pgmr_basic_status,
    }


def execute_evaluate_task(args: argparse.Namespace) -> int:
    """Run model inference, execution, metrics, and report writing."""
    print("Running evaluation task with args:", args)

    prediction_format = getattr(args, "prediction_format", "sparql")

    entries = load_evaluate_entries(
        dataset_path=args.dataset,
        limit=args.limit,
    )

    run_dir = ensure_evaluate_run_dir(
        model_name=args.model,
        dataset_path=args.dataset,
        prompt_mode=args.prompt_mode,
    )

    output_path = get_benchmark_raw_output_path(run_dir)
    summary_output_path = get_benchmark_summary_output_path(run_dir)
    started_at_utc = datetime.now(timezone.utc).isoformat()

    run_metadata = build_initial_run_metadata(
        model_name=args.model,
        dataset_path=args.dataset,
        prompt_mode=args.prompt_mode,
        requested_limit=args.limit,
        run_dir=run_dir,
        output_path=output_path,
        started_at_utc=started_at_utc,
        total_items=len(entries),
        summary_output_path=summary_output_path,
    )
    run_metadata["prediction_format"] = prediction_format
    if getattr(args, "ace_playbook", None) or getattr(args, "ace_playbook_dir", None):
        run_metadata["ace"] = {
            "playbook_path": getattr(args, "ace_playbook", None),
            "playbook_dir": getattr(args, "ace_playbook_dir", None),
            "mode": getattr(args, "ace_mode", None),
            "max_bullets": getattr(args, "ace_max_bullets", 0),
        }


    if prediction_format == "pgmr_lite":
        run_metadata["pgmr_memory_dir"] = getattr(
            args,
            "pgmr_memory_dir",
            "code/data/orkg_memory/templates",
        )

    print(f"Run directory: {run_dir}\n")
    print(f"Raw benchmark output path: {output_path}\n")
    print(f"Run metadata: {run_metadata}\n")
    print(f"Loaded entries for this run: {len(entries)}\n")

    inference_session = prepare_inference_session(args.model)

    pgmr_memory_mapping: dict[str, str] | None = None

    if prediction_format == "pgmr_lite":
        pgmr_memory_mapping = load_memory_mapping(Path(args.pgmr_memory_dir))
        print(f"PGMR memory mappings loaded: {len(pgmr_memory_mapping)}")

    print(f"Inference provider: {inference_session['provider']}\n")

    results: list[dict[str, Any]] = []

    # Local KG memory provides the allowlist for URI hallucination checks.
    kg_memory_path = Path(
    getattr(args, "kg_memory_path", "code/data/orkg_memory/templates")
)

    allowed_kg_refs = None
    if kg_memory_path.exists():
        kg_memory = load_allowed_orkg_refs(kg_memory_path)
        allowed_kg_refs = kg_memory["all_refs"]
    else:
        print(
            f"Warning: KG memory path not found: {kg_memory_path}. "
            "URI hallucination metric will be marked as not comparable."
        )

    for index, entry in enumerate(entries, start=1):
        selected = select_entry_fields(
            entry,
            ["id", "uid", "family", "question", "gold_sparql"],
        )
        entry_metadata = select_entry_fields(entry, ENTRY_METADATA_FIELDS)

        entry_id = str(selected.get("id") or selected.get("uid") or f"item_{index}")
        question = selected["question"]
        gold_query = selected["gold_sparql"]
        family = selected["family"]

        if args.prompt_mode == "pgmr_lite_meta":
            final_prompt = _build_pgmr_lite_meta_prompt(entry)
            final_prompt = append_ace_context_to_prompt(
                prompt=final_prompt,
                family=family,
                prompt_mode=args.prompt_mode,
                ace_playbook_path=getattr(args, "ace_playbook", None),
                ace_playbook_dir=getattr(args, "ace_playbook_dir", None),
                ace_mode=getattr(args, "ace_mode", None),
                ace_max_bullets=getattr(args, "ace_max_bullets", 0),
                model_name=getattr(args, "model", None),
            )
        else:
            final_prompt = build_final_prompt_for_question(
                question=question,
                prompt_mode=args.prompt_mode,
                family=family,
                ace_playbook_path=getattr(args, "ace_playbook", None),
                ace_playbook_dir=getattr(args, "ace_playbook_dir", None),
                ace_mode=getattr(args, "ace_mode", None),
                ace_max_bullets=getattr(args, "ace_max_bullets", 0),
                model_name=getattr(args, "model", None),
            )

        response_started_at = datetime.now(timezone.utc)
        model_response = generate_response_with_session(
            session=inference_session,
            final_prompt=final_prompt,
        )
        response_finished_at = datetime.now(timezone.utc)

        if isinstance(model_response, dict):
            raw_model_output = str(model_response.get("text", "")).strip()
            model_usage = model_response.get("usage")
        else:
            raw_model_output = str(model_response).strip()
            model_usage = None

        response_time_seconds = (
            response_finished_at - response_started_at
        ).total_seconds()

        cost_payload = build_cost_payload(
            provider=inference_session["provider"],
            model_name=inference_session["model_config"].get("model_id", args.model),
            usage=model_usage,
        )

        prediction_payload = _build_prediction_query_from_model_output(
            raw_model_output=raw_model_output,
            entry=entry,
            prediction_format=prediction_format,
            pgmr_memory_mapping=pgmr_memory_mapping,
        )

        extracted_query = prediction_payload["extracted_query"]
        has_extracted_query = prediction_payload["has_extracted_query"]
        extraction_status = prediction_payload["extraction_status"]

        prediction_query_form, query_execution = _prepare_and_execute_query(
            query=extracted_query,
            endpoint_url=args.sparql_endpoint,
        )
        gold_query_form, gold_execution = _prepare_and_execute_query(
            query=gold_query,
            endpoint_url=args.sparql_endpoint,
        )

        prompt_mode = str(getattr(args, "prompt_mode", "") or "").lower()
        prediction_format = str(getattr(args, "prediction_format", "") or "").lower()

        enable_pgmr_metrics = (
            prompt_mode == "pgmr"
            or "pgmr" in prompt_mode
            or "pgmr" in prediction_format
        )

        validation = build_validation_metrics(
            has_extracted_query=has_extracted_query,
            prediction_query_form=prediction_query_form,
            gold_query_form=gold_query_form,
            prediction_execution=query_execution,
            gold_execution=gold_execution,
            endpoint_url=args.sparql_endpoint,
            prediction_query=extracted_query,
            gold_query=gold_query,
            allowed_kg_refs=allowed_kg_refs,
            enable_pgmr_metrics=enable_pgmr_metrics,
        )

        result_entry = build_raw_result_entry(
            entry_id=entry_id,
            question=question,
            gold_query=gold_query,
        )
        result_entry["entry_metadata"] = entry_metadata
        result_entry["prediction_format"] = prediction_format
        result_entry["raw_model_output"] = raw_model_output
        result_entry["extracted_query"] = extracted_query
        result_entry["has_extracted_query"] = has_extracted_query
        result_entry["extraction_status"] = extraction_status

        result_entry["pgmr_postprocessed_query"] = prediction_payload[
            "pgmr_postprocessed_query"
        ]
        result_entry["pgmr_restored_query"] = prediction_payload[
            "pgmr_restored_query"
        ]
        result_entry["pgmr_restore_status"] = prediction_payload[
            "pgmr_restore_status"
        ]
        result_entry["pgmr_missing_mapping_tokens"] = prediction_payload[
            "pgmr_missing_mapping_tokens"
        ]
        result_entry["pgmr_remaining_tokens"] = prediction_payload[
            "pgmr_remaining_tokens"
        ]
        result_entry["pgmr_basic_status"] = prediction_payload[
            "pgmr_basic_status"
        ]

        result_entry["response_time_seconds"] = round(response_time_seconds, 4)
        result_entry["prediction_query_form"] = prediction_query_form
        result_entry["gold_query_form"] = gold_query_form
        result_entry["query_execution"] = query_execution
        result_entry["gold_execution"] = gold_execution
        result_entry["validation"] = validation
        result_entry["model_usage"] = model_usage
        result_entry["cost"] = cost_payload

        results.append(result_entry)

        print(
            f"[{index}/{len(entries)}] "
            f"id={entry_id} "
            f"family={family} "
            f"prompt_chars={len(final_prompt)} "
            f"extraction={extraction_status} "
            f"pred_form={prediction_query_form} "
            f"pred_exec={query_execution.get('status')} "
            f"gold_form={gold_query_form} "
            f"gold_exec={gold_execution.get('status')}"
        )

        output_path.write_text(
            json.dumps(
                {
                    "run_metadata": run_metadata,
                    "results": results,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    finished_at_utc = datetime.now(timezone.utc).isoformat()
    run_metadata["finished_at_utc"] = finished_at_utc
    run_metadata["completed_items"] = len(results)

    cost_summary = _aggregate_costs(results)
    run_metadata["cost_summary"] = cost_summary

    raw_payload = {
        "run_metadata": run_metadata,
        "results": results,
    }
    output_path.write_text(
        json.dumps(raw_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary_body = build_benchmark_summary(results)
    summary_body["costs"] = cost_summary

    summary_payload = {
        "run_metadata": run_metadata,
        "summary": summary_body,
    }
    summary_output_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Collected result entries: {len(results)}")
    print(f"Saved summary payload to: {summary_output_path}")
    print(f"Saved raw benchmark payload to: {output_path}")
    return 0
