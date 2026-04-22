from __future__ import annotations

from src.evaluate.metrics.common import SUPPORTED_QUERY_FORMS, build_metric


def compute_gold_execution_success(
    gold_query_form: str | None,
    gold_execution: dict,
    endpoint_url: str | None,
) -> dict:
    if not endpoint_url:
        return build_metric(
            metric_name="gold_execution_success",
            metric_type="execution_based",
            comparable=False,
            value=None,
            reason="no_endpoint_configured",
            execution_status=gold_execution.get("status"),
        )

    if gold_query_form not in SUPPORTED_QUERY_FORMS:
        return build_metric(
            metric_name="gold_execution_success",
            metric_type="execution_based",
            comparable=False,
            value=None,
            reason="unsupported_or_missing_gold_query",
            execution_status=gold_execution.get("status"),
            gold_query_form=gold_query_form,
        )

    return build_metric(
        metric_name="gold_execution_success",
        metric_type="execution_based",
        comparable=True,
        value=1.0 if gold_execution.get("status") == "ok" else 0.0,
        execution_status=gold_execution.get("status"),
        gold_query_form=gold_query_form,
    )
