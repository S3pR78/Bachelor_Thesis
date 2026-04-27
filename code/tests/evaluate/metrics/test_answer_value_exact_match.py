from __future__ import annotations

from src.evaluate.metrics.answer_exact_match import compute_answer_exact_match
from src.evaluate.metrics.answer_value_exact_match import (
    compute_answer_value_exact_match,
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


def test_answer_value_exact_match_ignores_select_variable_names() -> None:
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

    strict_metric = compute_answer_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )
    value_metric = compute_answer_value_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert strict_metric["value"] == 0.0

    assert value_metric["metric"] == "answer_value_exact_match"
    assert value_metric["type"] == "answer_based"
    assert value_metric["comparison_mode"] == "value_only"
    assert value_metric["comparable"] is True
    assert value_metric["value"] == 1.0
    assert value_metric["prediction_kind"] == "select"
    assert value_metric["gold_kind"] == "select"


def test_answer_value_exact_match_detects_wrong_select_values() -> None:
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
                "nachname": lit("Miller"),
            }
        ]
    )

    metric = compute_answer_value_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 0.0


def test_answer_value_exact_match_works_for_multi_column_rows() -> None:
    prediction = ok_select(
        [
            {
                "name": lit("Smith"),
                "paper": uri("http://orkg.org/orkg/resource/R1"),
            }
        ]
    )

    gold = ok_select(
        [
            {
                "surname": lit("Smith"),
                "publication": uri("http://orkg.org/orkg/resource/R1"),
            }
        ]
    )

    metric = compute_answer_value_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["prediction_row_count"] == 1
    assert metric["gold_row_count"] == 1


def test_answer_value_exact_match_still_ignores_row_order() -> None:
    prediction = ok_select(
        [
            {"name": lit("Smith")},
            {"name": lit("Miller")},
        ]
    )

    gold = ok_select(
        [
            {"nachname": lit("Miller")},
            {"nachname": lit("Smith")},
        ]
    )

    metric = compute_answer_value_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["prediction_row_count"] == 2
    assert metric["gold_row_count"] == 2


def test_answer_value_exact_match_compares_ask_answers_normally() -> None:
    same = compute_answer_value_exact_match(
        prediction_execution=ok_ask(True),
        gold_execution=ok_ask(True),
    )
    different = compute_answer_value_exact_match(
        prediction_execution=ok_ask(False),
        gold_execution=ok_ask(True),
    )

    assert same["comparable"] is True
    assert same["value"] == 1.0

    assert different["comparable"] is True
    assert different["value"] == 0.0


def test_answer_value_exact_match_is_not_comparable_for_prediction_error() -> None:
    metric = compute_answer_value_exact_match(
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
    assert metric["reason"] == "prediction_error"
    assert metric["comparison_mode"] == "value_only"


def test_answer_value_exact_match_is_not_comparable_for_missing_prediction() -> None:
    metric = compute_answer_value_exact_match(
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


def test_answer_value_exact_match_uses_numeric_literal_normalization() -> None:
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

    metric = compute_answer_value_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 1.0
