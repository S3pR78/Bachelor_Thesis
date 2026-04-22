from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from src.evaluate.answer_metrics import (
    compute_answer_exact_match,
    compute_answer_precision_recall_f1,
)
from src.evaluate.dataset_loader import load_evaluate_entries, select_entry_fields
from src.evaluate.run_io import (
    build_initial_run_metadata,
    build_raw_result_entry,
    ensure_evaluate_run_dir,
    get_benchmark_raw_output_path,
)
from src.evaluate.sparql_extraction import extract_sparql_query
from src.query.inference_session import (
    generate_response_with_session,
    prepare_inference_session,
)
from src.query.prompt_builder import build_final_prompt_for_question
from src.sparql.execution import detect_sparql_query_type, execute_sparql_query
from src.sparql.prefixes import prepend_orkg_prefixes

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


def _round_metric_payload(metric_payload: dict[str, Any]) -> dict[str, Any]:
    rounded = dict(metric_payload)
    for key in ("value", "precision", "recall", "f1"):
        value = rounded.get(key)
        if isinstance(value, (int, float)):
            rounded[key] = round(float(value), 4)
    return rounded


def _build_binary_metric(
    metric_name: str,
    metric_type: str,
    comparable: bool,
    value: float | None,
    reason: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metric": metric_name,
        "type": metric_type,
        "comparable": comparable,
        "value": round(float(value), 4) if value is not None else None,
    }
    if reason is not None:
        payload["reason"] = reason
    payload.update(extra)
    return payload


def _prepare_and_execute_query(
    query: str | None,
    endpoint_url: str | None,
) -> tuple[str | None, dict[str, Any]]:
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


def _derive_primary_error_category(
    has_extracted_query: bool,
    prediction_query_form: str | None,
    gold_query_form: str | None,
    prediction_execution: dict[str, Any],
    gold_execution: dict[str, Any],
    exact_match_metric: dict[str, Any],
    endpoint_url: str | None,
) -> str | None:
    if not has_extracted_query:
        return "extraction_failure"

    if prediction_query_form not in SUPPORTED_QUERY_FORMS:
        return "unsupported_query_form"

    if not endpoint_url:
        return "not_evaluated_no_endpoint"

    if gold_query_form is None:
        return "gold_query_missing"

    if gold_query_form not in SUPPORTED_QUERY_FORMS:
        return "gold_query_form_unsupported"

    if gold_execution.get("status") == "error":
        return "gold_execution_error"

    if prediction_execution.get("status") == "error":
        return "prediction_execution_error"

    if prediction_execution.get("status") != "ok":
        return "prediction_not_executed"

    if gold_execution.get("status") != "ok":
        return "gold_not_executed"

    if exact_match_metric.get("comparable") and exact_match_metric.get("value") == 0.0:
        return "answer_mismatch"

    return None


def _build_validation_block(
    *,
    has_extracted_query: bool,
    prediction_query_form: str | None,
    gold_query_form: str | None,
    prediction_execution: dict[str, Any],
    gold_execution: dict[str, Any],
    endpoint_url: str | None,
) -> dict[str, Any]:
    query_extracted_metric = _build_binary_metric(
        metric_name="query_extracted",
        metric_type="structural",
        comparable=True,
        value=1.0 if has_extracted_query else 0.0,
    )

    if has_extracted_query:
        supported_query_form_metric = _build_binary_metric(
            metric_name="supported_query_form",
            metric_type="structural",
            comparable=True,
            value=1.0 if prediction_query_form in SUPPORTED_QUERY_FORMS else 0.0,
            prediction_query_form=prediction_query_form,
        )
    else:
        supported_query_form_metric = _build_binary_metric(
            metric_name="supported_query_form",
            metric_type="structural",
            comparable=False,
            value=None,
            reason="no_extracted_query",
            prediction_query_form=prediction_query_form,
        )

    if prediction_query_form is not None and gold_query_form is not None:
        query_form_match_metric = _build_binary_metric(
            metric_name="query_form_match",
            metric_type="structural",
            comparable=True,
            value=1.0 if prediction_query_form == gold_query_form else 0.0,
            prediction_query_form=prediction_query_form,
            gold_query_form=gold_query_form,
        )
    else:
        query_form_match_metric = _build_binary_metric(
            metric_name="query_form_match",
            metric_type="structural",
            comparable=False,
            value=None,
            reason="missing_query_form",
            prediction_query_form=prediction_query_form,
            gold_query_form=gold_query_form,
        )

    prediction_execution_comparable = bool(
        endpoint_url and has_extracted_query and prediction_query_form in SUPPORTED_QUERY_FORMS
    )
    if prediction_execution_comparable:
        prediction_execution_success_metric = _build_binary_metric(
            metric_name="prediction_execution_success",
            metric_type="execution_based",
            comparable=True,
            value=1.0 if prediction_execution.get("status") == "ok" else 0.0,
            execution_status=prediction_execution.get("status"),
        )
    else:
        reason = (
            "no_endpoint_configured"
            if not endpoint_url
            else "unsupported_or_missing_prediction_query"
        )
        prediction_execution_success_metric = _build_binary_metric(
            metric_name="prediction_execution_success",
            metric_type="execution_based",
            comparable=False,
            value=None,
            reason=reason,
            execution_status=prediction_execution.get("status"),
        )

    gold_execution_comparable = bool(
        endpoint_url and gold_query_form in SUPPORTED_QUERY_FORMS
    )
    if gold_execution_comparable:
        gold_execution_success_metric = _build_binary_metric(
            metric_name="gold_execution_success",
            metric_type="execution_based",
            comparable=True,
            value=1.0 if gold_execution.get("status") == "ok" else 0.0,
            execution_status=gold_execution.get("status"),
        )
    else:
        reason = (
            "no_endpoint_configured"
            if not endpoint_url
            else "unsupported_or_missing_gold_query"
        )
        gold_execution_success_metric = _build_binary_metric(
            metric_name="gold_execution_success",
            metric_type="execution_based",
            comparable=False,
            value=None,
            reason=reason,
            execution_status=gold_execution.get("status"),
        )

    exact_match_metric = _round_metric_payload(
        compute_answer_exact_match(
            prediction_execution=prediction_execution,
            gold_execution=gold_execution,
        )
    )

    prf1_metric = _round_metric_payload(
        compute_answer_precision_recall_f1(
            prediction_execution=prediction_execution,
            gold_execution=gold_execution,
        )
    )

    primary_error_category = _derive_primary_error_category(
        has_extracted_query=has_extracted_query,
        prediction_query_form=prediction_query_form,
        gold_query_form=gold_query_form,
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
        exact_match_metric=exact_match_metric,
        endpoint_url=endpoint_url,
    )

    return {
        "query_extracted": query_extracted_metric,
        "supported_query_form": supported_query_form_metric,
        "query_form_match": query_form_match_metric,
        "prediction_execution_success": prediction_execution_success_metric,
        "gold_execution_success": gold_execution_success_metric,
        "answer_exact_match": exact_match_metric,
        "answer_precision_recall_f1": prf1_metric,
        "primary_error_category": primary_error_category,
    }


def execute_evaluate_task(args: argparse.Namespace) -> int:
    print("Running evaluation task with args:", args)

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
    )

    print(f"Run directory: {run_dir}\n")
    print(f"Raw benchmark output path: {output_path}\n")
    print(f"Run metadata: {run_metadata}\n")
    print(f"Loaded entries for this run: {len(entries)}\n")

    inference_session = prepare_inference_session(args.model)
    print(f"Inference provider: {inference_session['provider']}\n")

    results = []

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

        final_prompt = build_final_prompt_for_question(
            question=question,
            prompt_mode=args.prompt_mode,
            family=family,
        )

        response_started_at = datetime.now(timezone.utc)
        raw_model_output = generate_response_with_session(
            session=inference_session,
            final_prompt=final_prompt,
        )
        response_finished_at = datetime.now(timezone.utc)
        response_time_seconds = (
            response_finished_at - response_started_at
        ).total_seconds()

        extracted_query = extract_sparql_query(raw_model_output)
        has_extracted_query = extracted_query is not None
        extraction_status = "ok" if has_extracted_query else "empty"

        prediction_query_form, query_execution = _prepare_and_execute_query(
            query=extracted_query,
            endpoint_url=args.sparql_endpoint,
        )
        gold_query_form, gold_execution = _prepare_and_execute_query(
            query=gold_query,
            endpoint_url=args.sparql_endpoint,
        )

        validation = _build_validation_block(
            has_extracted_query=has_extracted_query,
            prediction_query_form=prediction_query_form,
            gold_query_form=gold_query_form,
            prediction_execution=query_execution,
            gold_execution=gold_execution,
            endpoint_url=args.sparql_endpoint,
        )

        result_entry = build_raw_result_entry(
            entry_id=entry_id,
            question=question,
            gold_query=gold_query,
        )
        result_entry["entry_metadata"] = entry_metadata
        result_entry["raw_model_output"] = raw_model_output
        result_entry["extracted_query"] = extracted_query
        result_entry["has_extracted_query"] = has_extracted_query
        result_entry["extraction_status"] = extraction_status
        result_entry["response_time_seconds"] = round(response_time_seconds, 4)
        result_entry["prediction_query_form"] = prediction_query_form
        result_entry["gold_query_form"] = gold_query_form
        result_entry["query_execution"] = query_execution
        result_entry["gold_execution"] = gold_execution
        result_entry["validation"] = validation

        results.append(result_entry)

        print(
            f"[{index}/{len(entries)}] "
            f"id={entry_id} "
            f"family={family} "
            f"prompt_chars={len(final_prompt)} "
            f"pred_form={prediction_query_form} "
            f"gold_form={gold_query_form}"
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

    print(f"Collected result entries: {len(results)}")
    print(f"Saved raw benchmark payload to: {output_path}")
    return 0