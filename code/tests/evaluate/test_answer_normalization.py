from __future__ import annotations

import pytest

from src.evaluate.answer_normalization import normalize_execution_result


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


def test_none_execution_result_is_missing() -> None:
    assert normalize_execution_result(None) == {"kind": "missing"}


def test_skipped_execution_result_is_missing_with_reason() -> None:
    result = normalize_execution_result(
        {
            "status": "skipped",
            "reason": "no_query",
        }
    )

    assert result == {
        "kind": "missing",
        "status": "skipped",
        "reason": "no_query",
    }


def test_error_execution_result_is_error_with_reason() -> None:
    result = normalize_execution_result(
        {
            "status": "error",
            "error": "endpoint_bad_request",
        }
    )

    assert result == {
        "kind": "error",
        "status": "error",
        "reason": "endpoint_bad_request",
    }


def test_ask_result_is_normalized() -> None:
    assert normalize_execution_result(ok_ask(True)) == {
        "kind": "ask",
        "value": True,
    }


def test_select_row_order_and_variable_order_do_not_matter() -> None:
    select_a = ok_select(
        [
            {
                "paper": uri("http://orkg.org/orkg/resource/R1"),
                "label": lit("Paper A", lang="en"),
            },
            {
                "paper": uri("http://orkg.org/orkg/resource/R2"),
                "label": lit("Paper B", lang="en"),
            },
        ]
    )

    select_b = ok_select(
        [
            {
                "label": lit("Paper B", lang="en"),
                "paper": uri("http://orkg.org/orkg/resource/R2"),
            },
            {
                "label": lit("Paper A", lang="en"),
                "paper": uri("http://orkg.org/orkg/resource/R1"),
            },
        ]
    )

    assert normalize_execution_result(select_a) == normalize_execution_result(select_b)


def test_duplicate_select_rows_are_currently_collapsed() -> None:
    result = normalize_execution_result(
        ok_select(
            [
                {
                    "paper": uri("http://orkg.org/orkg/resource/R1"),
                },
                {
                    "paper": uri("http://orkg.org/orkg/resource/R1"),
                },
            ]
        )
    )

    assert result["kind"] == "select"
    assert result["row_count"] == 1


def test_different_variable_names_are_currently_strict() -> None:
    by_paper_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "paper": uri("http://orkg.org/orkg/resource/R1"),
                }
            ]
        )
    )

    by_resource_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "resource": uri("http://orkg.org/orkg/resource/R1"),
                }
            ]
        )
    )

    assert by_paper_variable != by_resource_variable


def test_numeric_literal_datatype_differences_are_normalized() -> None:
    integer_result = normalize_execution_result(
        ok_select(
            [
                {
                    "count": lit(
                        "1",
                        datatype="http://www.w3.org/2001/XMLSchema#integer",
                    )
                }
            ]
        )
    )

    decimal_result = normalize_execution_result(
        ok_select(
            [
                {
                    "count": lit(
                        "1.0",
                        datatype="http://www.w3.org/2001/XMLSchema#decimal",
                    )
                }
            ]
        )
    )

    assert integer_result == decimal_result


def test_invalid_select_bindings_raise_value_error() -> None:
    with pytest.raises(ValueError):
        normalize_execution_result(
            {
                "status": "ok",
                "result_type": "select",
                "response_json": {
                    "results": {
                        "bindings": "not-a-list",
                    }
                },
            }
        )


def test_invalid_ask_boolean_raises_value_error() -> None:
    with pytest.raises(ValueError):
        normalize_execution_result(
            {
                "status": "ok",
                "result_type": "ask",
                "response_json": {
                    "boolean": "true",
                },
            }
        )


def test_plain_literal_numbers_without_numeric_datatype_stay_strict() -> None:
    plain_one = normalize_execution_result(
        ok_select(
            [
                {
                    "label": lit("1"),
                }
            ]
        )
    )

    plain_one_with_leading_zero = normalize_execution_result(
        ok_select(
            [
                {
                    "label": lit("01"),
                }
            ]
        )
    )

    assert plain_one != plain_one_with_leading_zero



def test_value_only_select_mode_ignores_variable_names() -> None:
    by_name_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        ),
        select_mode="value_only",
    )

    by_lastname_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "nachname": lit("Smith"),
                }
            ]
        ),
        select_mode="value_only",
    )

    assert by_name_variable == by_lastname_variable


def test_strict_select_mode_keeps_variable_names() -> None:
    by_name_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        ),
        select_mode="strict",
    )

    by_lastname_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "nachname": lit("Smith"),
                }
            ]
        ),
        select_mode="strict",
    )

    assert by_name_variable != by_lastname_variable


def test_value_only_select_mode_preserves_multi_column_row_content() -> None:
    prediction = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                    "paper": uri("http://orkg.org/orkg/resource/R1"),
                }
            ]
        ),
        select_mode="value_only",
    )

    gold = normalize_execution_result(
        ok_select(
            [
                {
                    "surname": lit("Smith"),
                    "publication": uri("http://orkg.org/orkg/resource/R1"),
                }
            ]
        ),
        select_mode="value_only",
    )

    assert prediction == gold


def test_invalid_select_mode_raises_value_error() -> None:
    with pytest.raises(ValueError):
        normalize_execution_result(
            ok_select([]),
            select_mode="unknown",
        )

def test_value_only_select_mode_ignores_variable_names() -> None:
    by_name_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        ),
        select_mode="value_only",
    )

    by_lastname_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "nachname": lit("Smith"),
                }
            ]
        ),
        select_mode="value_only",
    )

    assert by_name_variable == by_lastname_variable


def test_strict_select_mode_keeps_variable_names() -> None:
    by_name_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        ),
        select_mode="strict",
    )

    by_lastname_variable = normalize_execution_result(
        ok_select(
            [
                {
                    "nachname": lit("Smith"),
                }
            ]
        ),
        select_mode="strict",
    )

    assert by_name_variable != by_lastname_variable


def test_default_select_mode_is_strict() -> None:
    default_mode = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        )
    )

    explicit_strict_mode = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        ),
        select_mode="strict",
    )

    assert default_mode == explicit_strict_mode


def test_value_only_select_mode_preserves_multi_column_row_content() -> None:
    prediction = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                    "paper": uri("http://orkg.org/orkg/resource/R1"),
                }
            ]
        ),
        select_mode="value_only",
    )

    gold = normalize_execution_result(
        ok_select(
            [
                {
                    "surname": lit("Smith"),
                    "publication": uri("http://orkg.org/orkg/resource/R1"),
                }
            ]
        ),
        select_mode="value_only",
    )

    assert prediction == gold


def test_value_only_select_mode_still_detects_wrong_values() -> None:
    prediction = normalize_execution_result(
        ok_select(
            [
                {
                    "name": lit("Smith"),
                }
            ]
        ),
        select_mode="value_only",
    )

    gold = normalize_execution_result(
        ok_select(
            [
                {
                    "nachname": lit("Miller"),
                }
            ]
        ),
        select_mode="value_only",
    )

    assert prediction != gold


def test_invalid_select_mode_raises_value_error() -> None:
    with pytest.raises(ValueError):
        normalize_execution_result(
            ok_select([]),
            select_mode="unknown",
        )
