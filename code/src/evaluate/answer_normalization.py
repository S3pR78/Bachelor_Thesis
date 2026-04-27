from __future__ import annotations
"""
Normalize executed SPARQL answers for answer-based evaluation.

This module does not compare SPARQL query strings. It normalizes execution
outputs so that answer-based metrics such as exact match and precision/recall/F1
can compare ASK booleans or SELECT result rows.

Current SELECT behavior:
- row order does not matter
- variable order inside a row does not matter
- duplicate rows are collapsed because rows are represented as a set
- variable names are part of the normalized answer
- literal datatypes and language tags are part of the normalized answer
"""

from typing import Any


def _normalize_binding_value(value_obj: dict[str, Any]) -> tuple[str, str, str, str]:
    value_type = str(value_obj.get("type", ""))
    value = str(value_obj.get("value", ""))
    datatype = str(value_obj.get("datatype", ""))
    language = str(value_obj.get("xml:lang", value_obj.get("lang", "")))
    return (value_type, value, datatype, language)


def _normalize_select_rows(response_json: dict[str, Any]) -> frozenset[tuple[tuple[str, str, str, str, str], ...]]:
    results = response_json.get("results", {})
    bindings = results.get("bindings", [])

    if not isinstance(bindings, list):
        raise ValueError("SELECT response_json.results.bindings must be a list.")

    normalized_rows = []

    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError("Each SELECT binding must be a dict.")

        normalized_row = []

        for variable_name, value_obj in binding.items():
            if not isinstance(value_obj, dict):
                raise ValueError("Each bound value must be a dict.")

            value_type, value, datatype, language = _normalize_binding_value(value_obj)
            normalized_row.append(
                (str(variable_name), value_type, value, datatype, language)
            )

        normalized_rows.append(tuple(sorted(normalized_row)))

    return frozenset(normalized_rows)


def normalize_execution_result(execution_result: dict[str, Any] | None) -> dict[str, Any]:
    if execution_result is None:
        return {"kind": "missing"}

    if not isinstance(execution_result, dict):
        raise ValueError("execution_result must be a dict or None.")

    status = execution_result.get("status")

    if status != "ok":
        if status == "skipped":
            return {
                "kind": "missing",
                "status": "skipped",
                "reason": execution_result.get("reason"),
            }

        return {
            "kind": "error",
            "status": status,
            "reason": execution_result.get("error") or execution_result.get("reason"),
        }

    result_type = execution_result.get("result_type")
    response_json = execution_result.get("response_json")

    if not isinstance(response_json, dict):
        raise ValueError("execution_result.response_json must be a dict when status='ok'.")

    if result_type == "ask":
        boolean_value = response_json.get("boolean")

        if not isinstance(boolean_value, bool):
            raise ValueError("ASK response_json.boolean must be a bool.")

        return {
            "kind": "ask",
            "value": boolean_value,
        }

    if result_type == "select":
        normalized_rows = _normalize_select_rows(response_json)
        return {
            "kind": "select",
            "rows": normalized_rows,
            "row_count": len(normalized_rows),
        }

    return {
        "kind": "unsupported",
        "result_type": result_type,
    }