from __future__ import annotations

from src.evaluate.metrics.common import build_metric


def compute_query_form_match(
    prediction_query_form: str | None,
    gold_query_form: str | None,
) -> dict:
    if prediction_query_form is None or gold_query_form is None:
        return build_metric(
            metric_name="query_form_match",
            metric_type="structural",
            comparable=False,
            value=None,
            reason="missing_query_form",
            prediction_query_form=prediction_query_form,
            gold_query_form=gold_query_form,
        )

    return build_metric(
        metric_name="query_form_match",
        metric_type="structural",
        comparable=True,
        value=1.0 if prediction_query_form == gold_query_form else 0.0,
        prediction_query_form=prediction_query_form,
        gold_query_form=gold_query_form,
    )
