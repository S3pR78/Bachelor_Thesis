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


DEFAULT_SPLITS = ["train", "validation", "test"]


def load_json(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_matching_sparql_lines(
    sparql: str,
    term: str,
    max_lines: int = 5,
) -> list[str]:
    lines = []

    for line in sparql.splitlines():
        if term in line:
            lines.append(line.strip())

        if len(lines) >= max_lines:
            break

    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect PGMR-lite unmapped ORKG identifiers across final dataset splits."
        )
    )

    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("code/data/dataset/final"),
        help="Directory containing train.json, validation.json, and test.json.",
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        default=Path("code/data/orkg_memory/templates"),
        help="Directory containing *_memory.json files.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=DEFAULT_SPLITS,
        help="Dataset split names to inspect.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("code/outputs/pgmr/unmapped_terms_summary.json"),
        help="Output path for the unmapped terms summary JSON.",
    )
    parser.add_argument(
        "--max-examples-per-term",
        type=int,
        default=5,
        help="Maximum number of examples to store for each unmapped term.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    memory_entries = load_memory_dir(args.memory_dir)
    validate_memory_entries(memory_entries)
    uri_to_placeholder_by_family = build_uri_to_placeholder_map(memory_entries)

    status_counts: Counter[str] = Counter()
    split_item_counts: Counter[str] = Counter()

    unmapped_index: dict[tuple[str, str], dict[str, Any]] = {}

    for split in args.splits:
        split_path = args.dataset_dir / f"{split}.json"
        data = load_json(split_path)

        if not isinstance(data, list):
            raise ValueError(f"Expected JSON list in {split_path}")

        split_item_counts[split] = len(data)

        for index, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise ValueError(f"Entry {index} in {split_path} is not an object.")

            family = str(entry.get("family", "")).strip()
            gold_sparql = str(entry.get("gold_sparql", ""))

            result = transform_sparql_to_pgmr(
                sparql=gold_sparql,
                family=family,
                uri_to_placeholder_by_family=uri_to_placeholder_by_family,
            )

            status_counts[result.status] += 1

            for term in result.unmapped_terms:
                key = (family, term)

                if key not in unmapped_index:
                    unmapped_index[key] = {
                        "family": family,
                        "canonical_uri": term,
                        "total_entries": 0,
                        "split_counts": {name: 0 for name in args.splits},
                        "examples": [],
                    }

                record = unmapped_index[key]
                record["total_entries"] += 1
                record["split_counts"][split] += 1

                if len(record["examples"]) < args.max_examples_per_term:
                    record["examples"].append(
                        {
                            "split": split,
                            "id": entry.get("id"),
                            "family": family,
                            "question": entry.get("question"),
                            "pgmr_status": result.status,
                            "matching_sparql_lines": extract_matching_sparql_lines(
                                gold_sparql,
                                term,
                            ),
                        }
                    )

    unmapped_terms = sorted(
        unmapped_index.values(),
        key=lambda item: (-item["total_entries"], item["family"], item["canonical_uri"]),
    )

    summary = {
        "dataset_dir": str(args.dataset_dir),
        "memory_dir": str(args.memory_dir),
        "splits": args.splits,
        "split_item_counts": dict(split_item_counts),
        "status_counts": dict(status_counts),
        "total_unmapped_unique_family_uri_pairs": len(unmapped_terms),
        "unmapped_terms": unmapped_terms,
    }

    save_json(args.output, summary)

    print(json.dumps(
        {
            "dataset_dir": summary["dataset_dir"],
            "memory_dir": summary["memory_dir"],
            "split_item_counts": summary["split_item_counts"],
            "status_counts": summary["status_counts"],
            "total_unmapped_unique_family_uri_pairs": summary[
                "total_unmapped_unique_family_uri_pairs"
            ],
            "output": str(args.output),
        },
        ensure_ascii=False,
        indent=2,
    ))

    if unmapped_terms:
        print("\nTop unmapped terms:\n")
        header = f"{'family':35} {'uri':25} {'total':>6} {'train':>6} {'val':>6} {'test':>6}"
        print(header)
        print("-" * len(header))

        for item in unmapped_terms[:50]:
            split_counts = item["split_counts"]
            print(
                f"{item['family'][:35]:35} "
                f"{item['canonical_uri'][:25]:25} "
                f"{item['total_entries']:6} "
                f"{split_counts.get('train', 0):6} "
                f"{split_counts.get('validation', 0):6} "
                f"{split_counts.get('test', 0):6}"
            )

        print(f"\nFull summary written to: {args.output}")
    else:
        print("\nNo unmapped terms found. PGMR memory covers all detected ORKG identifiers.")


if __name__ == "__main__":
    main()