from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.sparql.execution import detect_sparql_query_type, execute_sparql_query
from src.sparql.prefixes import prepend_orkg_prefixes


def load_json_file(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_file(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {path}. Use --overwrite to replace it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_dataset_list(obj: Any, path: Path) -> list[dict[str, Any]]:
    if not isinstance(obj, list):
        raise ValueError(f"{path} must contain a top-level JSON array.")
    for index, item in enumerate(obj, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {index} in {path} is not a JSON object.")
    return obj


def build_sample_answer_preview(result: Any, query_type: str, max_items: int = 3) -> list[str]:
    preview: list[str] = []

    if query_type == "ask":
        if isinstance(result, dict) and "boolean" in result:
            preview.append(f"boolean={result['boolean']}")
        return preview

    if not isinstance(result, dict):
        return preview

    bindings = (
        result.get("results", {}).get("bindings", [])
        if isinstance(result.get("results"), dict)
        else []
    )

    for row in bindings[:max_items]:
        if not isinstance(row, dict):
            continue

        parts: list[str] = []
        for key, value_obj in row.items():
            if isinstance(value_obj, dict):
                value = value_obj.get("value")
                parts.append(f"{key}={value}")
            else:
                parts.append(f"{key}={value_obj}")

        preview.append("; ".join(parts))

    return preview


def compute_result_cardinality(result: Any, query_type: str) -> int:
    if query_type == "ask":
        if isinstance(result, dict) and "boolean" in result:
            return 1
        return 0

    if not isinstance(result, dict):
        return 0

    results_obj = result.get("results")
    if not isinstance(results_obj, dict):
        return 0

    bindings = results_obj.get("bindings")
    if not isinstance(bindings, list):
        return 0

    return len(bindings)


def validate_dataset_execution(
    items: list[dict[str, Any]],
    endpoint_url: str,
    timeout_seconds: int,
    limit: int | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    effective_items = items[:limit] if limit is not None else items

    ok_count = 0
    error_count = 0
    empty_result_count = 0

    problematic_entries: list[dict[str, Any]] = []

    for index, item in enumerate(effective_items, start=1):
        item_id = str(item.get("id", f"item_{index}"))
        family = item.get("family")
        question = item.get("question")
        answer_type = item.get("answer_type")
        gold_sparql = item.get("gold_sparql")

        if not isinstance(gold_sparql, str) or not gold_sparql.strip():
            result_row = {
                "id": item_id,
                "family": family,
                "answer_type": answer_type,
                "question": question,
                "execution_status": "error",
                "query_type": None,
                "result_cardinality": 0,
                "execution_error": "Missing or invalid gold_sparql",
                "sample_answer_preview": [],
            }
            results.append(result_row)
            error_count += 1
            problematic_entries.append(result_row)
            continue

        full_query = prepend_orkg_prefixes(gold_sparql)
        query_type = detect_sparql_query_type(full_query)

        try:
            response = execute_sparql_query(
                query=full_query,
                endpoint_url=endpoint_url,
                timeout_seconds=timeout_seconds,
            )

            result_cardinality = compute_result_cardinality(response, query_type)
            preview = build_sample_answer_preview(response, query_type)

            result_row = {
                "id": item_id,
                "family": family,
                "answer_type": answer_type,
                "question": question,
                "execution_status": "ok",
                "query_type": query_type,
                "result_cardinality": result_cardinality,
                "execution_error": None,
                "sample_answer_preview": preview,
            }
            results.append(result_row)
            ok_count += 1

            if result_cardinality == 0:
                empty_result_count += 1
                problematic_entries.append(
                    {
                        "id": item_id,
                        "family": family,
                        "answer_type": answer_type,
                        "question": question,
                        "execution_status": "ok",
                        "query_type": query_type,
                        "result_cardinality": 0,
                        "execution_error": None,
                        "problem_type": "empty_result",
                    }
                )

        except Exception as exc:  # noqa: BLE001
            result_row = {
                "id": item_id,
                "family": family,
                "answer_type": answer_type,
                "question": question,
                "execution_status": "error",
                "query_type": query_type,
                "result_cardinality": 0,
                "execution_error": str(exc),
                "sample_answer_preview": [],
            }
            results.append(result_row)
            error_count += 1
            problematic_entries.append(
                {
                    "id": item_id,
                    "family": family,
                    "answer_type": answer_type,
                    "question": question,
                    "execution_status": "error",
                    "query_type": query_type,
                    "result_cardinality": 0,
                    "execution_error": str(exc),
                    "problem_type": "execution_error",
                }
            )

    summary = {
        "total_items": len(effective_items),
        "ok_count": ok_count,
        "error_count": error_count,
        "empty_result_count": empty_result_count,
        "non_empty_result_count": ok_count - empty_result_count,
    }

    return {
        "dataset_path": None,
        "endpoint_url": endpoint_url,
        "timeout_seconds": timeout_seconds,
        "summary": summary,
        "problematic_entries": problematic_entries,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute all gold SPARQL queries in a dataset against an endpoint and export a validation report."
    )
    parser.add_argument("--dataset", required=True, help="Path to the dataset JSON file.")
    parser.add_argument("--endpoint", required=True, help="SPARQL endpoint URL.")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the full execution validation report JSON file.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=60,
        help="Timeout in seconds per query execution.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for the number of entries to validate.",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)

    items = ensure_dataset_list(load_json_file(dataset_path), dataset_path)
    report = validate_dataset_execution(
        items=items,
        endpoint_url=args.endpoint,
        timeout_seconds=args.timeout_seconds,
        limit=args.limit,
    )
    report["dataset_path"] = str(dataset_path)

    save_json_file(output_path, report, overwrite=args.overwrite)

    print(f"Execution validation report written to: {output_path}")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise