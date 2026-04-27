from __future__ import annotations

from src.evaluate.metrics.answer_exact_match import compute_answer_exact_match
from src.evaluate.metrics.answer_precision_recall_f1 import compute_answer_precision_recall_f1


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


def test_answer_exact_match_for_equal_ask_answers() -> None:
    metric = compute_answer_exact_match(
        prediction_execution=ok_ask(True),
        gold_execution=ok_ask(True),
    )

    assert metric["metric"] == "answer_exact_match"
    assert metric["type"] == "answer_based"
    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["prediction_kind"] == "ask"
    assert metric["gold_kind"] == "ask"


def test_answer_exact_match_for_different_ask_answers() -> None:
    metric = compute_answer_exact_match(
        prediction_execution=ok_ask(False),
        gold_execution=ok_ask(True),
    )

    assert metric["comparable"] is True
    assert metric["value"] == 0.0


def test_answer_exact_match_for_equal_select_answers_ignores_row_order() -> None:
    prediction = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R2")},
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
        ]
    )

    gold = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
            {"paper": uri("http://orkg.org/orkg/resource/R2")},
        ]
    )

    metric = compute_answer_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["prediction_row_count"] == 2
    assert metric["gold_row_count"] == 2


def test_answer_exact_match_for_partial_select_overlap_is_zero() -> None:
    prediction = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
            {"paper": uri("http://orkg.org/orkg/resource/R2")},
        ]
    )

    gold = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
            {"paper": uri("http://orkg.org/orkg/resource/R3")},
        ]
    )

    metric = compute_answer_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 0.0


def test_answer_precision_recall_f1_for_partial_select_overlap() -> None:
    prediction = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
            {"paper": uri("http://orkg.org/orkg/resource/R2")},
        ]
    )

    gold = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
            {"paper": uri("http://orkg.org/orkg/resource/R3")},
        ]
    )

    metric = compute_answer_precision_recall_f1(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert metric["metric"] == "answer_precision_recall_f1"
    assert metric["type"] == "answer_based"
    assert metric["comparable"] is True
    assert metric["true_positives"] == 1
    assert metric["prediction_row_count"] == 2
    assert metric["gold_row_count"] == 2
    assert metric["precision"] == 0.5
    assert metric["recall"] == 0.5
    assert metric["f1"] == 0.5
    assert metric["value"] == 0.5


def test_answer_precision_recall_f1_for_empty_select_answers() -> None:
    metric = compute_answer_precision_recall_f1(
        prediction_execution=ok_select([]),
        gold_execution=ok_select([]),
    )

    assert metric["comparable"] is True
    assert metric["precision"] == 1.0
    assert metric["recall"] == 1.0
    assert metric["f1"] == 1.0
    assert metric["value"] == 1.0


def test_answer_metrics_are_not_comparable_for_prediction_execution_error() -> None:
    exact_match = compute_answer_exact_match(
        prediction_execution=error_execution(),
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
    )

    f1 = compute_answer_precision_recall_f1(
        prediction_execution=error_execution(),
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
    )

    assert exact_match["comparable"] is False
    assert exact_match["value"] is None
    assert exact_match["reason"] == "prediction_error"

    assert f1["comparable"] is False
    assert f1["value"] is None
    assert f1["reason"] == "prediction_error"


def test_numeric_literal_normalization_reaches_answer_metrics() -> None:
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
                "count": lit(
                    "1.0",
                    datatype="http://www.w3.org/2001/XMLSchema#decimal",
                )
            }
        ]
    )

    exact_match = compute_answer_exact_match(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    f1 = compute_answer_precision_recall_f1(
        prediction_execution=prediction,
        gold_execution=gold,
    )

    assert exact_match["comparable"] is True
    assert exact_match["value"] == 1.0

    assert f1["comparable"] is True
    assert f1["precision"] == 1.0
    assert f1["recall"] == 1.0
    assert f1["f1"] == 1.0
