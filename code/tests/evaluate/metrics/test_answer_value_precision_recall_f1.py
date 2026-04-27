from __future__ import annotations

from src.evaluate.metrics.answer_precision_recall_f1 import (
    compute_answer_precision_recall_f1,
)
from src.evaluate.metrics.answer_value_precision_recall_f1 import (
    compute_answer_value_precision_recall_f1,
)


def uri(value: str) -> dict:
    return {
        "type": "uri",
        "value": value,
    }


def lit(value: str, datatype: str = "", lang: str = "") -> dict:
    obj = {
        "type": "literal",
        "value": value,
    }
    if datatype:
        obj["datatype"] = datatype
    if lang:
        obj["xml:lang"] = lang
    return obj


def ok_select(bindings: list[dict]) -> dict:
    return {
        "status": "ok",
        "result_type": "select",
        "response_json": {
            "head": {"vars": []},
            "results": {"bindings": bindings},
        },
    }


def ok_ask(value: bool) -> dict:
    return {
        "status": "ok",
        "result_type": "ask",
        "response_json": {
            "boolean": value,
        },
    }


def error_execution(reason: str = "endpoint_bad_request") -> dict:
    return {
        "status": "error",
        "error": reason,
    }


def test_value_f1_ignores_select_variable_names() -> None:
    prediction = ok_select(
        [
            {
                "name": lit("Smith"),
            }
        ]
    )

    gold = ok_select(
        [
            {
                "nachname": lit("Smith"),
            }
        ]
    )

    strict = compute_answer_precision_recall_f1(
        prediction_execution=prediction,
        gold_execution=gold,
    )
    relaxed = compute_answer_value_precision_recall_f1(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert strict["f1"] == 0.0

    assert relaxed["metric"] == "answer_value_precision_recall_f1"
    assert relaxed["type"] == "answer_based"
    assert relaxed["comparison_mode"] == "value_only"
    assert relaxed["comparable"] is True
    assert relaxed["precision"] == 1.0
    assert relaxed["recall"] == 1.0
    assert relaxed["f1"] == 1.0
    assert relaxed["value"] == 1.0


def test_value_f1_detects_partial_overlap_with_different_variable_names() -> None:
    prediction = ok_select(
        [
            {"name": lit("Smith")},
            {"name": lit("Miller")},
        ]
    )

    gold = ok_select(
        [
            {"nachname": lit("Smith")},
            {"nachname": lit("Taylor")},
        ]
    )

    metric = compute_answer_value_precision_recall_f1(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["true_positives"] == 1
    assert metric["prediction_row_count"] == 2
    assert metric["gold_row_count"] == 2
    assert metric["precision"] == 0.5
    assert metric["recall"] == 0.5
    assert metric["f1"] == 0.5
    assert metric["value"] == 0.5


def test_value_f1_works_for_multi_column_rows() -> None:
    prediction = ok_select(
        [
            {
                "name": lit("Smith"),
                "paper": uri("http://orkg.org/orkg/resource/R1"),
            },
            {
                "name": lit("Miller"),
                "paper": uri("http://orkg.org/orkg/resource/R2"),
            },
        ]
    )

    gold = ok_select(
        [
            {
                "surname": lit("Smith"),
                "publication": uri("http://orkg.org/orkg/resource/R1"),
            },
            {
                "surname": lit("Taylor"),
                "publication": uri("http://orkg.org/orkg/resource/R3"),
            },
        ]
    )

    metric = compute_answer_value_precision_recall_f1(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["true_positives"] == 1
    assert metric["prediction_row_count"] == 2
    assert metric["gold_row_count"] == 2
    assert metric["precision"] == 0.5
    assert metric["recall"] == 0.5
    assert metric["f1"] == 0.5


def test_value_f1_still_detects_wrong_values() -> None:
    prediction = ok_select(
        [
            {"name": lit("Smith")},
        ]
    )

    gold = ok_select(
        [
            {"nachname": lit("Miller")},
        ]
    )

    metric = compute_answer_value_precision_recall_f1(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["true_positives"] == 0
    assert metric["precision"] == 0.0
    assert metric["recall"] == 0.0
    assert metric["f1"] == 0.0
    assert metric["value"] == 0.0


def test_value_f1_for_empty_select_answers() -> None:
    metric = compute_answer_value_precision_recall_f1(
        prediction_execution=ok_select([]),
        gold_execution=ok_select([]),
    )

    assert metric["comparable"] is True
    assert metric["precision"] == 1.0
    assert metric["recall"] == 1.0
    assert metric["f1"] == 1.0
    assert metric["value"] == 1.0


def test_value_f1_compares_ask_answers_normally() -> None:
    same = compute_answer_value_precision_recall_f1(
        prediction_execution=ok_ask(True),
        gold_execution=ok_ask(True),
    )
    different = compute_answer_value_precision_recall_f1(
        prediction_execution=ok_ask(False),
        gold_execution=ok_ask(True),
    )

    assert same["comparable"] is True
    assert same["precision"] == 1.0
    assert same["recall"] == 1.0
    assert same["f1"] == 1.0

    assert different["comparable"] is True
    assert different["precision"] == 0.0
    assert different["recall"] == 0.0
    assert different["f1"] == 0.0


def test_value_f1_is_not_comparable_for_prediction_error() -> None:
    metric = compute_answer_value_precision_recall_f1(
        prediction_execution=error_execution(),
        gold_execution=ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        ),
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["precision"] is None
    assert metric["recall"] is None
    assert metric["f1"] is None
    assert metric["reason"] == "prediction_error"
    assert metric["comparison_mode"] == "value_only"


def test_value_f1_is_not_comparable_for_missing_prediction() -> None:
    metric = compute_answer_value_precision_recall_f1(
        prediction_execution=None,
        gold_execution=ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        ),
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "prediction_missing"
    assert metric["comparison_mode"] == "value_only"


def test_value_f1_uses_numeric_literal_normalization() -> None:
    prediction = ok_select(
        [
            {
                "count": lit(
                    "1",
                    datatype="http://www.w3.org/2001/XMLSchema#integer",
                )
            }
        ]
    )

    gold = ok_select(
        [
            {
                "number": lit(
                    "1.0",
                    datatype="http://www.w3.org/2001/XMLSchema#decimal",
                )
            }
        ]
    )

    metric = compute_answer_value_precision_recall_f1(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["precision"] == 1.0
    assert metric["recall"] == 1.0
    assert metric["f1"] == 1.0
