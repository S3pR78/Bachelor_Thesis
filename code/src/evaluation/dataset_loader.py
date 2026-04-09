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