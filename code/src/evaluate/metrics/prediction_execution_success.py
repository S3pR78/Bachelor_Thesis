from __future__ import annotations

from src.evaluate.metrics.common import SUPPORTED_QUERY_FORMS, build_metric


def compute_prediction_execution_success(
    has_extracted_query: bool,
    prediction_query_form: str | None,
    prediction_execution: dict,
    endpoint_url: str | None,
) -> dict:
    if not endpoint_url:
        return build_metric(
            metric_name="prediction_execution_success",
            metric_type="execution_based",
            comparable=False,
            value=None,
            reason="no_endpoint_configured",
            execution_status=prediction_execution.get("status"),
        )

    if not has_extracted_query or prediction_query_form not in SUPPORTED_QUERY_FORMS:
        return build_metric(
            metric_name="prediction_execution_success",
            metric_type="execution_based",
            comparable=False,
            value=None,
            reason="unsupported_or_missing_prediction_query",
            execution_status=prediction_execution.get("status"),
            prediction_query_form=prediction_query_form,
        )

    return build_metric(
        metric_name="prediction_execution_success",
        metric_type="execution_based",
        comparable=True,
        value=1.0 if prediction_execution.get("status") == "ok" else 0.0,
        execution_status=prediction_execution.get("status"),
        prediction_query_form=prediction_query_form,
    )
