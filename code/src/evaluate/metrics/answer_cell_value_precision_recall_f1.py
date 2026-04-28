from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


NUMERIC_DATATYPE_SUFFIXES = (
    "#integer",
    "#int",
    "#long",
    "#short",
    "#byte",
    "#decimal",
    "#double",
    "#float",
)

BOOLEAN_DATATYPE_SUFFIX = "#boolean"


def _build_non_comparable_metric(reason: str) -> dict[str, Any]:
    return {
        "metric": "answer_cell_value_precision_recall_f1",
        "type": "answer_based",
        "comparable": False,
        "precision": None,
        "recall": None,
        "f1": None,
        "reason": reason,
        "comparison_mode": "cell_value_only_unique",
        "prediction_value_count": None,
        "gold_value_count": None,
        "true_positive_value_count": None,
        "matched_values": [],
        "missing_gold_values": [],
        "extra_predicted_values": [],
    }


def _is_ok_execution(execution: dict[str, Any] | None) -> bool:
    return isinstance(execution, dict) and execution.get("status") == "ok"


def _get_response_json(execution: dict[str, Any]) -> dict[str, Any]:
    response_json = execution.get("response_json") or {}
    return response_json if isinstance(response_json, dict) else {}


def _normalize_boolean(value: str) -> str:
    lowered = str(value).strip().lower()

    if lowered in {"1", "true"}:
        return "true"

    if lowered in {"0", "false"}:
        return "false"

    return lowered


def _normalize_numeric(value: str) -> str:
    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return str(value).strip()

    normalized = decimal_value.normalize()

    # Avoid scientific notation for common integer-like values.
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal(1)))

    return format(normalized, "f").rstrip("0").rstrip(".")


def _normalize_binding_value(binding: dict[str, Any]) -> tuple[str, str, str, str]:
    value_type = str(binding.get("type") or "").strip().lower()
    value = str(binding.get("value") or "").strip()

    datatype = str(binding.get("datatype") or "").strip().lower()
    language = str(
        binding.get("xml:lang")
        or binding.get("lang")
        or binding.get("language")
        or ""
    ).strip().lower()

    if value_type == "typed-literal":
        value_type = "literal"

    if datatype.endswith(BOOLEAN_DATATYPE_SUFFIX):
        value = _normalize_boolean(value)

    elif datatype.endswith(NUMERIC_DATATYPE_SUFFIXES):
        value = _normalize_numeric(value)

    return (value_type, value, datatype, language)


def _format_value(value: tuple[str, str, str, str]) -> str:
    value_type, lexical_value, datatype, language = value

    if value_type == "uri":
        return lexical_value

    if datatype:
        return f'"{lexical_value}"^^{datatype}'

    if language:
        return f'"{lexical_value}"@{language}'

    return f'"{lexical_value}"'


def _extract_select_cell_values(execution: dict[str, Any]) -> set[tuple[str, str, str, str]]:
    response_json = _get_response_json(execution)
    results = response_json.get("results") or {}
    if not isinstance(results, dict):
        return set()

    bindings = results.get("bindings") or []
    if not isinstance(bindings, list):
        return set()

    values: set[tuple[str, str, str, str]] = set()

    for row in bindings:
        if not isinstance(row, dict):
            continue

        for binding in row.values():
            if isinstance(binding, dict):
                values.add(_normalize_binding_value(binding))

    return values


def _extract_ask_value(execution: dict[str, Any]) -> set[tuple[str, str, str, str]]:
    response_json = _get_response_json(execution)

    if "boolean" not in response_json:
        return set()

    boolean_value = bool(response_json.get("boolean"))
    return {
        (
            "literal",
            "true" if boolean_value else "false",
            "http://www.w3.org/2001/XMLSchema#boolean",
            "",
        )
    }


def _extract_cell_values(execution: dict[str, Any]) -> set[tuple[str, str, str, str]]:
    result_type = str(execution.get("result_type") or "").strip().lower()

    if result_type == "ask":
        return _extract_ask_value(execution)

    return _extract_select_cell_values(execution)


def compute_answer_cell_value_precision_recall_f1(
    *,
    prediction_execution: dict[str, Any] | None,
    gold_execution: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute relaxed answer F1 over unique individual cell values.

    This metric is answer-based but more relaxed than row-level answer F1.

    It ignores:
    - SELECT variable names
    - row grouping
    - column order
    - row order

    It compares:
    - unique returned values
    - value type
    - datatype
    - language tag

    This is useful as a diagnostic metric when the predicted and gold result
    tables have different shapes but still share many individual values.
    """

    if prediction_execution is None:
        return _build_non_comparable_metric("prediction_missing")

    if gold_execution is None:
        return _build_non_comparable_metric("gold_missing")

    if not _is_ok_execution(prediction_execution):
        return _build_non_comparable_metric("prediction_error")

    if not _is_ok_execution(gold_execution):
        return _build_non_comparable_metric("gold_error")

    prediction_values = _extract_cell_values(prediction_execution)
    gold_values = _extract_cell_values(gold_execution)

    true_positive_values = prediction_values & gold_values

    prediction_count = len(prediction_values)
    gold_count = len(gold_values)
    true_positive_count = len(true_positive_values)

    if prediction_count == 0 and gold_count == 0:
        precision = 1.0
        recall = 1.0
        f1 = 1.0
    else:
        precision = 0.0 if prediction_count == 0 else true_positive_count / prediction_count
        recall = 0.0 if gold_count == 0 else true_positive_count / gold_count
        f1 = (
            0.0
            if precision + recall == 0.0
            else (2.0 * precision * recall) / (precision + recall)
        )

    missing_gold_values = sorted(gold_values - prediction_values)
    extra_predicted_values = sorted(prediction_values - gold_values)
    matched_values = sorted(true_positive_values)

    return {
        "metric": "answer_cell_value_precision_recall_f1",
        "type": "answer_based",
        "comparable": True,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "comparison_mode": "cell_value_only_unique",
        "prediction_value_count": prediction_count,
        "gold_value_count": gold_count,
        "true_positive_value_count": true_positive_count,
        "matched_values": [_format_value(value) for value in matched_values[:50]],
        "missing_gold_values": [_format_value(value) for value in missing_gold_values[:50]],
        "extra_predicted_values": [
            _format_value(value) for value in extra_predicted_values[:50]
        ],
    }
