import json
from typing import Any

from src.utils.config_loader import get_configured_path



def _filter_entries_by_filed(
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
    
    """Load a dataset from a JSON file specified in the path configuration. Optionally filter entries by review_status."""
    dataset_path = get_configured_path(dataset_key)

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Dataset JSON must be a list of entries.")
    
    data = _filter_entries_by_filed(data, "review_status", review_status)
    data = _filter_entries_by_filed(data, "gold_status", gold_status)
    data = _filter_entries_by_filed(data, "family", family)
    data = _filter_entries_by_filed(data, "source_dataset", source_dataset)
    
    return data



"""Helper function to build a summary of the dataset loading process, including the number of entries and applied filters."""
def build_dataset_load_summary(
    entries: list[dict[str, Any]],
    dataset_key: str,
    review_status: str | None = None,
    gold_status: str | None = None,
    family: str | None = None,
    source_dataset: str | None = None,
) -> dict[str, Any]:
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
    unique_values = {
        entry.get(field_name)
        for entry in entries
        if isinstance(entry, dict) and entry.get(field_name) is not None
    }

    return sorted(unique_values)


"""Helper function to count occurrences of unique values in a specified field across a list of dictionary entries."""
def count_field_values(
    entries: list[dict[str, Any]],
    field_name: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        value = entry.get(field_name)

        if value is None:
            continue

        counts[value] = counts.get(value, 0) + 1

    return dict(sorted(counts.items()))

"""Helper function to count the number of entries with missing values for a specified field across a list of dictionary entries."""
def count_missing_field_values(
    entries: list[dict[str, Any]],
    field_name: str,
) -> int:
    missing_count = 0

    for entry in entries:
        if not isinstance(entry, dict):
            missing_count += 1
            continue

        value = entry.get(field_name)

        if value is None:
            missing_count += 1

    return missing_count

"""Helper function to build a profile of a specific field in the dataset, including the number of unique values, count of missing values, and counts of each unique value."""
def build_field_profile(
    entries: list[dict[str, Any]],
    field_name: str,
) -> dict[str, Any]:
    value_counts = count_field_values(entries, field_name)
    missing_count = count_missing_field_values(entries, field_name)

    return {
        "field_name": field_name,
        "num_unique_values": len(value_counts),
        "missing_count": missing_count,
        "value_counts": value_counts,
    }


"""Helper function to build profiles for multiple specified fields in the dataset, returning a dictionary of field profiles keyed by field name."""
def build_profiles_for_fields(
    entries: list[dict[str, Any]],
    field_names: list[str],
) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}

    for field_name in field_names:
        profiles[field_name] = build_field_profile(entries, field_name)

    return profiles

"""Helper function to build standard benchmark profiles for a predefined set of fields in the dataset."""
def build_standard_benchmark_profiles(
    entries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
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