from __future__ import annotations

from typing import Any

from src.evaluate.answer_normalization import normalize_execution_result
from src.evaluate.metrics.common import build_metric


NON_COMPARABLE_KINDS = {"missing", "error", "unsupported"}


def _build_non_comparable_metric(
    prediction_kind: str,
    gold_kind: str,
    reason: str,
) -> dict[str, Any]:
    return build_metric(
        metric_name="answer_value_exact_match",
        metric_type="answer_based",
        comparable=False,
        value=None,
        reason=reason,
        prediction_kind=prediction_kind,
        gold_kind=gold_kind,
        comparison_mode="value_only",
    )


def compute_answer_value_exact_match(
    prediction_execution: dict[str, Any] | None,
    gold_execution: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute relaxed exact match over executed answers.

    Compared to answer_exact_match, this metric uses value-only SELECT
    normalization. For SELECT answers, variable names are ignored and only the
    returned values are compared. ASK answers are compared normally.
    """

    prediction = normalize_execution_result(
        prediction_execution,
        select_mode="value_only",
    )
    gold = normalize_execution_result(
        gold_execution,
        select_mode="value_only",
    )

    prediction_kind = prediction["kind"]
    gold_kind = gold["kind"]

    if prediction_kind in NON_COMPARABLE_KINDS:
        return _build_non_comparable_metric(
            prediction_kind=prediction_kind,
            gold_kind=gold_kind,
            reason=f"prediction_{prediction_kind}",
        )

    if gold_kind in NON_COMPARABLE_KINDS:
        return _build_non_comparable_metric(
            prediction_kind=prediction_kind,
            gold_kind=gold_kind,
            reason=f"gold_{gold_kind}",
        )

    if prediction_kind != gold_kind:
        return build_metric(
            metric_name="answer_value_exact_match",
            metric_type="answer_based",
            comparable=True,
            value=0.0,
            reason="different_answer_kind",
            prediction_kind=prediction_kind,
            gold_kind=gold_kind,
            comparison_mode="value_only",
        )

    if prediction_kind == "ask":
        return build_metric(
            metric_name="answer_value_exact_match",
            metric_type="answer_based",
            comparable=True,
            value=1.0 if prediction["value"] == gold["value"] else 0.0,
            prediction_kind="ask",
            gold_kind="ask",
            comparison_mode="value_only",
        )

    if prediction_kind == "select":
        return build_metric(
            metric_name="answer_value_exact_match",
            metric_type="answer_based",
            comparable=True,
            value=1.0 if prediction["rows"] == gold["rows"] else 0.0,
            prediction_kind="select",
            gold_kind="select",
            prediction_row_count=prediction["row_count"],
            gold_row_count=gold["row_count"],
            comparison_mode="value_only",
        )

    raise ValueError(f"Unsupported normalized answer kind: {prediction_kind}")
