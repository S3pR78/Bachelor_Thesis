"""Create ACE-oriented train/validation/playbook/benchmark splits."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


VALID_REVIEW_STATUS = {"reviewed", "revised", "approved"}
VALID_GOLD_STATUS = {"validated", "final"}

DEFAULT_STRATIFY_FIELDS = [
    "family",
    "source_dataset",
    "answer_type",
    "complexity_level",
    "query_shape",
]


def load_json(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {path}. Use --overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_dataset_list(obj: Any, path: Path) -> list[dict[str, Any]]:
    if not isinstance(obj, list):
        raise ValueError(f"{path} must contain a top-level JSON array.")
    for idx, item in enumerate(obj):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {idx} is not a JSON object.")
    return obj


def item_id(item: dict[str, Any]) -> str:
    value = item.get("id")
    if value is None or str(value).strip() == "":
        raise ValueError(f"Dataset item without id: {item}")
    return str(value)


def has_paraphrase(item: dict[str, Any]) -> bool:
    value = item.get("paraphrased_questions")
    return isinstance(value, list) and len(value) > 0


def is_eligible(item: dict[str, Any], require_paraphrase: bool) -> bool:
    if item.get("language") != "en":
        return False

    if item.get("review_status") not in VALID_REVIEW_STATUS:
        return False

    if item.get("gold_status") not in VALID_GOLD_STATUS:
        return False

    if require_paraphrase and not has_paraphrase(item):
        return False

    if not str(item.get("gold_sparql", "")).strip():
        return False

    if item.get("family") not in {"nlp4re", "empirical_research_practice"}:
        return False

    return True


def parse_source_quota(value: str) -> tuple[str, int]:
    if "=" not in value:
        raise ValueError(
            f"Invalid source quota '{value}'. Expected format: SourceDataset=COUNT"
        )
    source, count_text = value.split("=", 1)
    source = source.strip()
    count = int(count_text.strip())
    if not source:
        raise ValueError(f"Invalid empty source in quota: {value}")
    if count < 0:
        raise ValueError(f"Quota must be non-negative: {value}")
    return source, count


def parse_forced_ids(values: list[str], file_path: Path | None) -> list[str]:
    ids: list[str] = []

    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                ids.append(part)

    if file_path:
        raw = file_path.read_text(encoding="utf-8").splitlines()
        for line in raw:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)

    seen: set[str] = set()
    unique_ids: list[str] = []
    for id_value in ids:
        if id_value not in seen:
            unique_ids.append(id_value)
            seen.add(id_value)

    return unique_ids


def complexity_rank(value: Any) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(str(value), 9)


def count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        counter[str(item.get(field, "__missing__"))] += 1
    return dict(sorted(counter.items()))


def split_counts_by_field(
    split_items: dict[str, list[dict[str, Any]]],
    field: str,
) -> dict[str, dict[str, int]]:
    return {split_name: count_by(items, field) for split_name, items in split_items.items()}


def deterministic_shuffle(items: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    copied = list(items)
    rng = random.Random(seed)
    rng.shuffle(copied)
    return copied


def group_key(item: dict[str, Any], fields: list[str]) -> tuple[str, ...]:
    return tuple(str(item.get(field, "__missing__")) for field in fields)


def usable_stratify_fields(items: list[dict[str, Any]], fields: list[str]) -> list[str]:
    usable: list[str] = []
    for field in fields:
        if any(field in item for item in items):
            usable.append(field)
    return usable


def sample_stratified(
    items: list[dict[str, Any]],
    size: int,
    stratify_fields: list[str],
    seed: int,
) -> list[dict[str, Any]]:
    if size < 0:
        raise ValueError("Sample size must be non-negative.")
    if size > len(items):
        raise ValueError(f"Cannot sample {size} items from only {len(items)} candidates.")
    if size == 0:
        return []

    fields = usable_stratify_fields(items, stratify_fields)
    if not fields:
        return deterministic_shuffle(items, seed)[:size]

    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[group_key(item, fields)].append(item)

    shuffled_groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for index, (key, group_items) in enumerate(sorted(groups.items(), key=lambda kv: str(kv[0]))):
        shuffled_groups[key] = deterministic_shuffle(group_items, seed + index + 1)

    total = len(items)
    allocations: dict[tuple[str, ...], int] = {}
    fractions: list[tuple[float, int, tuple[str, ...]]] = []

    allocated = 0
    for key, group_items in shuffled_groups.items():
        exact = size * (len(group_items) / total)
        base = min(int(exact), len(group_items))
        allocations[key] = base
        allocated += base
        fractions.append((exact - base, len(group_items) - base, key))

    remaining = size - allocated
    fractions.sort(key=lambda x: (-x[0], -x[1], str(x[2])))

    while remaining > 0:
        progressed = False
        for _, _, key in fractions:
            if remaining <= 0:
                break
            if allocations[key] < len(shuffled_groups[key]):
                allocations[key] += 1
                remaining -= 1
                progressed = True
        if not progressed:
            break

    selected: list[dict[str, Any]] = []
    for key, amount in allocations.items():
        selected.extend(shuffled_groups[key][:amount])

    if len(selected) < size:
        selected_ids = {item_id(item) for item in selected}
        leftovers = [
            item for item in deterministic_shuffle(items, seed + 999)
            if item_id(item) not in selected_ids
        ]
        selected.extend(leftovers[: size - len(selected)])

    return selected[:size]


def annotate_items(items: list[dict[str, Any]], split_name: str) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for item in items:
        new_item = dict(item)
        if "split" in item:
            new_item["previous_split"] = item.get("split")
        new_item["split"] = split_name
        new_item["ace_split"] = split_name
        annotated.append(new_item)
    return annotated


def pick_forced_items(
    forced_ids: list[str],
    id_to_item: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    forced_items: list[dict[str, Any]] = []
    for forced_id in forced_ids:
        if forced_id not in id_to_item:
            raise ValueError(f"Forced playbook id not found in eligible dataset: {forced_id}")
        forced_items.append(id_to_item[forced_id])
    return forced_items


def pick_priority_source_items(
    candidates: list[dict[str, Any]],
    source_quotas: list[tuple[str, int]],
    already_selected_ids: set[str],
    preferred_previous_split: str | None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for source_dataset, quota in source_quotas:
        source_candidates = [
            item for item in candidates
            if item_id(item) not in already_selected_ids
            and str(item.get("source_dataset")) == source_dataset
        ]

        source_candidates = sorted(
            source_candidates,
            key=lambda item: (
                0 if preferred_previous_split and item.get("split") == preferred_previous_split else 1,
                complexity_rank(item.get("complexity_level")),
                str(item.get("family", "")),
                item_id(item),
            ),
        )

        chosen = source_candidates[:quota]
        selected.extend(chosen)
        already_selected_ids.update(item_id(item) for item in chosen)

    return selected



def pick_source_quota_items_exact(
    candidates: list[dict[str, Any]],
    source_quotas: list[tuple[str, int]],
    already_selected_ids: set[str],
    preferred_previous_split: str | None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for source_dataset, quota in source_quotas:
        source_candidates = [
            item for item in candidates
            if item_id(item) not in already_selected_ids
            and str(item.get("source_dataset")) == source_dataset
        ]

        source_candidates = sorted(
            source_candidates,
            key=lambda item: (
                0 if preferred_previous_split and item.get("split") == preferred_previous_split else 1,
                complexity_rank(item.get("complexity_level")),
                str(item.get("family", "")),
                item_id(item),
            ),
        )

        if len(source_candidates) < quota:
            raise ValueError(
                f"Not enough candidates for benchmark source quota "
                f"{source_dataset}={quota}. Available: {len(source_candidates)}"
            )

        chosen = source_candidates[:quota]
        selected.extend(chosen)
        already_selected_ids.update(item_id(item) for item in chosen)

    return selected

def ensure_disjoint(split_items: dict[str, list[dict[str, Any]]]) -> None:
    seen: dict[str, str] = {}
    for split_name, items in split_items.items():
        for item in items:
            current_id = item_id(item)
            if current_id in seen:
                raise ValueError(
                    f"Duplicate id across splits: {current_id} in {seen[current_id]} and {split_name}"
                )
            seen[current_id] = split_name


def build_summary(
    input_file: Path,
    seed: int,
    split_items: dict[str, list[dict[str, Any]]],
    forced_playbook_ids: list[str],
    source_quotas: list[tuple[str, int]],
    benchmark_source_quotas: list[tuple[str, int]],
    stratify_fields: list[str],
) -> dict[str, Any]:
    fields_for_summary = [
        "family",
        "source_dataset",
        "answer_type",
        "complexity_level",
        "query_shape",
        "previous_split",
    ]

    summary: dict[str, Any] = {
        "input_file": str(input_file),
        "seed": seed,
        "split_counts": {name: len(items) for name, items in split_items.items()},
        "forced_playbook_ids": forced_playbook_ids,
        "playbook_priority_source_quotas": [
            {"source_dataset": source, "quota": quota}
            for source, quota in source_quotas
        ],
        "benchmark_source_quotas": [
            {"source_dataset": source, "quota": quota}
            for source, quota in benchmark_source_quotas
        ],
        "stratify_fields": stratify_fields,
        "duplicate_id_check": "passed",
    }

    for field in fields_for_summary:
        summary[f"by_{field}"] = split_counts_by_field(split_items, field)

    total = sum(len(items) for items in split_items.values())
    unique_ids = {
        item_id(item)
        for items in split_items.values()
        for item in items
    }
    summary["total_items"] = total
    summary["unique_ids"] = len(unique_ids)

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create ACE-aware train/validation/playbook/benchmark splits from the master dataset."
    )
    parser.add_argument("--input-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)

    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--train-size", type=int, default=602)
    parser.add_argument("--validation-size", type=int, default=50)
    parser.add_argument("--ace-playbook-size", type=int, default=59)
    parser.add_argument("--benchmark-size", type=int, default=51)

    parser.add_argument(
        "--playbook-priority-source",
        action="append",
        default=[],
        help="Priority source quota for ACE playbook, e.g. EmpiRE_Compass=10. Can be repeated.",
    )
    parser.add_argument(
        "--benchmark-source-quota",
        action="append",
        default=[],
        help="Hard source quota for final benchmark, e.g. Hybrid_NLP4RE=25. Can be repeated.",
    )
    parser.add_argument(
        "--preferred-previous-split-for-priority",
        default="test",
        help="Prefer this previous split when selecting priority source items. Use empty string to disable.",
    )

    parser.add_argument(
        "--force-playbook-ids",
        action="append",
        default=[],
        help="Comma-separated ids to force into ace_playbook. Can be repeated.",
    )
    parser.add_argument("--force-playbook-ids-file", type=Path, default=None)

    parser.add_argument(
        "--stratify-fields",
        default=",".join(DEFAULT_STRATIFY_FIELDS),
        help="Comma-separated fields for stratified sampling.",
    )
    parser.add_argument("--require-paraphrase", action="store_true")

    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    raw_items = ensure_dataset_list(load_json(args.input_file), args.input_file)

    eligible_items = [
        item for item in raw_items
        if is_eligible(item, require_paraphrase=args.require_paraphrase)
    ]

    target_total = (
        args.train_size
        + args.validation_size
        + args.ace_playbook_size
        + args.benchmark_size
    )

    if len(eligible_items) != target_total:
        raise ValueError(
            f"Eligible item count is {len(eligible_items)}, but target total is {target_total}. "
            "Check eligibility rules or target sizes."
        )

    ids = [item_id(item) for item in eligible_items]
    duplicate_ids = [id_value for id_value, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        raise ValueError(f"Duplicate ids in eligible dataset: {duplicate_ids[:20]}")

    id_to_item = {item_id(item): item for item in eligible_items}

    source_quotas = [
        parse_source_quota(value)
        for value in args.playbook_priority_source
    ]
    benchmark_source_quotas = [
        parse_source_quota(value)
        for value in args.benchmark_source_quota
    ]

    forced_ids = parse_forced_ids(
        values=args.force_playbook_ids,
        file_path=args.force_playbook_ids_file,
    )

    stratify_fields = [
        field.strip()
        for field in args.stratify_fields.split(",")
        if field.strip()
    ]

    preferred_previous_split = args.preferred_previous_split_for_priority.strip() or None

    forced_items = pick_forced_items(forced_ids, id_to_item)
    forced_ids_set = {item_id(item) for item in forced_items}

    # Reserve the final benchmark first.
    # This prevents EmpiRE/Hybrid challenge questions from being consumed by playbook/train.
    benchmark_selected_ids = set(forced_ids_set)
    benchmark_quota_items = pick_source_quota_items_exact(
        candidates=eligible_items,
        source_quotas=benchmark_source_quotas,
        already_selected_ids=benchmark_selected_ids,
        preferred_previous_split=preferred_previous_split,
    )

    if len(benchmark_quota_items) > args.benchmark_size:
        raise ValueError(
            f"Benchmark source quotas select {len(benchmark_quota_items)} items, "
            f"but benchmark size is only {args.benchmark_size}."
        )

    remaining_for_benchmark = [
        item for item in eligible_items
        if item_id(item) not in benchmark_selected_ids
    ]

    benchmark_fill = sample_stratified(
        remaining_for_benchmark,
        args.benchmark_size - len(benchmark_quota_items),
        stratify_fields=stratify_fields,
        seed=args.seed + 200,
    )

    benchmark_items = benchmark_quota_items + benchmark_fill
    benchmark_ids = {item_id(item) for item in benchmark_items}

    selected_playbook: list[dict[str, Any]] = []
    selected_playbook.extend(forced_items)

    selected_ids = set(forced_ids_set)
    selected_ids.update(benchmark_ids)

    priority_items = pick_priority_source_items(
        candidates=eligible_items,
        source_quotas=source_quotas,
        already_selected_ids=selected_ids,
        preferred_previous_split=preferred_previous_split,
    )
    selected_playbook.extend(priority_items)
    selected_ids.update(item_id(item) for item in priority_items)

    if len(selected_playbook) > args.ace_playbook_size:
        raise ValueError(
            f"Forced/priority playbook items ({len(selected_playbook)}) exceed "
            f"ace-playbook-size ({args.ace_playbook_size})."
        )

    remaining_for_playbook = [
        item for item in eligible_items
        if item_id(item) not in selected_ids
    ]

    playbook_fill = sample_stratified(
        remaining_for_playbook,
        args.ace_playbook_size - len(selected_playbook),
        stratify_fields=stratify_fields,
        seed=args.seed + 100,
    )

    selected_playbook.extend(playbook_fill)
    playbook_ids = {item_id(item) for item in selected_playbook}

    remaining_after_benchmark_and_playbook = [
        item for item in eligible_items
        if item_id(item) not in benchmark_ids
        and item_id(item) not in playbook_ids
    ]

    validation_items = sample_stratified(
        remaining_after_benchmark_and_playbook,
        args.validation_size,
        stratify_fields=stratify_fields,
        seed=args.seed + 300,
    )
    validation_ids = {item_id(item) for item in validation_items}

    train_items = [
        item for item in remaining_after_benchmark_and_playbook
        if item_id(item) not in validation_ids
    ]

    if len(train_items) != args.train_size:
        raise ValueError(f"Expected train size {args.train_size}, got {len(train_items)}.")

    annotated_splits = {
        "train": annotate_items(train_items, "train"),
        "validation": annotate_items(validation_items, "validation"),
        "ace_playbook": annotate_items(selected_playbook, "ace_playbook"),
        "benchmark": annotate_items(benchmark_items, "benchmark"),
    }

    ensure_disjoint(annotated_splits)

    summary = build_summary(
        input_file=args.input_file,
        seed=args.seed,
        split_items=annotated_splits,
        forced_playbook_ids=forced_ids,
        source_quotas=source_quotas,
        benchmark_source_quotas=benchmark_source_quotas,
        stratify_fields=stratify_fields,
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.dry_run:
        print("\nDry run only. No files written.")
        return 0

    output_dir = args.output_dir
    save_json(output_dir / "train.json", annotated_splits["train"], overwrite=args.overwrite)
    save_json(output_dir / "validation.json", annotated_splits["validation"], overwrite=args.overwrite)
    save_json(output_dir / "ace_playbook.json", annotated_splits["ace_playbook"], overwrite=args.overwrite)
    save_json(output_dir / "benchmark.json", annotated_splits["benchmark"], overwrite=args.overwrite)
    save_json(output_dir / "ace_split_summary.json", summary, overwrite=args.overwrite)

    print(f"\nWrote ACE splits to: {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
