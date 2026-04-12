from __future__ import annotations

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