"""Dataset selection helpers for online ACE runs."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


DatasetItem = dict[str, Any]


def load_dataset_items(dataset_path: str | Path) -> list[DatasetItem]:
    """Load a dataset JSON file as a list of item dictionaries."""
    path = Path(dataset_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError(f"Expected dataset list in {path}")

    if not all(isinstance(item, dict) for item in data):
        raise ValueError(f"Expected all dataset items in {path} to be objects")

    return data


def select_dataset_items(
    items: list[DatasetItem],
    *,
    family: str | None = None,
    limit: int | None = None,
    shuffle: bool = False,
    sample_seed: int = 42,
) -> list[DatasetItem]:
    """Filter, optionally shuffle, and limit dataset items deterministically."""
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")

    selected = [
        item for item in items
        if family is None or str(item.get("family")) == str(family)
    ]

    if shuffle:
        selected = list(selected)
        random.Random(sample_seed).shuffle(selected)

    if limit is not None:
        selected = selected[:limit]

    return selected


def selected_item_ids(items: list[DatasetItem]) -> list[str]:
    """Return selected item IDs as strings for summaries and trace metadata."""
    return [str(item.get("id")) for item in items]

