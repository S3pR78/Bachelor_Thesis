from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from typing import Any

from src.evaluate.dataset_loader import load_evaluate_entries


def load_schema_definition(schema_path: str | Path) -> dict[str, Any]:
    """
    Load a schema JSON file and return it as a dictionary.
    """
    path = Path(schema_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Schema file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    if not isinstance(schema, dict):
        raise ValueError("Schema JSON must be a dictionary/object at the top level.")

    return schema


def load_analysis_inputs(
    dataset_path: str | Path,
    schema_path: str | Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """
    Load dataset entries and optionally a schema definition for later analysis.
    """
    dataset_path = Path(dataset_path)

    entries = load_evaluate_entries(str(dataset_path), limit=limit)
    schema = load_schema_definition(schema_path) if schema_path is not None else None

    return {
        "dataset_path": str(dataset_path),
        "dataset_name": dataset_path.stem,
        "entries": entries,
        "entry_count": len(entries),
        "schema_path": str(schema_path) if schema_path is not None else None,
        "schema": schema,
        "has_schema": schema is not None,
    }


def collect_available_fields(entries: list[dict]) -> list[str]:
    """
    Collect all field names that appear in dictionary entries.
    """
    field_names: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        field_names.update(entry.keys())

    return sorted(field_names)


def build_field_presence_summary(entries: list[dict]) -> dict[str, Any]:
    """
    Build a summary of which fields appear across dataset entries.
    """
    dict_entries = [entry for entry in entries if isinstance(entry, dict)]
    total_entries = len(dict_entries)

    field_counter: Counter[str] = Counter()

    for entry in dict_entries:
        field_counter.update(entry.keys())

    all_fields = sorted(field_counter.keys())

    field_details = {}
    for field_name in all_fields:
        present_count = field_counter[field_name]
        field_details[field_name] = {
            "present_count": present_count,
            "missing_count": total_entries - present_count,
            "coverage_ratio": round(present_count / total_entries, 4) if total_entries > 0 else None,
        }

    return {
        "total_entries": total_entries,
        "field_count": len(all_fields),
        "fields": all_fields,
        "field_details": field_details,
    }





"""
    dataset_path='code/data/dataset/benchmark_merged_v1.json',
    schema_path='code/config/schemas/benchmark_dataset_schema_v1.json'
"""