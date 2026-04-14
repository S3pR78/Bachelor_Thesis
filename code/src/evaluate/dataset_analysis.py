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



def extract_schema_field_names(schema: dict[str, Any]) -> list[str]:
    """
    Extract top-level field names from the schema's 'properties' object.
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary/object.")

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(
            "Schema must contain a top-level 'properties' dictionary."
        )

    return sorted(properties.keys())


def extract_required_schema_fields(schema: dict[str, Any]) -> list[str]:
    """
    Extract required top-level field names from the schema.
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary/object.")

    required_fields = schema.get("required", [])
    if not isinstance(required_fields, list):
        raise ValueError("Schema field 'required' must be a list.")

    return sorted(field for field in required_fields if isinstance(field, str))


def build_schema_field_comparison(
    entries: list[dict],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare dataset fields against schema-defined top-level fields.
    """
    dataset_fields = set(collect_available_fields(entries))
    schema_fields = set(extract_schema_field_names(schema))
    required_fields = set(extract_required_schema_fields(schema))

    shared_fields = sorted(dataset_fields & schema_fields)
    schema_only_fields = sorted(schema_fields - dataset_fields)
    dataset_only_fields = sorted(dataset_fields - schema_fields)
    missing_required_fields = sorted(required_fields - dataset_fields)

    return {
        "dataset_field_count": len(dataset_fields),
        "schema_field_count": len(schema_fields),
        "required_field_count": len(required_fields),
        "shared_field_count": len(shared_fields),
        "shared_fields": shared_fields,
        "schema_only_field_count": len(schema_only_fields),
        "schema_only_fields": schema_only_fields,
        "dataset_only_field_count": len(dataset_only_fields),
        "dataset_only_fields": dataset_only_fields,
        "missing_required_field_count": len(missing_required_fields),
        "missing_required_fields": missing_required_fields,
    }


"""
"""


"""
    dataset_path='code/data/dataset/benchmark_merged_v1.json',
    schema_path='code/config/schemas/benchmark_dataset_schema_v1.json'
"""