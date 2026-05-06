"""Restore PGMR-lite placeholders to executable ORKG compact identifiers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.pgmr.memory_resolver import (
    ORKG_TOKEN_PATTERN,
    PGMR_TOKEN_PATTERN,
    PgmrMemoryEntry,
    PgmrResolutionOptions,
    build_memory_index,
    load_pgmr_memory_by_family,
    restore_pgmr_query_with_diagnostics,
)


MANUAL_FALLBACK_MAP: dict[str, str] = {
    # Core ORKG paper/contribution pattern.
    "pgmr:has_contribution": "orkgp:P31",
    "pgmr:publication_year": "orkgp:P29",

    # Safe alias observed in model output:
    # gold PGMR uses pgmr:statistical_tests -> orkgp:P35133.
    "pgmr:statistical_test": "orkgp:P35133",

    # Alias tokens observed in T5 PGMR-mini pathmap outputs.
    # These aliases map model-generated placeholder variants to existing
    # canonical PGMR memory predicates.
    "pgmr:scheme_availability": "orkgp:P181038",
    "pgmr:question_answer": "orkgp:P57004",
    "pgmr:requirements_engineering_Task": "orkgp:P181002",
}


@dataclass(frozen=True)
class RestoreResult:
    """Restoration output plus diagnostics for unresolved placeholders."""
    restored_query: str
    missing_mapping_tokens: list[str]
    remaining_pgmr_tokens: list[str]
    used_mapping_count: int
    alias_mappings: list[dict[str, Any]] | None = None
    auto_mappings: list[dict[str, Any]] | None = None
    mapping_suggestions: list[dict[str, Any]] | None = None
    unmapped_placeholders: list[str] | None = None


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_strings(obj: Any) -> list[str]:
    """Collect strings recursively from nested memory JSON structures."""
    values: list[str] = []

    if isinstance(obj, str):
        values.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            values.extend(find_strings(value))
    elif isinstance(obj, list):
        for value in obj:
            values.extend(find_strings(value))

    return values


def extract_mapping_pairs_from_object(obj: Any) -> dict[str, str]:
    """Infer one-token PGMR-to-ORKG pairs from a memory JSON object."""
    mapping: dict[str, str] = {}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            strings = find_strings(value)
            pgmr_tokens: list[str] = []
            orkg_tokens: list[str] = []

            for text in strings:
                pgmr_tokens.extend(PGMR_TOKEN_PATTERN.findall(text))
                orkg_tokens.extend(ORKG_TOKEN_PATTERN.findall(text))

            pgmr_tokens = sorted(set(pgmr_tokens))
            orkg_tokens = sorted(set(orkg_tokens))

            if len(pgmr_tokens) == 1 and len(orkg_tokens) == 1:
                mapping[pgmr_tokens[0]] = orkg_tokens[0]

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return mapping


def load_memory_mapping(memory_dir: Path) -> dict[str, str]:
    """Build a flat PGMR token to ORKG token mapping from memory files."""
    if not memory_dir.exists():
        raise FileNotFoundError(f"PGMR memory directory not found: {memory_dir}")

    mapping: dict[str, str] = {}

    for path in sorted(memory_dir.rglob("*.json")):
        try:
            data = load_json(path)
        except Exception:
            continue

        mapping.update(extract_mapping_pairs_from_object(data))

    return mapping


def build_restore_mapping(memory_dir: Path) -> dict[str, str]:
    mapping = dict(MANUAL_FALLBACK_MAP)
    mapping.update(load_memory_mapping(memory_dir))
    return mapping


def restore_pgmr_query(
    pgmr_query: str,
    memory_dir: Path,
    options: PgmrResolutionOptions | None = None,
) -> RestoreResult:
    """Replace mapped PGMR tokens and report any tokens still unresolved."""
    memory_by_family = load_pgmr_memory_by_family(memory_dir)
    all_entries = [
        entry
        for index in memory_by_family.values()
        for entry in index.entries
    ]
    all_entries.extend(
        PgmrMemoryEntry(
            family="__fallback__",
            placeholder=placeholder,
            canonical_uri=canonical_uri,
        )
        for placeholder, canonical_uri in MANUAL_FALLBACK_MAP.items()
    )
    memory_index = build_memory_index(all_entries)

    result = restore_pgmr_query_with_diagnostics(
        pgmr_query,
        memory_index,
        options,
    )

    return RestoreResult(
        restored_query=result.restored_query,
        missing_mapping_tokens=result.missing_mapping_tokens,
        remaining_pgmr_tokens=result.remaining_pgmr_tokens,
        used_mapping_count=result.used_mapping_count,
        alias_mappings=result.alias_mappings,
        auto_mappings=result.auto_mappings,
        mapping_suggestions=result.mapping_suggestions,
        unmapped_placeholders=result.unmapped_placeholders,
    )
