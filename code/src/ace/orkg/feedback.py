from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ORKGFeedbackTrace:
    """Structured ACE feedback trace for one ORKG Text-to-SPARQL evaluation item."""

    id: str
    family: Optional[str]
    source_dataset: Optional[str]
    prompt_mode: Optional[str]
    prediction_format: Optional[str]

    question: str

    # Different query/output stages.
    raw_model_output: Optional[str]
    extracted_query: Optional[str]
    postprocessed_query: Optional[str]
    executed_query: Optional[str]
    gold_query: Optional[str]

    # Core feedback signals.
    query_extracted: bool
    extraction_status: Optional[str]
    postprocessing_status: Optional[str]
    prediction_execution_success: bool
    answer_exact_match: bool
    answer_cell_value_f1: Optional[float]
    kg_ref_f1: Optional[float]

    # Optional finer-grained KG-reference metrics.
    predicate_ref_f1: Optional[float]
    class_ref_f1: Optional[float]
    resource_ref_f1: Optional[float]

    # Error information if available.
    prediction_error: Optional[str]
    execution_error: Optional[str]

    # Deterministic diagnosis for the LLM Reflector.
    main_issue: str
    diagnostic_hint: str


def _safe_get(item: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first available non-None value from a list of possible keys."""
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_main_issue(
    *,
    query_extracted: bool,
    extraction_status: Optional[str],
    postprocessing_status: Optional[str],
    prediction_execution_success: bool,
    answer_exact_match: bool,
    answer_cell_value_f1: Optional[float],
    kg_ref_f1: Optional[float],
) -> str:
    """Classify the main issue using deterministic evaluation signals."""

    extraction_status_l = (extraction_status or "").lower()
    postprocessing_status_l = (postprocessing_status or "").lower()

    if not query_extracted:
        return "no_query_extracted"

    if "pgmr_restore:missing_mapping" in extraction_status_l or "missing_mapping" in extraction_status_l:
        return "pgmr_missing_mapping_or_hallucinated_placeholder"

    if "pgmr_restore:missing_mapping" in postprocessing_status_l or "missing_mapping" in postprocessing_status_l:
        return "pgmr_missing_mapping_or_hallucinated_placeholder"

    if "pgmr_restore" in extraction_status_l and "ok" not in extraction_status_l:
        return "pgmr_restore_failure"

    if "pgmr_restore" in postprocessing_status_l and "ok" not in postprocessing_status_l:
        return "pgmr_restore_failure"

    if not prediction_execution_success:
        return "execution_failure"

    if answer_exact_match:
        return "correct"

    if answer_cell_value_f1 is not None and answer_cell_value_f1 >= 0.8:
        return "partial_answer_mismatch"

    if kg_ref_f1 is not None and kg_ref_f1 < 0.5:
        return "wrong_or_missing_kg_references"

    if kg_ref_f1 is not None and kg_ref_f1 >= 0.5:
        return "query_logic_projection_or_filter_error"

    return "answer_mismatch"


def make_diagnostic_hint(main_issue: str) -> str:
    """Create a short deterministic hint for the LLM Reflector."""

    hints = {
        "no_query_extracted": (
            "No executable query could be extracted from the raw model output. "
            "Use raw_model_output to diagnose whether the model produced explanations, markdown, "
            "multiple outputs, incomplete SPARQL, or malformed PGMR-lite instead of a clean query."
        ),
        "pgmr_missing_mapping_or_hallucinated_placeholder": (
            "The model produced a PGMR-lite placeholder that could not be restored using the available memory mapping. "
            "Use raw_model_output and extracted_query to identify hallucinated pgmr: predicates or pgmrc: classes. "
            "The reusable rule should restrict the model to known family-specific PGMR placeholders."
        ),
        "pgmr_restore_failure": (
            "A PGMR-lite query was extracted, but restoration/postprocessing failed. "
            "Compare raw_model_output, extracted_query, and postprocessed_query to identify whether the structure or placeholders are invalid."
        ),
        "execution_failure": (
            "A query was extracted and/or postprocessed, but execution failed. "
            "Use executed_query or postprocessed_query to diagnose invalid SPARQL syntax, unbound variables, malformed FILTER expressions, "
            "invalid prefixes, or endpoint-incompatible structure."
        ),
        "correct": (
            "The prediction matched the gold answer according to the evaluation metrics."
        ),
        "partial_answer_mismatch": (
            "The prediction was close to the gold answer but not an exact match. "
            "Compare executed_query/postprocessed_query with gold_query to identify missing values, extra values, projection issues, or insufficient filtering."
        ),
        "wrong_or_missing_kg_references": (
            "The prediction used substantially different ORKG references than the gold query. "
            "Compare executed_query/postprocessed_query with gold_query to identify wrong predicates, classes, resources, or template-specific relations."
        ),
        "query_logic_projection_or_filter_error": (
            "The prediction used some relevant ORKG references, but the answer was still wrong. "
            "Compare executed_query/postprocessed_query with gold_query to identify query-logic, SELECT projection, join-pattern, or filter errors."
        ),
        "answer_mismatch": (
            "The query executed but did not match the gold answer. "
            "Compare executed_query/postprocessed_query with gold_query and derive a reusable structural rule. Do not copy the gold query."
        ),
    }
    return hints.get(main_issue, hints["answer_mismatch"])


def raw_item_to_feedback_trace(
    item: Dict[str, Any],
    *,
    prompt_mode: Optional[str] = None,
    prediction_format: Optional[str] = None,
) -> ORKGFeedbackTrace:
    """Convert one benchmark_raw.json item into an ORKGFeedbackTrace."""

    raw_model_output = _safe_get(
        item,
        "raw_model_output",
        "model_output",
        "prediction_raw",
        "prediction",
        default=None,
    )

    extracted_query = _safe_get(
        item,
        "extracted_query",
        "prediction_query",
        "predicted_query",
        "extracted_sparql",
        default=None,
    )

    postprocessed_query = _safe_get(
        item,
        "pgmr_postprocessed_query",
        "postprocessed_query",
        "restored_query",
        "restored_sparql",
        "prediction_postprocessed_query",
        default=None,
    )

    executed_query = _safe_get(
        item,
        "executed_query",
        "prediction_executed_query",
        "final_query",
        "final_prediction_query",
        default=None,
    )

    # Fallback: if the run does not store executed_query separately, the closest
    # representation is usually postprocessed_query, then extracted_query.
    if executed_query is None:
        executed_query = postprocessed_query or extracted_query

    gold_query = _safe_get(
        item,
        "gold_query",
        "gold_sparql",
        "reference_query",
        "target",
        default=None,
    )

    query_extracted = _as_bool(
        _safe_get(
            item,
            "query_extracted",
            "prediction_query_extracted",
            "has_extracted_query",
            default=extracted_query is not None,
        )
    )

    extraction_status = _safe_get(
        item,
        "extraction_status",
        "prediction_extraction_status",
        "query_extraction_status",
        default=None,
    )

    postprocessing_status = _safe_get(
        item,
        "postprocessing_status",
        "pgmr_postprocessing_status",
        "pgmr_restore_status",
        "restore_status",
        default=None,
    )

    prediction_execution_success = _as_bool(
        _safe_get(
            item,
            "prediction_execution_success",
            "execution_success",
            "prediction_executed",
            default=False,
        )
    )

    answer_exact_match = _as_bool(
        _safe_get(item, "answer_exact_match", "exact_match", default=False)
    )

    answer_cell_value_f1 = _as_float(
        _safe_get(
            item,
            "answer_cell_value_f1",
            "answer_f1",
            "cell_value_f1",
            default=None,
        )
    )

    kg_ref_f1 = _as_float(
        _safe_get(item, "kg_ref_f1", "kg_reference_f1", default=None)
    )

    predicate_ref_f1 = _as_float(
        _safe_get(item, "predicate_ref_f1", "predicate_reference_f1", default=None)
    )
    class_ref_f1 = _as_float(
        _safe_get(item, "class_ref_f1", "class_reference_f1", default=None)
    )
    resource_ref_f1 = _as_float(
        _safe_get(item, "resource_ref_f1", "resource_reference_f1", default=None)
    )

    prediction_error = _safe_get(
        item,
        "prediction_error",
        "error",
        "prediction_error_message",
        default=None,
    )

    execution_error = _safe_get(
        item,
        "execution_error",
        "prediction_execution_error",
        "endpoint_error",
        "sparql_error",
        default=None,
    )

    main_issue = classify_main_issue(
        query_extracted=query_extracted,
        extraction_status=extraction_status,
        postprocessing_status=postprocessing_status,
        prediction_execution_success=prediction_execution_success,
        answer_exact_match=answer_exact_match,
        answer_cell_value_f1=answer_cell_value_f1,
        kg_ref_f1=kg_ref_f1,
    )

    return ORKGFeedbackTrace(
        id=str(_safe_get(item, "id", "example_id", "source_id", default="unknown")),
        family=_safe_get(item, "family", default=None),
        source_dataset=_safe_get(item, "source_dataset", default=None),
        prompt_mode=prompt_mode or _safe_get(item, "prompt_mode", default=None),
        prediction_format=prediction_format or _safe_get(item, "prediction_format", default=None),
        question=str(_safe_get(item, "question", default="")),
        raw_model_output=raw_model_output,
        extracted_query=extracted_query,
        postprocessed_query=postprocessed_query,
        executed_query=executed_query,
        gold_query=gold_query,
        query_extracted=query_extracted,
        extraction_status=extraction_status,
        postprocessing_status=postprocessing_status,
        prediction_execution_success=prediction_execution_success,
        answer_exact_match=answer_exact_match,
        answer_cell_value_f1=answer_cell_value_f1,
        kg_ref_f1=kg_ref_f1,
        predicate_ref_f1=predicate_ref_f1,
        class_ref_f1=class_ref_f1,
        resource_ref_f1=resource_ref_f1,
        prediction_error=prediction_error,
        execution_error=execution_error,
        main_issue=main_issue,
        diagnostic_hint=make_diagnostic_hint(main_issue),
    )


def load_raw_items(path: Path) -> List[Dict[str, Any]]:
    """Load benchmark_raw.json in list or dict-wrapped format."""
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ["items", "results", "examples", "records", "benchmark_raw", "raw"]:
            value = payload.get(key)
            if isinstance(value, list):
                return value

    raise ValueError(f"Could not find a list of raw evaluation items in {path}")


def build_feedback_traces(
    raw_path: Path,
    *,
    prompt_mode: Optional[str] = None,
    prediction_format: Optional[str] = None,
    include_correct: bool = False,
) -> List[Dict[str, Any]]:
    """Build serializable feedback traces from benchmark_raw.json."""
    items = load_raw_items(raw_path)
    traces = [
        raw_item_to_feedback_trace(
            item,
            prompt_mode=prompt_mode,
            prediction_format=prediction_format,
        )
        for item in items
    ]

    if not include_correct:
        traces = [trace for trace in traces if trace.main_issue != "correct"]

    return [asdict(trace) for trace in traces]


def write_feedback_traces(
    raw_path: Path,
    output_path: Path,
    *,
    prompt_mode: Optional[str] = None,
    prediction_format: Optional[str] = None,
    include_correct: bool = False,
) -> None:
    traces = build_feedback_traces(
        raw_path,
        prompt_mode=prompt_mode,
        prediction_format=prediction_format,
        include_correct=include_correct,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(traces, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
