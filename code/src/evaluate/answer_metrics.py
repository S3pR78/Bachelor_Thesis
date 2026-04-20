from __future__ import annotations

from typing import Any

from src.evaluate.answer_normalization import normalize_execution_result


NON_COMPARABLE_KINDS = {"missing", "error", "unsupported"}


def compute_answer_exact_match(
    prediction_execution: dict[str, Any] | None,
    gold_execution: dict[str, Any] | None,
) -> dict[str, Any]:
    prediction = normalize_execution_result(prediction_execution)
    gold = normalize_execution_result(gold_execution)

    prediction_kind = prediction["kind"]
    gold_kind = gold["kind"]

    if prediction_kind in NON_COMPARABLE_KINDS:
        return {
            "metric": "answer_exact_match",
            "type": "answer_based",
            "comparable": False,
            "value": None,
            "reason": f"prediction_{prediction_kind}",
            "prediction_kind": prediction_kind,
            "gold_kind": gold_kind,
        }

    if gold_kind in NON_COMPARABLE_KINDS:
        return {
            "metric": "answer_exact_match",
            "type": "answer_based",
            "comparable": False,
            "value": None,
            "reason": f"gold_{gold_kind}",
            "prediction_kind": prediction_kind,
            "gold_kind": gold_kind,
        }

    if prediction_kind != gold_kind:
        return {
            "metric": "answer_exact_match",
            "type": "answer_based",
            "comparable": True,
            "value": 0.0,
            "reason": "different_answer_kind",
            "prediction_kind": prediction_kind,
            "gold_kind": gold_kind,
        }

    if prediction_kind == "ask":
        return {
            "metric": "answer_exact_match",
            "type": "answer_based",
            "comparable": True,
            "value": 1.0 if prediction["value"] == gold["value"] else 0.0,
            "prediction_kind": "ask",
            "gold_kind": "ask",
        }

    if prediction_kind == "select":
        return {
            "metric": "answer_exact_match",
            "type": "answer_based",
            "comparable": True,
            "value": 1.0 if prediction["rows"] == gold["rows"] else 0.0,
            "prediction_kind": "select",
            "gold_kind": "select",
            "prediction_row_count": prediction["row_count"],
            "gold_row_count": gold["row_count"],
        }

    raise ValueError(f"Unsupported normalized answer kind: {prediction_kind}")