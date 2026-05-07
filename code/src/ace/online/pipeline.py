"""Adapters from the online ACE loop to the existing query/evaluation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.ace.online.loop import (
    OnlineAceConfig,
    OnlineAceEvaluationInput,
    OnlineAceGenerationInput,
    OnlineAceHooks,
    OnlineAceReflectionInput,
)
from src.ace.online.reflector import OnlineAceReflector, OnlineReflectorConfig
from src.ace.playbook import AceBullet
from src.ace.rendering import render_bullet
from src.evaluate.metric_runner import build_validation_metrics
from src.evaluate.sparql_extraction import extract_sparql_query
from src.query.prompt_builder import build_final_prompt_for_question
from src.sparql.execution import detect_sparql_query_type, execute_sparql_query
from src.sparql.prefixes import prepend_orkg_prefixes


SUPPORTED_QUERY_FORMS = {"select", "ask"}


def _format_prompt_value(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, list):
        values = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(values) if values else "none"
    text = str(value).strip()
    return text if text else "none"


def build_pgmr_lite_meta_prompt(entry: dict[str, Any]) -> str:
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


def render_online_ace_context(context_rules: list[dict[str, Any]]) -> str:
    """Render the active in-memory online ACE rules for one prompt."""
    bullets = [AceBullet.from_dict(rule) for rule in context_rules]
    bullets = [bullet for bullet in bullets if bullet.enabled]
    if not bullets:
        return ""

    rendered = "\n".join(render_bullet(bullet) for bullet in bullets)
    return (
        "ACE playbook rules learned during this online run:\n"
        f"{rendered}\n"
        "Follow these rules, but still return only the required final query.\n"
    )


def build_online_prompt(payload: OnlineAceGenerationInput) -> str:
    """Build a prompt using existing templates plus active in-memory rules."""
    item = payload.item
    family = str(item.get("family") or payload.config.family or "")

    if payload.config.prompt_mode == "pgmr_lite_meta":
        base_prompt = build_pgmr_lite_meta_prompt(item)
    else:
        base_prompt = build_final_prompt_for_question(
            question=str(item.get("question") or ""),
            prompt_mode=payload.config.prompt_mode,
            family=family,
            ace_max_bullets=0,
            model_name=payload.config.model,
        )

    ace_context = render_online_ace_context(payload.context_rules)
    if not ace_context:
        return base_prompt
    return f"{ace_context}\n\n{base_prompt.strip()}"


def _prepare_and_execute_query(
    *,
    query: str | None,
    endpoint_url: str | None,
    execute_query_fn: Any = execute_sparql_query,
) -> tuple[str | None, dict[str, Any]]:
    if not isinstance(query, str) or not query.strip():
        return None, {"status": "skipped", "reason": "no_query"}

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
        response_json = execute_query_fn(
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
        }

    from tools.pgmr.evaluate_model_outputs import postprocess_pgmr_query
    from tools.pgmr.restore_and_execute_predictions import (
        build_entry_mapping,
        detect_basic_query_status,
        restore_pgmr_query,
    )

    pgmr_postprocessed_query = postprocess_pgmr_query(raw_model_output)
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
    }


def _metric_value(metric: Any, key: str = "value") -> Any:
    if isinstance(metric, dict):
        return metric.get(key)
    return metric


def flatten_validation_metrics(validation: dict[str, Any]) -> dict[str, Any]:
    """Expose the small metric surface consumed by the online loop."""
    return {
        "query_extracted": bool(
            _metric_value(validation.get("query_extracted"))
        ),
        "prediction_execution_success": bool(
            _metric_value(validation.get("prediction_execution_success"))
        ),
        "gold_execution_success": bool(
            _metric_value(validation.get("gold_execution_success"))
        ),
        "answer_exact_match": bool(
            _metric_value(validation.get("answer_exact_match"))
        ),
        "answer_f1": float(
            _metric_value(validation.get("answer_precision_recall_f1"), "f1") or 0.0
        ),
        "answer_cell_value_f1": float(
            _metric_value(
                validation.get("answer_cell_value_precision_recall_f1"),
                "f1",
            )
            or 0.0
        ),
        "kg_ref_f1": float(
            _metric_value(validation.get("kg_ref_match"), "f1") or 0.0
        ),
        "predicate_ref_f1": float(
            _metric_value(validation.get("predicate_ref_match"), "f1") or 0.0
        ),
        "error_category": validation.get("primary_error_category"),
    }


@dataclass
class OnlineAcePipeline:
    """Real online ACE hooks backed by existing project utilities."""

    config: OnlineAceConfig
    inference_session: dict[str, Any] | None = None
    pgmr_memory_mapping: dict[str, str] | None = None
    allowed_kg_refs: set[str] | frozenset[str] | None = None
    reflector: OnlineAceReflector | None = None
    execute_query_fn: Any = execute_sparql_query

    def __post_init__(self) -> None:
        if self.inference_session is None:
            from src.query.inference_session import prepare_inference_session

            self.inference_session = prepare_inference_session(self.config.model)

        if self.pgmr_memory_mapping is None and self.config.prediction_format == "pgmr_lite":
            from tools.pgmr.restore_and_execute_predictions import load_memory_mapping

            memory_dir = self.config.pgmr_memory_dir or Path(
                "code/data/orkg_memory/templates"
            )
            self.pgmr_memory_mapping = load_memory_mapping(Path(memory_dir))

        if self.allowed_kg_refs is None:
            from src.evaluate.kg_memory import load_allowed_orkg_refs

            memory_dir = self.config.pgmr_memory_dir or Path(
                "code/data/orkg_memory/templates"
            )
            if Path(memory_dir).exists():
                self.allowed_kg_refs = load_allowed_orkg_refs(Path(memory_dir))[
                    "all_refs"
                ]

        if self.reflector is None:
            self.reflector = OnlineAceReflector(
                OnlineReflectorConfig(reflector_model=self.config.reflect_model)
            )

    def generate(self, payload: OnlineAceGenerationInput) -> dict[str, Any]:
        """Build a prompt and generate one raw model output."""
        from src.query.inference_session import generate_response_with_session

        final_prompt = build_online_prompt(payload)
        model_response = generate_response_with_session(
            session=self.inference_session,
            final_prompt=final_prompt,
        )

        if isinstance(model_response, dict):
            raw_model_output = str(model_response.get("text", "")).strip()
            model_usage = model_response.get("usage")
        else:
            raw_model_output = str(model_response).strip()
            model_usage = None

        return {
            "final_prompt": final_prompt,
            "raw_model_output": raw_model_output,
            "model_usage": model_usage,
            "generation_estimated_cost_usd": 0.0,
        }

    def evaluate(self, payload: OnlineAceEvaluationInput) -> dict[str, Any]:
        """Postprocess, restore, execute, and score one generated query."""
        raw_model_output = str(payload.generation.get("raw_model_output") or "")
        gold_query = payload.item.get("gold_sparql")
        gold_pgmr_query = payload.item.get("gold_pgmr_sparql")

        prediction_payload = _build_prediction_query_from_model_output(
            raw_model_output=raw_model_output,
            entry=payload.item,
            prediction_format=self.config.prediction_format,
            pgmr_memory_mapping=self.pgmr_memory_mapping,
        )

        extracted_query = prediction_payload["extracted_query"]
        prediction_query_form, prediction_execution = _prepare_and_execute_query(
            query=extracted_query,
            endpoint_url=self.config.sparql_endpoint,
            execute_query_fn=self.execute_query_fn,
        )
        gold_query_form, gold_execution = _prepare_and_execute_query(
            query=str(gold_query) if gold_query else None,
            endpoint_url=self.config.sparql_endpoint,
            execute_query_fn=self.execute_query_fn,
        )

        enable_pgmr_metrics = (
            "pgmr" in str(self.config.prompt_mode).lower()
            or "pgmr" in str(self.config.prediction_format).lower()
        )

        validation = build_validation_metrics(
            has_extracted_query=prediction_payload["has_extracted_query"],
            prediction_query_form=prediction_query_form,
            gold_query_form=gold_query_form,
            prediction_execution=prediction_execution,
            gold_execution=gold_execution,
            endpoint_url=self.config.sparql_endpoint,
            prediction_query=extracted_query,
            gold_query=str(gold_query) if gold_query else None,
            prediction_pgmr_query=prediction_payload["pgmr_postprocessed_query"],
            gold_pgmr_query=gold_pgmr_query,
            allowed_kg_refs=self.allowed_kg_refs,
            enable_pgmr_metrics=enable_pgmr_metrics,
        )

        flattened = flatten_validation_metrics(validation)
        return {
            **flattened,
            "validation": validation,
            "extracted_query": extracted_query,
            "pgmr_postprocessed_query": prediction_payload["pgmr_postprocessed_query"],
            "pgmr_restored_query": prediction_payload["pgmr_restored_query"],
            "selected_prediction_query": extracted_query,
            "prediction_query_form": prediction_query_form,
            "gold_query_form": gold_query_form,
            "query_execution": prediction_execution,
            "gold_execution": gold_execution,
            "extraction_status": prediction_payload["extraction_status"],
            "pgmr_restore_status": prediction_payload["pgmr_restore_status"],
            "pgmr_missing_mapping_tokens": prediction_payload[
                "pgmr_missing_mapping_tokens"
            ],
            "pgmr_remaining_tokens": prediction_payload["pgmr_remaining_tokens"],
        }

    def reflect(self, payload: OnlineAceReflectionInput) -> dict[str, Any]:
        """Reflect on one failed attempt using the online LLM reflector."""
        return self.reflector.reflect(payload)

    def hooks(self) -> OnlineAceHooks:
        return OnlineAceHooks(
            generate=self.generate,
            evaluate=self.evaluate,
            reflect=self.reflect,
        )


def build_online_ace_hooks(config: OnlineAceConfig) -> OnlineAceHooks:
    """Prepare real online ACE hooks for server/local execution."""
    return OnlineAcePipeline(config).hooks()
