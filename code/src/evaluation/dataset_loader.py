import json
from typing import Any

from src.utils.config_loader import get_configured_path


def load_dataset_from_config(dataset_key: str, 
        review_status: str | None = None,
        gold_status: str | None = None) -> list[dict[str, Any]]:
    
    """Load a dataset from a JSON file specified in the path configuration. Optionally filter entries by review_status."""
    dataset_path = get_configured_path(dataset_key)

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Dataset JSON must be a list of entries.")
    

    if review_status is not None:
        data = [
            entry
            for entry in data
            if isinstance(entry, dict) and entry.get("review_status") == review_status
        ]

    if gold_status is not None:
        data = [
            entry
            for entry in data
            if isinstance(entry, dict) and entry.get("gold_status") == gold_status
        ]
    
    return data