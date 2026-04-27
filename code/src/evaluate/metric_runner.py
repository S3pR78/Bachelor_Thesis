from __future__ import annotations

from typing import Any

from src.evaluate.metrics.answer_exact_match import compute_answer_exact_match
from src.evaluate.metrics.answer_precision_recall_f1 import (
    compute_answer_precision_recall_f1,
)
from src.evaluate.metrics.gold_execution_success import compute_gold_execution_success
from src.evaluate.metrics.prediction_execution_success import (
    compute_prediction_execution_success,
)
from src.evaluate.metrics.primary_error_category import compute_primary_error_category
from src.evaluate.metrics.query_extracted import compute_query_extracted
from src.evaluate.metrics.query_form_match import compute_query_form_match
from src.evaluate.metrics.supported_query_form import compute_supported_query_form


def build_validation_metrics(
    *,
    has_extracted_query: bool,
    prediction_query_form: str | None,
    gold_query_form: str | None,
    prediction_execution: dict[str, Any] | None,
    gold_execution: dict[str, Any] | None,
    endpoint_url: str | None,
) -> dict[str, Any]:
    prediction_execution_for_status = prediction_execution or {}
    gold_execution_for_status = gold_execution or {}

    query_extracted = compute_query_extracted(
        has_extracted_query=has_extracted_query,
    )

    supported_query_form = compute_supported_query_form(
        has_extracted_query=has_extracted_query,
        prediction_query_form=prediction_query_form,
    )

    query_form_match = compute_query_form_match(
        prediction_query_form=prediction_query_form,
        gold_query_form=gold_query_form,
    )

    prediction_execution_success = compute_prediction_execution_success(
        has_extracted_query=has_extracted_query,
        prediction_query_form=prediction_query_form,
        prediction_execution=prediction_execution_for_status,
        endpoint_url=endpoint_url,
    )

    gold_execution_success = compute_gold_execution_success(
        gold_query_form=gold_query_form,
        gold_execution=gold_execution_for_status,
        endpoint_url=endpoint_url,
    )

    answer_exact_match = compute_answer_exact_match(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    answer_precision_recall_f1 = compute_answer_precision_recall_f1(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    primary_error_category = compute_primary_error_category(
        has_extracted_query=has_extracted_query,
        prediction_query_form=prediction_query_form,
        gold_query_form=gold_query_form,
        prediction_execution=prediction_execution_for_status,
        gold_execution=gold_execution_for_status,
        answer_exact_match=answer_exact_match,
        endpoint_url=endpoint_url,
    )

    return {
        "query_extracted": query_extracted,
        "supported_query_form": supported_query_form,
        "query_form_match": query_form_match,
        "prediction_execution_success": prediction_execution_success,
        "gold_execution_success": gold_execution_success,
        "answer_exact_match": answer_exact_match,
        "answer_precision_recall_f1": answer_precision_recall_f1,
        "primary_error_category": primary_error_category,
    }
