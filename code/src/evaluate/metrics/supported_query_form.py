from __future__ import annotations

from src.evaluate.metrics.common import SUPPORTED_QUERY_FORMS, build_metric


def compute_supported_query_form(
    has_extracted_query: bool,
    prediction_query_form: str | None,
) -> dict:
    if not has_extracted_query:
        return build_metric(
            metric_name="supported_query_form",
            metric_type="structural",
            comparable=False,
            value=None,
            reason="no_extracted_query",
            prediction_query_form=prediction_query_form,
        )

    return build_metric(
        metric_name="supported_query_form",
        metric_type="structural",
        comparable=True,
        value=1.0 if prediction_query_form in SUPPORTED_QUERY_FORMS else 0.0,
        prediction_query_form=prediction_query_form,
    )
