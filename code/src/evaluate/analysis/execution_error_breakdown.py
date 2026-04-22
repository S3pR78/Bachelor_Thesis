from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SUPPORTED_QUERY_FORMS = {"select", "ask"}
AGGREGATE_FUNCTIONS = (
    "COUNT(",
    "SUM(",
    "AVG(",
    "MIN(",
    "MAX(",
    "GROUP_CONCAT(",
    "SAMPLE(",
)


def _normalize_whitespace(text: str) -> str:
    return " ".join((text or "").split())


def _contains_escaped_formatting(query: str) -> bool:
    return "\\n" in query or "\\t" in query or '\\"' in query


def _looks_truncated(query: str) -> bool:
    if not query or not query.strip():
        return False

    stripped = query.strip()

    if stripped.count("{") != stripped.count("}"):
        return True

    if stripped.count("(") != stripped.count(")"):
        return True

    suspicious_endings = (" AS", " AS ?", "||", "&&", ";", "{", "(")
    if any(stripped.endswith(ending) for ending in suspicious_endings):
        return True

    return False


def _likely_missing_group_by(query: str) -> bool:
    upper = _normalize_whitespace(query.upper())

    if "SELECT" not in upper or "WHERE" not in upper:
        return False

    if "GROUP BY" in upper:
        return False

    if not any(func in upper for func in AGGREGATE_FUNCTIONS):
        return False

    select_part = upper.split("WHERE", 1)[0]

    return bool(
        re.search(
            r"SELECT\s+(?:DISTINCT\s+|REDUCED\s+)?\?[A-Z_][A-Z0-9_]*",
            select_part,
        )
    )


def _extract_http_status(error_message: str) -> str | None:
    match = re.search(r"(\d{3})\s+Client Error", error_message)
    if match:
        return match.group(1)
    return None


def _compact_error_signature(error_message: str) -> str:
    if not error_message:
        return "no_error_message"

    message = error_message.split(" for url:", 1)[0]
    message = _normalize_whitespace(message)

    if len(message) > 200:
        return message[:200] + "..."

    return message


def classify_result_entry(result: dict[str, Any]) -> dict[str, Any]:
    validation = result.get("validation") or {}
    primary_error_category = validation.get("primary_error_category")

    entry_id = result.get("id")
    extracted_query = result.get("extracted_query") or ""
    prediction_query_form = result.get("prediction_query_form")
    query_execution = result.get("query_execution") or {}
    gold_execution = result.get("gold_execution") or {}

    prediction_status = query_execution.get("status")
    prediction_error = str(query_execution.get("error") or "")

    category = "unknown"
    details: dict[str, Any] = {}

    if gold_execution.get("status") == "error" or primary_error_category == "gold_execution_error":
        category = "gold_execution_error"
        details["error_signature"] = _compact_error_signature(
            str(gold_execution.get("error") or "")
        )

    elif not result.get("has_extracted_query"):
        category = "no_extracted_query"

    elif prediction_query_form not in SUPPORTED_QUERY_FORMS:
        category = "unsupported_query_form"
        details["prediction_query_form"] = prediction_query_form

    elif prediction_status == "error":
        if prediction_error.startswith("query_preparation_failed"):
            category = "query_preparation_failed"

        elif _contains_escaped_formatting(extracted_query):
            category = "likely_escaped_query_formatting"

        elif _looks_truncated(extracted_query):
            category = "likely_truncated_query"

        elif _likely_missing_group_by(extracted_query):
            category = "likely_missing_group_by"

        else:
            http_status = _extract_http_status(prediction_error)
            if http_status == "400":
                category = "endpoint_bad_request"
            elif http_status is not None:
                category = f"endpoint_http_{http_status}"
            else:
                category = "prediction_execution_error_other"

        details["error_signature"] = _compact_error_signature(prediction_error)

    elif prediction_status == "skipped":
        category = "prediction_execution_skipped"
        details["reason"] = query_execution.get("reason")

    elif prediction_status == "ok":
        if primary_error_category == "answer_mismatch":
            category = "answer_mismatch"
        else:
            category = "success"

    else:
        category = "unknown_prediction_status"
        details["prediction_status"] = prediction_status

    return {
        "id": entry_id,
        "category": category,
        "primary_error_category": primary_error_category,
        "prediction_status": prediction_status,
        "details": details,
    }


def build_execution_error_breakdown(results: list[dict[str, Any]]) -> dict[str, Any]:
    category_counter: Counter[str] = Counter()
    signature_counter: Counter[str] = Counter()
    examples_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for result in results:
        classified = classify_result_entry(result)
        category = classified["category"]
        category_counter[category] += 1

        details = classified.get("details") or {}
        error_signature = details.get("error_signature")
        if error_signature:
            signature_counter[str(error_signature)] += 1

        if len(examples_by_category[category]) < 3:
            examples_by_category[category].append(
                {
                    "id": classified.get("id"),
                    "primary_error_category": classified.get("primary_error_category"),
                    "prediction_status": classified.get("prediction_status"),
                    "details": details,
                }
            )

    return {
        "total_items": len(results),
        "category_counts": dict(sorted(category_counter.items())),
        "top_error_signatures": [
            {"signature": signature, "count": count}
            for signature, count in signature_counter.most_common(10)
        ],
        "examples_by_category": dict(sorted(examples_by_category.items())),
    }


def load_results_from_raw_file(raw_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    results = payload.get("results")

    if not isinstance(results, list):
        raise ValueError("benchmark_raw.json does not contain a valid 'results' list.")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build execution error breakdown from benchmark_raw.json"
    )
    parser.add_argument("raw_path", help="Path to benchmark_raw.json")
    parser.add_argument(
        "--output",
        help="Optional path to save execution_error_breakdown.json",
        default=None,
    )
    args = parser.parse_args()

    raw_path = Path(args.raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"File not found: {raw_path}")

    results = load_results_from_raw_file(raw_path)
    breakdown = build_execution_error_breakdown(results)

    print(json.dumps(breakdown, indent=2, ensure_ascii=False))

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(breakdown, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nSaved breakdown to: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
