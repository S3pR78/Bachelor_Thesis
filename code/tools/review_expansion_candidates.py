from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.evaluate.dataset_loader import get_dataset_entries
from src.sparql.execution import detect_sparql_query_type, execute_sparql_query
from src.sparql.prefixes import prepend_orkg_prefixes


def load_dataset_object(input_path: Path) -> object:
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Candidate file not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_entry_label(entry: dict[str, Any], index: int) -> str:
    if not isinstance(entry, dict):
        return f"item_{index}"
    return str(entry.get("id") or f"item_{index}")


def summarize_select_result(response_json: dict[str, Any]) -> tuple[int | None, list[str]]:
    results = response_json.get("results", {})
    bindings = results.get("bindings", [])

    if not isinstance(bindings, list):
        return None, []

    cardinality = len(bindings)
    preview: list[str] = []

    for row in bindings[:3]:
        if not isinstance(row, dict):
            continue

        rendered_parts: list[str] = []
        for var_name, value_obj in row.items():
            if not isinstance(value_obj, dict):
                continue
            value = value_obj.get("value")
            if value is None:
                continue
            rendered_parts.append(f"{var_name}={value}")

        if rendered_parts:
            preview.append("; ".join(rendered_parts))

    return cardinality, preview


def summarize_ask_result(response_json: dict[str, Any]) -> tuple[int | None, list[str]]:
    boolean_value = response_json.get("boolean")
    if isinstance(boolean_value, bool):
        return 1 if boolean_value else 0, [f"boolean={boolean_value}"]
    return None, []

def classify_review_bucket(
    execution_status: str,
    result_cardinality: int | None,
) -> str:
    if execution_status == "error":
        return "red"
    if execution_status == "skipped":
        return "yellow"
    if execution_status == "ok" and result_cardinality == 0:
        return "yellow"
    if execution_status == "ok" and result_cardinality is not None and result_cardinality > 0:
        return "green"
    return "yellow"


def review_entry(
    entry: dict[str, Any],
    endpoint_url: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    entry_id = str(entry.get("id", ""))
    family = entry.get("family")
    answer_type = entry.get("answer_type")
    question = entry.get("question")
    raw_query = entry.get("gold_sparql")

    if not isinstance(raw_query, str) or not raw_query.strip():
        return {
            "id": entry_id,
            "family": family,
            "answer_type": answer_type,
            "question": question,
            "execution_status": "error",
            "query_type": "unknown",
            "result_cardinality": None,
            "execution_error": "Missing or empty gold_sparql.",
            "sample_answer_preview": [],
            "review_bucket": "red",
        }

    query_with_prefixes = raw_query
    query_type = detect_sparql_query_type(query_with_prefixes)

    if query_type not in {"select", "ask"}:
        return {
            "id": entry_id,
            "family": family,
            "answer_type": answer_type,
            "question": question,
            "execution_status": "skipped",
            "query_type": query_type,
            "result_cardinality": None,
            "execution_error": f"Unsupported query type: {query_type}",
            "sample_answer_preview": [],
            "review_bucket": "yellow",
        }
    try:
        response_json = execute_sparql_query(
            query=query_with_prefixes,
            endpoint_url=endpoint_url,
            timeout_seconds=timeout_seconds,
        )

        if query_type == "select":
            result_cardinality, preview = summarize_select_result(response_json)
        else:
            result_cardinality, preview = summarize_ask_result(response_json)

        return {
            "id": entry_id,
            "family": family,
            "answer_type": answer_type,
            "question": question,
            "execution_status": "ok",
            "query_type": query_type,
            "result_cardinality": result_cardinality,
            "execution_error": None,
            "sample_answer_preview": preview,
            "review_bucket": classify_review_bucket("ok", result_cardinality),
        }

    except Exception as exc:
        return {
            "id": entry_id,
            "family": family,
            "answer_type": answer_type,
            "question": question,
            "execution_status": "error",
            "query_type": query_type,
            "result_cardinality": None,
            "execution_error": str(exc),
            "sample_answer_preview": [],
            "review_bucket": "red",
        }


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    ok_count = sum(1 for item in results if item["execution_status"] == "ok")
    error_count = sum(1 for item in results if item["execution_status"] == "error")
    skipped_count = sum(1 for item in results if item["execution_status"] == "skipped")
    empty_count = sum(
        1
        for item in results
        if item["execution_status"] == "ok" and item["result_cardinality"] == 0
    )

    green_count = sum(1 for item in results if item.get("review_bucket") == "green")
    yellow_count = sum(1 for item in results if item.get("review_bucket") == "yellow")
    red_count = sum(1 for item in results if item.get("review_bucket") == "red")

    return {
        "total_items": total,
        "ok_count": ok_count,
        "error_count": error_count,
        "skipped_count": skipped_count,
        "empty_result_count": empty_count,
        "green_count": green_count,
        "yellow_count": yellow_count,
        "red_count": red_count,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run lightweight execution review for generated expansion candidates."
    )
    parser.add_argument(
        "--candidate-file",
        required=True,
        help="Path to the generated candidate JSON file.",
    )
    parser.add_argument(
        "--sparql-endpoint",
        required=True,
        help="SPARQL endpoint URL.",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Path to save the execution review JSON.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=60,
        help="Timeout in seconds for each query execution.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for how many entries to review.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output file.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    candidate_path = Path(args.candidate_file)
    output_path = Path(args.output_file)

    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. Use --overwrite to replace it."
        )

    dataset_obj = load_dataset_object(candidate_path)
    entries = get_dataset_entries(dataset_obj)

    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be a positive integer.")
        entries = entries[: args.limit]

    results: list[dict[str, Any]] = []

    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            results.append(
                {
                    "id": build_entry_label({}, index),
                    "family": None,
                    "answer_type": None,
                    "question": None,
                    "execution_status": "error",
                    "query_type": "unknown",
                    "result_cardinality": None,
                    "execution_error": "Entry is not a JSON object.",
                    "sample_answer_preview": [],
                    "review_bucket": "red",
                }
            )
            continue

        result = review_entry(
            entry=entry,
            endpoint_url=args.sparql_endpoint,
            timeout_seconds=args.timeout_seconds,
        )
        results.append(result)

        print(
            f"[{index}/{len(entries)}] id={result['id']} "
            f"status={result['execution_status']} "
            f"bucket={result['review_bucket']} "
            f"type={result['query_type']} "
            f"cardinality={result['result_cardinality']}"
        )

    payload = {
        "candidate_file": str(candidate_path),
        "sparql_endpoint": args.sparql_endpoint,
        "summary": build_summary(results),
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nSaved execution review to: {output_path}")
    print(f"Summary: {payload['summary']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise