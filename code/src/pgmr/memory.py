from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_MEMORY_FIELDS = {
    "family",
    "kind",
    "canonical_uri",
    "label",
    "placeholder",
}


def load_memory_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Memory file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Memory file must contain a JSON list: {path}")

    return data


def load_memory_dir(memory_dir: Path) -> list[dict[str, Any]]:
    if not memory_dir.exists() or not memory_dir.is_dir():
        raise FileNotFoundError(f"Memory directory not found: {memory_dir}")

    entries: list[dict[str, Any]] = []

    for path in sorted(memory_dir.glob("*_memory.json")):
        entries.extend(load_memory_file(path))

    if not entries:
        raise ValueError(f"No *_memory.json files found in {memory_dir}")

    return entries


def validate_memory_entries(entries: list[dict[str, Any]]) -> None:
    seen: set[tuple[str, str]] = set()

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Memory entry at index {index} is not an object.")

        missing = REQUIRED_MEMORY_FIELDS - set(entry.keys())
        if missing:
            raise ValueError(
                f"Memory entry at index {index} is missing fields: {sorted(missing)}"
            )

        family = str(entry["family"])
        canonical_uri = str(entry["canonical_uri"])

        key = (family, canonical_uri)
        if key in seen:
            raise ValueError(
                f"Duplicate canonical_uri within family: family={family}, uri={canonical_uri}"
            )
        seen.add(key)

        placeholder = str(entry["placeholder"])
        kind = str(entry["kind"])

        valid_placeholder_prefixes = {
            "relation": ("pgmr:", "[REL: "),
            "class": ("pgmrc:", "[CLASS: "),
            "resource": ("pgmrr:", "[RESOURCE: "),
        }

        allowed_prefixes = valid_placeholder_prefixes.get(kind)
        if allowed_prefixes is not None and not placeholder.startswith(allowed_prefixes):
            raise ValueError(
                f"Invalid placeholder for kind={kind}: {placeholder}. "
                f"Allowed prefixes: {allowed_prefixes}"
            )


def build_uri_to_placeholder_map(
    entries: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """
    Returns:
        {
          "nlp4re": {
              "orkgp:P181003": "pgmr:nlp_task",
              "orkgc:C121001": "pgmrc:nlp4re_contribution"
          },
          ...
        }
    """
    mapping: dict[str, dict[str, str]] = {}

    for entry in entries:
        family = str(entry["family"])
        canonical_uri = str(entry["canonical_uri"])
        placeholder = str(entry["placeholder"])

        mapping.setdefault(family, {})[canonical_uri] = placeholder

    return mapping