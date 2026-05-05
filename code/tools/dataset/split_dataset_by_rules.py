"""Assign dataset entries to final splits according to project rules."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


TEST_ALLOWED_SOURCE_DATASETS = {
    "EmpiRE_Compass",
    "Hybrid_NLP4RE",
    "Hybrid_Empirical_Research",
}

TEST_ALLOWED_REVIEW_STATUS = {"approved"}
TEST_ALLOWED_GOLD_STATUS = {"final"}

VALIDATION_ALLOWED_REVIEW_STATUS = {"reviewed", "revised", "approved"}
VALIDATION_ALLOWED_GOLD_STATUS = {"validated", "final"}

TARGET_TEST_BY_FAMILY = {
    "nlp4re": 40,
    "empirical_research_practice": 40,
}

TARGET_VALIDATION_BY_FAMILY = {
    "nlp4re": 40,
    "empirical_research_practice": 40,
}

TARGET_TEST_ANSWER_TYPE = {
    "resource": 20,
    "string": 18,
    "number": 14,
    "date": 12,
    "mixed": 10,
    "list": 4,
    "boolean": 2,
}

TARGET_TEST_COMPLEXITY = {
    "low": 25,
    "medium": 35,
    "high": 20,
}

TARGET_VALIDATION_COMPLEXITY = {
    "low": 25,
    "medium": 35,
    "high": 20,
}


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


def has_paraphrase(item: dict[str, Any]) -> bool:
    value = item.get("paraphrased_questions")
    return isinstance(value, list) and len(value) > 0


def is_test_eligible(item: dict[str, Any]) -> bool:
    return (
        item.get("source_dataset") in TEST_ALLOWED_SOURCE_DATASETS
        and item.get("review_status") in TEST_ALLOWED_REVIEW_STATUS
        and item.get("gold_status") in TEST_ALLOWED_GOLD_STATUS
        and item.get("language") == "en"
        and has_paraphrase(item)
        and item.get("family") in TARGET_TEST_BY_FAMILY
    )


def is_validation_eligible(item: dict[str, Any]) -> bool:
    return (
        item.get("review_status") in VALIDATION_ALLOWED_REVIEW_STATUS
        and item.get("gold_status") in VALIDATION_ALLOWED_GOLD_STATUS
        and item.get("language") == "en"
        and has_paraphrase(item)
        and item.get("family") in TARGET_VALIDATION_BY_FAMILY
    )


def count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get(field, "__missing__"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def complexity_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(value, -1)


def source_rank_for_test(value: str) -> int:
    return {
        "EmpiRE_Compass": 0,
        "Hybrid_NLP4RE": 1,
        "Hybrid_Empirical_Research": 1,
    }.get(value, 9)


def source_rank_for_validation(value: str) -> int:
    return {
        "Hybrid_NLP4RE": 0,
        "Hybrid_Empirical_Research": 0,
        "EmpiRE_Compass": 1,
        "Generated_NLP4RE": 2,
        "Generated_Empirical_Research": 2,
    }.get(value, 9)


def sort_candidates_for_test(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            source_rank_for_test(str(item.get("source_dataset", ""))),
            -complexity_rank(str(item.get("complexity_level", ""))),
            str(item.get("id", "")),
        ),
    )


def sort_candidates_for_validation(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            source_rank_for_validation(str(item.get("source_dataset", ""))),
            -complexity_rank(str(item.get("complexity_level", ""))),
            str(item.get("id", "")),
        ),
    )


def pick_test_set(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = sort_candidates_for_test(candidates)

    selected: list[dict[str, Any]] = []

    family_counts: dict[str, int] = defaultdict(int)
    answer_type_counts: dict[str, int] = defaultdict(int)
    complexity_counts: dict[str, int] = defaultdict(int)

    # pass 1: satisfy answer_type targets while respecting family targets
    for item in candidates:
        family = str(item.get("family"))
        answer_type = str(item.get("answer_type"))
        complexity = str(item.get("complexity_level"))

        if family_counts[family] >= TARGET_TEST_BY_FAMILY[family]:
            continue
        if answer_type_counts[answer_type] >= TARGET_TEST_ANSWER_TYPE.get(answer_type, 0):
            continue

        selected.append(item)
        family_counts[family] += 1
        answer_type_counts[answer_type] += 1
        complexity_counts[complexity] += 1

    selected_ids = {str(item.get("id")) for item in selected}

    # pass 2: fill remaining family quotas while nudging toward complexity targets
    for item in candidates:
        item_id = str(item.get("id"))
        if item_id in selected_ids:
            continue

        family = str(item.get("family"))
        complexity = str(item.get("complexity_level"))

        if family_counts[family] >= TARGET_TEST_BY_FAMILY[family]:
            continue

        # prefer complexity buckets still under target
        under_target = complexity_counts[complexity] < TARGET_TEST_COMPLEXITY.get(complexity, 0)
        if under_target:
            selected.append(item)
            selected_ids.add(item_id)
            family_counts[family] += 1
            complexity_counts[complexity] += 1

    # pass 3: fill any remaining family gaps without further restrictions
    for item in candidates:
        item_id = str(item.get("id"))
        if item_id in selected_ids:
            continue

        family = str(item.get("family"))
        complexity = str(item.get("complexity_level"))

        if family_counts[family] >= TARGET_TEST_BY_FAMILY[family]:
            continue

        selected.append(item)
        selected_ids.add(item_id)
        family_counts[family] += 1
        complexity_counts[complexity] += 1

    return selected


def pick_validation_set(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = sort_candidates_for_validation(candidates)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    family_counts: dict[str, int] = defaultdict(int)
    complexity_counts: dict[str, int] = defaultdict(int)

    # pass 1: try to satisfy complexity targets with family quotas
    for item in candidates:
        family = str(item.get("family"))
        complexity = str(item.get("complexity_level"))
        item_id = str(item.get("id"))

        if family_counts[family] >= TARGET_VALIDATION_BY_FAMILY[family]:
            continue
        if complexity_counts[complexity] >= TARGET_VALIDATION_COMPLEXITY.get(complexity, 0):
            continue

        selected.append(item)
        selected_ids.add(item_id)
        family_counts[family] += 1
        complexity_counts[complexity] += 1

    # pass 2: fill family quotas
    for item in candidates:
        item_id = str(item.get("id"))
        if item_id in selected_ids:
            continue

        family = str(item.get("family"))
        complexity = str(item.get("complexity_level"))

        if family_counts[family] >= TARGET_VALIDATION_BY_FAMILY[family]:
            continue

        selected.append(item)
        selected_ids.add(item_id)
        family_counts[family] += 1
        complexity_counts[complexity] += 1

    return selected


def assign_split(items: list[dict[str, Any]], split_name: str) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    for item in items:
        new_item = dict(item)
        new_item["split"] = split_name
        updated.append(new_item)
    return updated


def build_summary(
    train_items: list[dict[str, Any]],
    validation_items: list[dict[str, Any]],
    test_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "total_items": len(train_items) + len(validation_items) + len(test_items),
        "split_counts": {
            "train": len(train_items),
            "validation": len(validation_items),
            "test": len(test_items),
        },
        "train_by_family": count_by(train_items, "family"),
        "validation_by_family": count_by(validation_items, "family"),
        "test_by_family": count_by(test_items, "family"),
        "train_by_source_dataset": count_by(train_items, "source_dataset"),
        "validation_by_source_dataset": count_by(validation_items, "source_dataset"),
        "test_by_source_dataset": count_by(test_items, "source_dataset"),
        "train_by_answer_type": count_by(train_items, "answer_type"),
        "validation_by_answer_type": count_by(validation_items, "answer_type"),
        "test_by_answer_type": count_by(test_items, "answer_type"),
        "train_by_complexity": count_by(train_items, "complexity_level"),
        "validation_by_complexity": count_by(validation_items, "complexity_level"),
        "test_by_complexity": count_by(test_items, "complexity_level"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split dataset into train/validation/test using improved rule-based selection."
    )
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--summary-output-file", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)
    summary_output_path = Path(args.summary_output_file)

    items = ensure_dataset_list(load_json_file(input_path), input_path)

    test_candidates = [item for item in items if is_test_eligible(item)]
    test_items_raw = pick_test_set(test_candidates)
    test_ids = {str(item.get("id")) for item in test_items_raw}

    remaining_after_test = [item for item in items if str(item.get("id")) not in test_ids]

    validation_candidates = [item for item in remaining_after_test if is_validation_eligible(item)]
    validation_items_raw = pick_validation_set(validation_candidates)
    validation_ids = {str(item.get("id")) for item in validation_items_raw}

    train_items_raw = [
        item for item in remaining_after_test if str(item.get("id")) not in validation_ids
    ]

    train_items = assign_split(train_items_raw, "train")
    validation_items = assign_split(validation_items_raw, "validation")
    test_items = assign_split(test_items_raw, "test")

    all_items = test_items + validation_items + train_items
    summary = build_summary(train_items, validation_items, test_items)

    save_json_file(output_path, all_items, overwrite=args.overwrite)
    save_json_file(summary_output_path, summary, overwrite=args.overwrite)

    print(f"Saved split dataset to: {output_path}")
    print(f"Saved split summary to: {summary_output_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
