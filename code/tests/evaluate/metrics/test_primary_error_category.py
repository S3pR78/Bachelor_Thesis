from __future__ import annotations

from src.evaluate.metrics.primary_error_category import compute_primary_error_category


ENDPOINT_URL = "https://www.orkg.org/triplestore"


def ok_execution() -> dict:
    return {
        "status": "ok",
        "result_type": "select",
        "response_json": {
            "head": {"vars": []},
            "results": {"bindings": []},
        },
    }


def error_execution() -> dict:
    return {
        "status": "error",
        "error": "endpoint_bad_request",
    }


def exact_match(value: float | None, comparable: bool = True) -> dict:
    return {
        "metric": "answer_exact_match",
        "type": "answer_based",
        "comparable": comparable,
        "value": value,
    }


def test_primary_error_category_marks_extraction_failure() -> None:
    category = compute_primary_error_category(
        has_extracted_query=False,
        prediction_query_form=None,
        gold_query_form="select",
        prediction_execution={},
        gold_execution=ok_execution(),
        answer_exact_match=exact_match(None, comparable=False),
        endpoint_url=ENDPOINT_URL,
    )

    assert category == "extraction_failure"


def test_primary_error_category_marks_prediction_execution_error() -> None:
    category = compute_primary_error_category(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=error_execution(),
        gold_execution=ok_execution(),
        answer_exact_match=exact_match(None, comparable=False),
        endpoint_url=ENDPOINT_URL,
    )

    assert category == "prediction_execution_error"


def test_primary_error_category_marks_answer_mismatch() -> None:
    category = compute_primary_error_category(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=ok_execution(),
        gold_execution=ok_execution(),
        answer_exact_match=exact_match(0.0),
        endpoint_url=ENDPOINT_URL,
    )

    assert category == "answer_mismatch"


def test_primary_error_category_marks_success_explicitly() -> None:
    category = compute_primary_error_category(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=ok_execution(),
        gold_execution=ok_execution(),
        answer_exact_match=exact_match(1.0),
        endpoint_url=ENDPOINT_URL,
    )

    assert category == "success"
