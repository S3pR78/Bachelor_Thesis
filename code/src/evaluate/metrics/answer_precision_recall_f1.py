from __future__ import annotations

from typing import Any

from src.evaluate.answer_normalization import normalize_execution_result
from src.evaluate.metrics.common import build_metric, round_metric_payload

NON_COMPARABLE_KINDS = {"missing", "error", "unsupported"}


def _build_non_comparable_metric(
    prediction_kind: str,
    gold_kind: str,
    reason: str,
) -> dict[str, Any]:
    return build_metric(
        metric_name="answer_precision_recall_f1",
        metric_type="answer_based",
        comparable=False,
        value=None,
        reason=reason,
        prediction_kind=prediction_kind,
        gold_kind=gold_kind,
    )


def compute_answer_precision_recall_f1(
    prediction_execution: dict[str, Any] | None,
    gold_execution: dict[str, Any] | None,
) -> dict[str, Any]:
    prediction = normalize_execution_result(prediction_execution)
    gold = normalize_execution_result(gold_execution)

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
        return round_metric_payload(
            {
                "metric": "answer_precision_recall_f1",
                "type": "answer_based",
                "comparable": True,
                "value": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "reason": "different_answer_kind",
                "prediction_kind": prediction_kind,
                "gold_kind": gold_kind,
            }
        )

    if prediction_kind == "ask":
        value = 1.0 if prediction["value"] == gold["value"] else 0.0
        return round_metric_payload(
            {
                "metric": "answer_precision_recall_f1",
                "type": "answer_based",
                "comparable": True,
                "value": value,
                "precision": value,
                "recall": value,
                "f1": value,
                "prediction_kind": "ask",
                "gold_kind": "ask",
            }
        )

    if prediction_kind == "select":
        prediction_rows = prediction["rows"]
        gold_rows = gold["rows"]

        true_positives = len(prediction_rows & gold_rows)
        prediction_row_count = prediction["row_count"]
        gold_row_count = gold["row_count"]

        if prediction_row_count == 0 and gold_row_count == 0:
            precision = 1.0
            recall = 1.0
            f1 = 1.0
        else:
            precision = (
                0.0
                if prediction_row_count == 0
                else true_positives / prediction_row_count
            )
            recall = (
                0.0
                if gold_row_count == 0
                else true_positives / gold_row_count
            )
            f1 = (
                0.0
                if (precision + recall) == 0.0
                else (2.0 * precision * recall) / (precision + recall)
            )

        return round_metric_payload(
            {
                "metric": "answer_precision_recall_f1",
                "type": "answer_based",
                "comparable": True,
                "value": f1,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "prediction_kind": "select",
                "gold_kind": "select",
                "true_positives": true_positives,
                "prediction_row_count": prediction_row_count,
                "gold_row_count": gold_row_count,
            }
        )

    raise ValueError(f"Unsupported normalized answer kind: {prediction_kind}")
