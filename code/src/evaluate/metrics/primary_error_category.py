from __future__ import annotations

from src.evaluate.metrics.common import SUPPORTED_QUERY_FORMS


def compute_primary_error_category(
    has_extracted_query: bool,
    prediction_query_form: str | None,
    gold_query_form: str | None,
    prediction_execution: dict,
    gold_execution: dict,
    answer_exact_match: dict,
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

    if answer_exact_match.get("comparable") and answer_exact_match.get("value") == 0.0:
        return "answer_mismatch"

    return "success"
