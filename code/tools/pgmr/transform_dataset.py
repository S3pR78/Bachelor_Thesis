from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.pgmr.memory import (
    build_uri_to_placeholder_map,
    load_memory_dir,
    validate_memory_entries,
)
from src.pgmr.transform import transform_sparql_to_pgmr


def load_json(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transform gold SPARQL queries into PGMR-lite placeholder queries."
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input dataset JSON file, e.g. code/data/dataset/final/train.json",
    )
    parser.add_argument(
        "--memory-dir",
        default=Path("code/data/orkg_memory/templates"),
        type=Path,
        help="Directory containing *_memory.json files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path for the enriched PGMR dataset.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of dataset entries to process.",
    )
    parser.add_argument(
        "--print-examples",
        type=int,
        default=3,
        help="Number of transformed examples to print.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    memory_entries = load_memory_dir(args.memory_dir)
    validate_memory_entries(memory_entries)
    uri_to_placeholder_by_family = build_uri_to_placeholder_map(memory_entries)

    data = load_json(args.input)

    if not isinstance(data, list):
        raise ValueError("Expected the input dataset to be a JSON list.")

    items = data[: args.limit] if args.limit is not None else data

    enriched: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    unmapped_counts: Counter[str] = Counter()

    for index, entry in enumerate(items):
        if not isinstance(entry, dict):
            raise ValueError(f"Dataset entry at index {index} is not an object.")

        family = str(entry.get("family", ""))
        gold_sparql = str(entry.get("gold_sparql", ""))

        result = transform_sparql_to_pgmr(
            sparql=gold_sparql,
            family=family,
            uri_to_placeholder_by_family=uri_to_placeholder_by_family,
        )

        new_entry = dict(entry)
        new_entry["gold_pgmr_sparql"] = result.pgmr_sparql
        new_entry["pgmr_status"] = result.status
        new_entry["pgmr_replaced_terms"] = result.replaced_terms
        new_entry["pgmr_unmapped_terms"] = result.unmapped_terms

        enriched.append(new_entry)

        status_counts[result.status] += 1
        unmapped_counts.update(result.unmapped_terms)

    summary = {
        "input_path": str(args.input),
        "memory_dir": str(args.memory_dir),
        "processed_items": len(enriched),
        "status_counts": dict(status_counts),
        "top_unmapped_terms": unmapped_counts.most_common(30),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    for entry in enriched[: args.print_examples]:
        print("\n" + "=" * 80)
        print(f"id: {entry.get('id')}")
        print(f"family: {entry.get('family')}")
        print(f"question: {entry.get('question')}")
        print("\nGOLD SPARQL:")
        print(entry.get("gold_sparql"))
        print("\nPGMR SPARQL:")
        print(entry.get("gold_pgmr_sparql"))
        print("\nPGMR STATUS:")
        print(entry.get("pgmr_status"))
        print("unmapped:", entry.get("pgmr_unmapped_terms"))

    if args.output:
        save_json(args.output, enriched)
        print(f"\nWrote PGMR dataset to: {args.output}")


if __name__ == "__main__":
    main()