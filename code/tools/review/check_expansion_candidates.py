from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_items_from_file(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("items"), list):
        items = data["items"]
    else:
        raise ValueError(f"Unsupported JSON structure in file: {path}")

    if not all(isinstance(item, dict) for item in items):
        raise ValueError(f"File contains non-object entries: {path}")

    return items


def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_question(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"[“”\"'`]", "", text)
    text = re.sub(r"[?.!,;:]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_sparql(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def build_reference_pool(paths: list[Path]) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []

    for path in paths:
        items = load_items_from_file(path)
        for item in items:
            pool.append(
                {
                    "source_file": str(path),
                    "id": str(item.get("id", "")),
                    "question": str(item.get("question", "")),
                    "gold_sparql": str(item.get("gold_sparql", "")),
                    "norm_question": normalize_question(str(item.get("question", ""))),
                    "norm_sparql": normalize_sparql(str(item.get("gold_sparql", ""))),
                }
            )

    return pool


def find_exact_duplicates(
    candidate_items: list[dict[str, Any]],
    reference_pool: list[dict[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    question_dups: list[dict[str, str]] = []
    sparql_dups: list[dict[str, str]] = []
    pair_dups: list[dict[str, str]] = []

    for item in candidate_items:
        candidate_id = str(item.get("id", ""))
        question = str(item.get("question", ""))
        gold_sparql = str(item.get("gold_sparql", ""))

        norm_question = normalize_question(question)
        norm_sparql = normalize_sparql(gold_sparql)

        for ref in reference_pool:
            if ref["id"] == candidate_id and ref["source_file"].endswith("__SELF__"):
                continue

            same_question = norm_question and norm_question == ref["norm_question"]
            same_sparql = norm_sparql and norm_sparql == ref["norm_sparql"]

            if same_question:
                question_dups.append(
                    {
                        "candidate_id": candidate_id,
                        "reference_id": ref["id"],
                        "reference_file": ref["source_file"],
                    }
                )

            if same_sparql:
                sparql_dups.append(
                    {
                        "candidate_id": candidate_id,
                        "reference_id": ref["id"],
                        "reference_file": ref["source_file"],
                    }
                )

            if same_question and same_sparql:
                pair_dups.append(
                    {
                        "candidate_id": candidate_id,
                        "reference_id": ref["id"],
                        "reference_file": ref["source_file"],
                    }
                )

    return {
        "exact_question_duplicates": question_dups,
        "exact_sparql_duplicates": sparql_dups,
        "exact_pair_duplicates": pair_dups,
    }


def find_near_question_duplicates(
    candidate_items: list[dict[str, Any]],
    reference_pool: list[dict[str, Any]],
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    near_dups: list[dict[str, Any]] = []

    for item in candidate_items:
        candidate_id = str(item.get("id", ""))
        question = str(item.get("question", ""))
        norm_question = normalize_question(question)

        if not norm_question:
            continue

        for ref in reference_pool:
            if ref["id"] == candidate_id and ref["source_file"].endswith("__SELF__"):
                continue

            ref_question = ref["norm_question"]
            if not ref_question or norm_question == ref_question:
                continue

            score = SequenceMatcher(None, norm_question, ref_question).ratio()
            if score >= similarity_threshold:
                near_dups.append(
                    {
                        "candidate_id": candidate_id,
                        "reference_id": ref["id"],
                        "reference_file": ref["source_file"],
                        "similarity": round(score, 4),
                        "candidate_question": question,
                        "reference_question": ref["question"],
                    }
                )

    near_dups.sort(key=lambda x: x["similarity"], reverse=True)
    return near_dups


def detect_generic_predicate_warnings(candidate_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    pattern = re.compile(r"orkgp:has[A-Za-z0-9_]+")

    for item in candidate_items:
        candidate_id = str(item.get("id", ""))
        sparql = str(item.get("gold_sparql", ""))
        matches = sorted(set(pattern.findall(sparql)))

        if matches:
            warnings.append(
                {
                    "candidate_id": candidate_id,
                    "generic_predicates": matches,
                }
            )

    return warnings


def build_self_reference_pool(candidate_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []

    for item in candidate_items:
        pool.append(
            {
                "source_file": "__SELF__",
                "id": str(item.get("id", "")),
                "question": str(item.get("question", "")),
                "gold_sparql": str(item.get("gold_sparql", "")),
                "norm_question": normalize_question(str(item.get("question", ""))),
                "norm_sparql": normalize_sparql(str(item.get("gold_sparql", ""))),
            }
        )

    return pool


def discover_candidate_reference_files(candidate_dir: Path, exclude_file: Path) -> list[Path]:
    if not candidate_dir.exists():
        return []

    files = sorted(candidate_dir.glob("*.json"))
    return [path for path in files if path.resolve() != exclude_file.resolve()]


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check expansion candidate files for duplicates and basic schema warnings."
    )
    parser.add_argument(
        "--candidate-file",
        required=True,
        help="Path to the candidate JSON file to check.",
    )
    parser.add_argument(
        "--benchmark-file",
        required=True,
        help="Path to the benchmark seed dataset JSON file.",
    )
    parser.add_argument(
        "--candidate-dir",
        default="code/data/dataset/expansion/candidates",
        help="Directory containing other generated candidate JSON files.",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.92,
        help="Threshold for near-duplicate question detection.",
    )
    args = parser.parse_args()

    candidate_file = Path(args.candidate_file)
    benchmark_file = Path(args.benchmark_file)
    candidate_dir = Path(args.candidate_dir)

    candidate_items = load_items_from_file(candidate_file)

    reference_files = [benchmark_file]
    reference_files.extend(discover_candidate_reference_files(candidate_dir, candidate_file))

    reference_pool = build_reference_pool(reference_files)
    self_pool = build_self_reference_pool(candidate_items)

    exact_against_refs = find_exact_duplicates(candidate_items, reference_pool)
    exact_within_batch = find_exact_duplicates(candidate_items, self_pool)
    near_against_refs = find_near_question_duplicates(
        candidate_items,
        reference_pool,
        similarity_threshold=args.similarity_threshold,
    )
    generic_predicate_warnings = detect_generic_predicate_warnings(candidate_items)

    print_section("SUMMARY")
    print(f"candidate_file: {candidate_file}")
    print(f"candidate_entries: {len(candidate_items)}")
    print(f"reference_files_checked: {len(reference_files)}")

    print_section("EXACT DUPLICATES AGAINST REFERENCE FILES")
    print(f"exact_question_duplicates: {len(exact_against_refs['exact_question_duplicates'])}")
    print(f"exact_sparql_duplicates: {len(exact_against_refs['exact_sparql_duplicates'])}")
    print(f"exact_pair_duplicates: {len(exact_against_refs['exact_pair_duplicates'])}")

    print_section("EXACT DUPLICATES WITHIN CURRENT BATCH")
    internal_question_dups = [
        x for x in exact_within_batch["exact_question_duplicates"]
        if x["candidate_id"] != x["reference_id"]
    ]
    internal_sparql_dups = [
        x for x in exact_within_batch["exact_sparql_duplicates"]
        if x["candidate_id"] != x["reference_id"]
    ]
    internal_pair_dups = [
        x for x in exact_within_batch["exact_pair_duplicates"]
        if x["candidate_id"] != x["reference_id"]
    ]
    print(f"internal_question_duplicates: {len(internal_question_dups)}")
    print(f"internal_sparql_duplicates: {len(internal_sparql_dups)}")
    print(f"internal_pair_duplicates: {len(internal_pair_dups)}")

    print_section("NEAR QUESTION DUPLICATES AGAINST REFERENCE FILES")
    print(f"near_question_duplicates: {len(near_against_refs)}")
    for row in near_against_refs[:20]:
        print(
            f"- candidate={row['candidate_id']} ref={row['reference_id']} "
            f"score={row['similarity']} file={row['reference_file']}"
        )

    print_section("GENERIC PREDICATE WARNINGS")
    print(f"candidates_with_generic_predicates: {len(generic_predicate_warnings)}")
    for row in generic_predicate_warnings[:20]:
        print(f"- candidate={row['candidate_id']} predicates={row['generic_predicates']}")

    if exact_against_refs["exact_pair_duplicates"] or internal_pair_dups:
        print_section("RESULT")
        print("FAIL: exact duplicate question+SPARQL pairs found.")
        return 1

    print_section("RESULT")
    print("DONE: no exact pair duplicates found. Review near-duplicates and schema warnings manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())