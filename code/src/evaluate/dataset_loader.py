"""Dataset loading and small profiling helpers for evaluation/reporting."""

import json
from typing import Any

from src.utils.config_loader import get_configured_path


def _filter_entries_by_field(
    data: list[dict[str, Any]], 
    field_name: str, 
    field_value: str | None
) -> list[dict[str, Any]]:
    """Filter a list of dictionary entries by a specific field value."""
    if field_value is None:
        return data
    
    return [
        entry
        for entry in data
        if isinstance(entry, dict) and entry.get(field_name) == field_value
    ]


def load_dataset_from_config(dataset_key: str, 
        review_status: str | None = None,
        gold_status: str | None = None,
        family: str | None = None,
        source_dataset: str | None = None) -> list[dict[str, Any]]:
    """Load a configured dataset and apply optional metadata filters."""
    dataset_path = get_configured_path(dataset_key)

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Dataset JSON must be a list of entries.")
    
    data = _filter_entries_by_field(data, "review_status", review_status)
    data = _filter_entries_by_field(data, "gold_status", gold_status)
    data = _filter_entries_by_field(data, "family", family)
    data = _filter_entries_by_field(data, "source_dataset", source_dataset)
    
    return data

def build_dataset_load_summary(
    entries: list[dict[str, Any]],
    dataset_key: str,
    review_status: str | None = None,
    gold_status: str | None = None,
    family: str | None = None,
    source_dataset: str | None = None,
) -> dict[str, Any]:
    """Summarize which dataset and filters produced the loaded entries."""
    return {
        "dataset_key": dataset_key,
        "num_entries": len(entries),
        "filters": {
            "review_status": review_status,
            "gold_status": gold_status,
            "family": family,
            "source_dataset": source_dataset,
        },
    }

def get_unique_field_values(
    entries: list[dict[str, Any]],
    field_name: str,
) -> list[str]:
    """Return sorted unique non-null values for one field."""
    unique_values = {
        entry.get(field_name)
        for entry in entries
        if isinstance(entry, dict) and entry.get(field_name) is not None
    }

    return sorted(unique_values)

def count_field_values(
    entries: list[dict[str, Any]],
    field_name: str,
) -> dict[str, int]:
    """Count non-null values for one field across entries."""
    counts: dict[str, int] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        value = entry.get(field_name)

        if value is None:
            continue

        counts[value] = counts.get(value, 0) + 1

    return dict(sorted(counts.items()))

def count_missing_field_values(
    entries: list[dict[str, Any]],
    field_name: str,
) -> int:
    """Count entries where a field is missing or null."""
    missing_count = 0

    for entry in entries:
        if not isinstance(entry, dict):
            missing_count += 1
            continue

        value = entry.get(field_name)

        if value is None:
            missing_count += 1

    return missing_count

def build_field_profile(
    entries: list[dict[str, Any]],
    field_name: str,
) -> dict[str, Any]:
    """Build one compact profile for field coverage and value distribution."""
    value_counts = count_field_values(entries, field_name)
    missing_count = count_missing_field_values(entries, field_name)

    return {
        "field_name": field_name,
        "num_unique_values": len(value_counts),
        "missing_count": missing_count,
        "value_counts": value_counts,
    }


def build_profiles_for_fields(
    entries: list[dict[str, Any]],
    field_names: list[str],
) -> dict[str, dict[str, Any]]:
    """Build field profiles keyed by field name."""
    profiles: dict[str, dict[str, Any]] = {}

    for field_name in field_names:
        profiles[field_name] = build_field_profile(entries, field_name)

    return profiles

def build_standard_benchmark_profiles(
    entries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build the standard field profiles used in benchmark reporting."""
    standard_fields = [
        "family",
        "source_dataset",
        "query_type",
        "answer_type",
        "query_shape",
        "complexity_level",
    ]

    return build_profiles_for_fields(entries, standard_fields)


import json
from pathlib import Path


def get_dataset_entries(dataset_obj: object) -> list[dict]:
    """Accept either a raw list or a common wrapped dataset object."""
    if isinstance(dataset_obj, list):
        return dataset_obj

    if isinstance(dataset_obj, dict):
        for key in ("entries", "items", "data"):
            value = dataset_obj.get(key)
            if isinstance(value, list):
                return value

    raise ValueError(
        "Dataset must be a list or a dict containing one of: "
        "'entries', 'items', or 'data'."
    )


def load_evaluate_entries(dataset_path: str, limit: int | None = None) -> list[dict]:
    """Load entries for benchmark evaluation from a JSON file."""
    path = Path(dataset_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        dataset_obj = json.load(f)

    entries = get_dataset_entries(dataset_obj)

    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be a positive integer.")
        entries = entries[:limit]

    return entries



def select_entry_fields(
    entry: dict,
    field_names: list[str] | tuple[str, ...],
) -> dict:
    """Copy a stable subset of fields into run output metadata."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a dictionary.")

    result = {}

    for field_name in field_names:
        result[field_name] = entry.get(field_name)

    return result
