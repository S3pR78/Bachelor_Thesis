"""Select green/yellow/red candidate pools from execution reviews."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_list_of_dicts(obj: Any, path: Path, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(obj, list):
        raise ValueError(f"{field_name} in {path} must be a JSON array.")

    for index, item in enumerate(obj, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"{field_name} in {path} must contain only JSON objects. "
                f"Invalid item at position {index}."
            )

    return obj


def load_candidate_items(path: Path) -> list[dict[str, Any]]:
    obj = load_json_file(path)
    return ensure_list_of_dicts(obj, path, "candidate file")


def load_review_results(path: Path) -> list[dict[str, Any]]:
    obj = load_json_file(path)

    if not isinstance(obj, dict):
        raise ValueError(f"Execution review file {path} must be a JSON object.")

    results = obj.get("results")
    if results is None:
        raise ValueError(f"Execution review file {path} is missing 'results'.")

    return ensure_list_of_dicts(results, path, "execution review results")


def pair_candidate_and_review_files(
    candidate_files: list[str],
    review_files: list[str],
) -> list[tuple[Path, Path]]:
    if len(candidate_files) != len(review_files):
        raise ValueError(
            "The number of --candidate-file and --review-file arguments must match."
        )

    return [(Path(c), Path(r)) for c, r in zip(candidate_files, review_files)]


def build_review_map(review_results: list[dict[str, Any]], review_path: Path) -> dict[str, dict[str, Any]]:
    review_map: dict[str, dict[str, Any]] = {}

    for index, item in enumerate(review_results, start=1):
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError(
                f"Execution review result {index} in {review_path} is missing a valid 'id'."
            )

        if item_id in review_map:
            raise ValueError(
                f"Duplicate review id '{item_id}' found in {review_path}."
            )

        review_map[item_id] = item

    return review_map


def classify_selection_bucket(review_item: dict[str, Any]) -> str:
    bucket = review_item.get("review_bucket")
    if isinstance(bucket, str) and bucket in {"green", "yellow", "red"}:
        return bucket

    status = review_item.get("execution_status")
    cardinality = review_item.get("result_cardinality")

    if status == "error":
        return "red"
    if status == "skipped":
        return "yellow"
    if status == "ok" and cardinality == 0:
        return "yellow"
    if status == "ok" and isinstance(cardinality, int) and cardinality > 0:
        return "green"
    return "yellow"


def merge_selected_candidates(
    pairs: list[tuple[Path, Path]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    green_items: list[dict[str, Any]] = []
    yellow_items: list[dict[str, Any]] = []
    red_items: list[dict[str, Any]] = []

    seen_ids: set[str] = set()

    for candidate_path, review_path in pairs:
        candidate_items = load_candidate_items(candidate_path)
        review_results = load_review_results(review_path)
        review_map = build_review_map(review_results, review_path)

        for index, candidate in enumerate(candidate_items, start=1):
            item_id = candidate.get("id")
            if not isinstance(item_id, str) or not item_id.strip():
                raise ValueError(
                    f"Candidate item {index} in {candidate_path} is missing a valid 'id'."
                )

            if item_id in seen_ids:
                raise ValueError(
                    f"Duplicate candidate id '{item_id}' encountered across input files."
                )
            seen_ids.add(item_id)

            if item_id not in review_map:
                raise ValueError(
                    f"Candidate id '{item_id}' in {candidate_path} has no matching "
                    f"execution review entry in {review_path}."
                )

            review_item = review_map[item_id]
            bucket = classify_selection_bucket(review_item)

            merged_item = dict(candidate)
            merged_item["_selection_review"] = {
                "review_bucket": bucket,
                "execution_status": review_item.get("execution_status"),
                "query_type": review_item.get("query_type"),
                "result_cardinality": review_item.get("result_cardinality"),
                "execution_error": review_item.get("execution_error"),
                "source_candidate_file": str(candidate_path),
                "source_review_file": str(review_path),
            }

            if bucket == "green":
                green_items.append(merged_item)
            elif bucket == "yellow":
                yellow_items.append(merged_item)
            else:
                red_items.append(merged_item)

    return green_items, yellow_items, red_items


def build_summary(
    green_items: list[dict[str, Any]],
    yellow_items: list[dict[str, Any]],
    red_items: list[dict[str, Any]],
) -> dict[str, Any]:
    def count_by_family(items: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            family = str(item.get("family", "unknown"))
            counts[family] = counts.get(family, 0) + 1
        return counts

    return {
        "green_count": len(green_items),
        "yellow_count": len(yellow_items),
        "red_count": len(red_items),
        "green_by_family": count_by_family(green_items),
        "yellow_by_family": count_by_family(yellow_items),
        "red_by_family": count_by_family(red_items),
    }


def write_json(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {path}. Use --overwrite to replace it."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select green/yellow/red candidate pools from execution-reviewed candidate files."
    )
    parser.add_argument(
        "--candidate-file",
        action="append",
        required=True,
        help="Path to a candidate JSON file. May be provided multiple times.",
    )
    parser.add_argument(
        "--review-file",
        action="append",
        required=True,
        help="Path to a matching execution review JSON file. May be provided multiple times.",
    )
    parser.add_argument(
        "--green-output-file",
        required=True,
        help="Path to save merged green candidates.",
    )
    parser.add_argument(
        "--yellow-output-file",
        required=True,
        help="Path to save merged yellow candidates.",
    )
    parser.add_argument(
        "--red-output-file",
        required=True,
        help="Path to save merged red candidates.",
    )
    parser.add_argument(
        "--summary-output-file",
        required=True,
        help="Path to save the selection summary JSON.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing output files.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    pairs = pair_candidate_and_review_files(
        candidate_files=args.candidate_file,
        review_files=args.review_file,
    )

    green_items, yellow_items, red_items = merge_selected_candidates(pairs)
    summary = build_summary(green_items, yellow_items, red_items)

    write_json(Path(args.green_output_file), green_items, overwrite=args.overwrite)
    write_json(Path(args.yellow_output_file), yellow_items, overwrite=args.overwrite)
    write_json(Path(args.red_output_file), red_items, overwrite=args.overwrite)
    write_json(Path(args.summary_output_file), summary, overwrite=args.overwrite)

    print("Selection complete.")
    print(
        f"Green: {summary['green_count']} | "
        f"Yellow: {summary['yellow_count']} | "
        f"Red: {summary['red_count']}"
    )
    print(f"Green by family: {summary['green_by_family']}")
    print(f"Yellow by family: {summary['yellow_by_family']}")
    print(f"Red by family: {summary['red_by_family']}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
