"""Remove exact duplicate dataset entries and write a dedupe report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {path}. Use --overwrite to replace it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def make_pair_key(question: str, gold_sparql: str) -> str:
    return f"{normalize_text(question)}|||{normalize_text(gold_sparql)}"


def dedupe_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seen_questions: dict[str, str] = {}
    seen_queries: dict[str, str] = {}
    seen_pairs: dict[str, str] = {}

    unique_items: list[dict[str, Any]] = []

    duplicate_questions: list[dict[str, Any]] = []
    duplicate_queries: list[dict[str, Any]] = []
    duplicate_pairs: list[dict[str, Any]] = []

    removed_ids: set[str] = set()

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {index} is not a JSON object.")

        item_id = str(item.get("id", f"item_{index}"))
        question = item.get("question")
        gold_sparql = item.get("gold_sparql")

        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Entry {item_id} is missing a valid question.")
        if not isinstance(gold_sparql, str) or not gold_sparql.strip():
            raise ValueError(f"Entry {item_id} is missing a valid gold_sparql.")

        question_key = normalize_text(question)
        query_key = normalize_text(gold_sparql)
        pair_key = make_pair_key(question, gold_sparql)

        pair_duplicate = pair_key in seen_pairs
        question_duplicate = question_key in seen_questions
        query_duplicate = query_key in seen_queries

        if pair_duplicate:
            duplicate_pairs.append(
                {
                    "duplicate_id": item_id,
                    "kept_id": seen_pairs[pair_key],
                    "reason": "duplicate_question_and_query",
                }
            )
            removed_ids.add(item_id)
            continue

        if question_duplicate:
            duplicate_questions.append(
                {
                    "duplicate_id": item_id,
                    "kept_id": seen_questions[question_key],
                    "reason": "duplicate_question",
                }
            )
            removed_ids.add(item_id)
            continue

        if query_duplicate:
            duplicate_queries.append(
                {
                    "duplicate_id": item_id,
                    "kept_id": seen_queries[query_key],
                    "reason": "duplicate_gold_sparql",
                }
            )
            removed_ids.add(item_id)
            continue

        seen_questions[question_key] = item_id
        seen_queries[query_key] = item_id
        seen_pairs[pair_key] = item_id
        unique_items.append(item)

    report = {
        "input_count": len(items),
        "unique_count": len(unique_items),
        "removed_count": len(removed_ids),
        "duplicate_question_count": len(duplicate_questions),
        "duplicate_query_count": len(duplicate_queries),
        "duplicate_pair_count": len(duplicate_pairs),
        "duplicate_questions": duplicate_questions,
        "duplicate_queries": duplicate_queries,
        "duplicate_pairs": duplicate_pairs,
    }

    return unique_items, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove exact duplicate dataset entries by question, query, and question-query pair."
    )
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)
    report_path = Path(args.report_file)

    data = load_json(input_path)
    if not isinstance(data, list):
        raise ValueError("Expected a top-level JSON array.")

    unique_items, report = dedupe_items(data)

    save_json(output_path, unique_items, overwrite=args.overwrite)
    save_json(report_path, report, overwrite=args.overwrite)

    print(f"Saved deduplicated dataset to: {output_path}")
    print(f"Saved dedupe report to: {report_path}")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
