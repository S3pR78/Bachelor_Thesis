from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from src.ace.online.selection import (
    load_dataset_items,
    select_dataset_items,
    selected_item_ids,
)


def _items() -> list[dict]:
    return [
        {"id": "1", "family": "nlp4re", "question": "A"},
        {"id": "2", "family": "empirical_research_practice", "question": "B"},
        {"id": "3", "family": "nlp4re", "question": "C"},
        {"id": "4", "family": "empirical_research_practice", "question": "D"},
        {"id": "5", "family": "nlp4re", "question": "E"},
    ]


def test_load_dataset_items_requires_list(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps({"id": "1"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Expected dataset list"):
        load_dataset_items(dataset_path)


def test_select_dataset_items_filters_by_family() -> None:
    selected = select_dataset_items(_items(), family="nlp4re")

    assert selected_item_ids(selected) == ["1", "3", "5"]
    assert all(item["family"] == "nlp4re" for item in selected)


def test_select_dataset_items_shuffle_is_deterministic_for_seed() -> None:
    first = select_dataset_items(_items(), shuffle=True, sample_seed=17)
    second = select_dataset_items(_items(), shuffle=True, sample_seed=17)
    different_seed = select_dataset_items(_items(), shuffle=True, sample_seed=18)

    assert selected_item_ids(first) == selected_item_ids(second)
    assert selected_item_ids(first) != selected_item_ids(different_seed)


def test_select_dataset_items_limit_applies_after_shuffle() -> None:
    items = _items()
    expected = list(items)
    random.Random(42).shuffle(expected)

    selected = select_dataset_items(
        items,
        limit=2,
        shuffle=True,
        sample_seed=42,
    )

    assert selected_item_ids(selected) == selected_item_ids(expected[:2])


def test_select_dataset_items_family_filter_happens_before_limit() -> None:
    selected = select_dataset_items(_items(), family="nlp4re", limit=2)

    assert selected_item_ids(selected) == ["1", "3"]


def test_select_dataset_items_rejects_negative_limit() -> None:
    with pytest.raises(ValueError, match="limit must be non-negative"):
        select_dataset_items(_items(), limit=-1)

