from __future__ import annotations

import json
import os
from typing import Any

from ace.orkg.context import domain_prompt_context, reflection_instruction, normalize_scope


MAX_FIELD_CHARS = int(os.environ.get("ACE_MAX_FIELD_CHARS", "2500"))


def truncate_text(value: str, max_chars: int = MAX_FIELD_CHARS) -> str:
    text = value.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 32].rstrip() + "\n...[truncated for ACE]..."


def shorten(value: Any, max_chars: int = MAX_FIELD_CHARS) -> Any:
    """Recursively shorten large values before sending them to Reflector/Curator."""
    if isinstance(value, str):
        return truncate_text(value, max_chars)

    if isinstance(value, list):
        return [shorten(v, max_chars) for v in value[:20]]

    if isinstance(value, dict):
        shortened = {}
        for key, val in value.items():
            if key in {"response_json", "bindings", "results"}:
                shortened[key] = "[omitted large endpoint response for ACE]"
            else:
                shortened[key] = shorten(val, max_chars)
        return shortened

    return value


def compact_json(obj: Any) -> str:
    return json.dumps(shorten(obj), ensure_ascii=False, indent=2)


def nonempty_dict(fields: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in fields.items() if value not in (None, "", [])}


def get_nested(item: dict[str, Any], *path: str) -> Any:
    cur: Any = item
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def get_family(item: dict[str, Any]) -> str:
    return (
        item.get("family")
        or get_nested(item, "entry_metadata", "family")
        or get_nested(item, "metadata", "family")
        or "unknown_family"
    )


def get_prompt_mode(item: dict[str, Any]) -> str:
    return (
        item.get("prompt_mode")
        or get_nested(item, "entry_metadata", "prompt_mode")
        or "unknown_prompt_mode"
    )


def get_prediction_format(item: dict[str, Any]) -> str:
    return item.get("prediction_format") or "unknown_format"


def get_primary_error(item: dict[str, Any]) -> str:
    return (
        item.get("main_issue")
        or get_nested(item, "validation", "primary_error_category")
        or item.get("diagnostic_hint")
        or "unknown_issue"
    )


def get_validation_metric(item: dict[str, Any], key: str) -> Any:
    value = get_nested(item, "validation", key)
    return value if value is not None else item.get(key)


def get_f1(item: dict[str, Any], key: str) -> Any:
    value = get_nested(item, "validation", key)
    if isinstance(value, dict):
        return value.get("f1")
    return value


def select_gold_target(item: dict[str, Any]) -> tuple[str, str]:
    """Select the active gold target for ACE reflection.

    Direct SPARQL uses gold_query. PGMR-lite should use gold_pgmr_sparql when
    available so reflection stays in placeholder space. Some raw outputs do not
    contain gold_pgmr_sparql; fallback is mainly for smoke tests and should not
    be relied upon for final ACE experiments.
    """
    prediction_format = normalize_scope(get_prediction_format(item))

    if prediction_format == "pgmr_lite":
        gold = (
            item.get("gold_pgmr_sparql")
            or item.get("gold_target_query")
            or item.get("gold_query")
            or ""
        )
        source = "gold_pgmr_sparql" if item.get("gold_pgmr_sparql") else "gold_pgmr_sparql_or_fallback"
        return truncate_text(str(gold), max_chars=4000), source

    gold = (
        item.get("gold_query")
        or item.get("gold_sparql")
        or item.get("gold_target_query")
        or ""
    )
    return truncate_text(str(gold), max_chars=4000), "gold_query"


def build_reasoning_trace(item: dict[str, Any]) -> str:
    family = get_family(item)
    prediction_format = get_prediction_format(item)
    question = item.get("question") or ""

    return compact_json(nonempty_dict({
        "id": item.get("id"),
        "family": family,
        "prompt_mode": get_prompt_mode(item),
        "prediction_format": prediction_format,
        "question": question,
        "raw_model_output": item.get("raw_model_output"),
        "prediction": item.get("prediction"),
        "predicted_query": item.get("predicted_query"),
        "extracted_query": item.get("extracted_query"),
        "postprocessed_query": item.get("postprocessed_query"),
        "executed_query": item.get("executed_query"),
        "query_extracted": get_validation_metric(item, "query_extracted"),
        "extraction_status": item.get("extraction_status"),
        "postprocessing_status": item.get("postprocessing_status"),
        "pgmr_basic_status": item.get("pgmr_basic_status"),
        "domain_prompt_context": domain_prompt_context(family, prediction_format, question),
    }))


def build_predicted_answer(item: dict[str, Any]) -> str:
    return compact_json(nonempty_dict({
        "prediction": item.get("prediction"),
        "predicted_query": item.get("predicted_query"),
        "extracted_query": item.get("extracted_query"),
        "postprocessed_query": item.get("postprocessed_query"),
        "executed_query": item.get("executed_query"),
        "prediction_answer": item.get("prediction_answer"),
        "prediction_result": item.get("prediction_result"),
        "query_execution_status": get_nested(item, "query_execution", "status"),
        "query_execution_result_type": get_nested(item, "query_execution", "result_type"),
    }))


def build_environment_feedback(item: dict[str, Any]) -> str:
    family = get_family(item)
    prediction_format = get_prediction_format(item)
    question = item.get("question") or ""

    return compact_json(nonempty_dict({
        "main_issue": get_primary_error(item),
        "diagnostic_hint": item.get("diagnostic_hint"),
        "prediction_execution_success": get_validation_metric(item, "prediction_execution_success"),
        "gold_execution_success": get_validation_metric(item, "gold_execution_success"),
        "answer_exact_match": get_validation_metric(item, "answer_exact_match"),
        "answer_cell_value_f1": get_f1(item, "answer_cell_value_precision_recall_f1"),
        "answer_f1": get_f1(item, "answer_precision_recall_f1"),
        "kg_ref_f1": get_f1(item, "kg_ref_match"),
        "predicate_ref_f1": get_f1(item, "predicate_ref_match"),
        "class_ref_f1": get_f1(item, "class_ref_match"),
        "resource_ref_f1": get_f1(item, "resource_ref_match"),
        "query_extracted": get_validation_metric(item, "query_extracted"),
        "uri_hallucination": get_validation_metric(item, "uri_hallucination"),
        "pgmr_unmapped_placeholders": get_validation_metric(item, "pgmr_unmapped_placeholders"),
        "query_execution_status": get_nested(item, "query_execution", "status"),
        "gold_execution_status": get_nested(item, "gold_execution", "status"),
        "execution_error": item.get("execution_error") or item.get("error"),
        "ace_reflection_instruction": reflection_instruction(prediction_format),
        "domain_prompt_context": domain_prompt_context(family, prediction_format, question),
    }))


def family_hint(family: str) -> str:
    if family == "nlp4re":
        return (
            "Current family is nlp4re. Prefer rules grounded in RE task, NLP task, "
            "NLP dataset, NLP data source, annotation process, implemented approach, "
            "release, evaluation, metric, validation procedure, baseline comparison, or license."
        )

    if family == "empirical_research_practice":
        return (
            "Current family is empirical_research_practice. Prefer rules grounded in venue serie, "
            "research paradigm, research question, research question answer, data collection, "
            "data analysis, inferential/descriptive statistics, machine learning, threats to validity, "
            "hypothesis, or statistical technique."
        )

    return "Current family is unknown; avoid family-specific claims unless supported by the trace."


def build_question_context(
    item: dict[str, Any],
    gold_field: str,
    *,
    run_note: str | None = None,
) -> str:
    family = get_family(item)
    prediction_format = get_prediction_format(item)
    question = item.get("question") or ""

    return compact_json(nonempty_dict({
        "id": item.get("id"),
        "family": family,
        "prediction_format": prediction_format,
        "prompt_mode": get_prompt_mode(item),
        "question": question,
        "main_issue": get_primary_error(item),
        "gold_target_field_used_for_reflection": gold_field,
        "family_hint": family_hint(family),
        "domain_prompt_context": domain_prompt_context(family, prediction_format, question),
        "run_note": run_note,
    }))
