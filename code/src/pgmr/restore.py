from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PGMR_TOKEN_PATTERN = re.compile(r"\b(?:pgmr|pgmrc):[A-Za-z_][A-Za-z0-9_]*\b")
ORKG_TOKEN_PATTERN = re.compile(r"\b(?:orkgp|orkgc|orkgr):[A-Za-z0-9_]+\b")


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
    restored_query: str
    missing_mapping_tokens: list[str]
    remaining_pgmr_tokens: list[str]
    used_mapping_count: int


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_strings(obj: Any) -> list[str]:
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


def restore_pgmr_query(pgmr_query: str, memory_dir: Path) -> RestoreResult:
    mapping = build_restore_mapping(memory_dir)
    missing: list[str] = []

    def replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        replacement = mapping.get(token)

        if replacement is None:
            missing.append(token)
            return token

        return replacement

    restored = PGMR_TOKEN_PATTERN.sub(replace_token, pgmr_query)
    remaining = sorted(set(PGMR_TOKEN_PATTERN.findall(restored)))

    return RestoreResult(
        restored_query=restored,
        missing_mapping_tokens=sorted(set(missing)),
        remaining_pgmr_tokens=remaining,
        used_mapping_count=len(mapping),
    )
