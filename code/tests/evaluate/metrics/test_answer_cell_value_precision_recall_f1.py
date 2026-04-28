from __future__ import annotations

from src.evaluate.metrics.answer_cell_value_precision_recall_f1 import (
    compute_answer_cell_value_precision_recall_f1,
)


def uri(value: str) -> dict:
    return {
        "type": "uri",
        "value": value,
    }


def literal(value: str, datatype: str | None = None, lang: str | None = None) -> dict:
    payload = {
        "type": "literal",
        "value": value,
    }
    if datatype:
        payload["datatype"] = datatype
        payload["type"] = "typed-literal"
    if lang:
        payload["xml:lang"] = lang
    return payload


def ok_select(bindings: list[dict]) -> dict:
    return {
        "status": "ok",
        "result_type": "select",
        "response_json": {
            "head": {
                "vars": [],
            },
            "results": {
                "bindings": bindings,
            },
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


def error_execution() -> dict:
    return {
        "status": "error",
        "result_type": "select",
        "error": "bad request",
    }


def test_cell_value_f1_is_one_for_same_values_with_different_variables() -> None:
    prediction_execution = ok_select(
        [
            {
                "publication": uri("http://orkg.org/orkg/resource/R1"),
                "publicationYear": literal(
                    "1993",
                    "http://www.w3.org/2001/XMLSchema#integer",
                ),
            }
        ]
    )
    gold_execution = ok_select(
        [
            {
                "paper": uri("http://orkg.org/orkg/resource/R1"),
                "year": literal(
                    "1993",
                    "http://www.w3.org/2001/XMLSchema#integer",
                ),
            }
        ]
    )

    metric = compute_answer_cell_value_precision_recall_f1(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    assert metric["metric"] == "answer_cell_value_precision_recall_f1"
    assert metric["type"] == "answer_based"
    assert metric["comparable"] is True
    assert metric["comparison_mode"] == "cell_value_only_unique"
    assert metric["precision"] == 1.0
    assert metric["recall"] == 1.0
    assert metric["f1"] == 1.0
    assert metric["prediction_value_count"] == 2
    assert metric["gold_value_count"] == 2
    assert metric["true_positive_value_count"] == 2


def test_cell_value_f1_detects_partial_overlap() -> None:
    prediction_execution = ok_select(
        [
            {
                "paper": uri("http://orkg.org/orkg/resource/R1"),
                "year": literal(
                    "1993",
                    "http://www.w3.org/2001/XMLSchema#integer",
                ),
                "label": literal("Paper A"),
            }
        ]
    )
    gold_execution = ok_select(
        [
            {
                "paper": uri("http://orkg.org/orkg/resource/R1"),
                "year": literal(
                    "1994",
                    "http://www.w3.org/2001/XMLSchema#integer",
                ),
            }
        ]
    )

    metric = compute_answer_cell_value_precision_recall_f1(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    assert metric["comparable"] is True
    assert metric["precision"] == 0.3333
    assert metric["recall"] == 0.5
    assert metric["f1"] == 0.4
    assert metric["prediction_value_count"] == 3
    assert metric["gold_value_count"] == 2
    assert metric["true_positive_value_count"] == 1


def test_cell_value_f1_normalizes_numeric_and_boolean_literals() -> None:
    prediction_execution = ok_select(
        [
            {
                "year": literal(
                    "1993.0",
                    "http://www.w3.org/2001/XMLSchema#decimal",
                ),
                "flag": literal(
                    "1",
                    "http://www.w3.org/2001/XMLSchema#boolean",
                ),
            }
        ]
    )
    gold_execution = ok_select(
        [
            {
                "year": literal(
                    "1993",
                    "http://www.w3.org/2001/XMLSchema#integer",
                ),
                "flag": literal(
                    "true",
                    "http://www.w3.org/2001/XMLSchema#boolean",
                ),
            }
        ]
    )

    metric = compute_answer_cell_value_precision_recall_f1(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    assert metric["comparable"] is True
    assert metric["precision"] == 0.5
    assert metric["recall"] == 0.5
    assert metric["f1"] == 0.5


def test_cell_value_f1_for_ask_queries() -> None:
    metric = compute_answer_cell_value_precision_recall_f1(
        prediction_execution=ok_ask(True),
        gold_execution=ok_ask(True),
    )

    assert metric["comparable"] is True
    assert metric["precision"] == 1.0
    assert metric["recall"] == 1.0
    assert metric["f1"] == 1.0


def test_cell_value_f1_for_different_ask_queries() -> None:
    metric = compute_answer_cell_value_precision_recall_f1(
        prediction_execution=ok_ask(False),
        gold_execution=ok_ask(True),
    )

    assert metric["comparable"] is True
    assert metric["precision"] == 0.0
    assert metric["recall"] == 0.0
    assert metric["f1"] == 0.0


def test_cell_value_f1_is_not_comparable_without_prediction() -> None:
    metric = compute_answer_cell_value_precision_recall_f1(
        prediction_execution=None,
        gold_execution=ok_select([]),
    )

    assert metric["comparable"] is False
    assert metric["reason"] == "prediction_missing"


def test_cell_value_f1_is_not_comparable_for_prediction_error() -> None:
    metric = compute_answer_cell_value_precision_recall_f1(
        prediction_execution=error_execution(),
        gold_execution=ok_select([]),
    )

    assert metric["comparable"] is False
    assert metric["reason"] == "prediction_error"
