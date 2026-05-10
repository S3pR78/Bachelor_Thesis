from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


MEMORY_PATHS = {
    "empirical_research_practice": Path(
        "code/data/orkg_memory/templates/empirical_research_practice_memory.json"
    ),
    "nlp4re": Path("code/data/orkg_memory/templates/nlp4re_memory.json"),
}


WORD_RE = re.compile(r"[a-z0-9_]+")


def normalize_scope(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def tokenize(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower().replace("-", "_")))


@lru_cache(maxsize=8)
def load_memory_entries(family: str) -> tuple[dict[str, Any], ...]:
    """Load structured ORKG memory entries for one template family."""
    normalized_family = normalize_scope(family)
    path = MEMORY_PATHS.get(normalized_family)

    if not path or not path.exists():
        return tuple()

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return tuple()

    return tuple(entry for entry in data if isinstance(entry, dict))


def entry_text(entry: dict[str, Any]) -> str:
    parts: list[str] = []

    for key in ("label", "placeholder", "canonical_uri", "notes", "kind"):
        value = entry.get(key)
        if value:
            parts.append(str(value))

    for key in ("aliases", "placeholder_aliases"):
        value = entry.get(key)
        if isinstance(value, list):
            parts.extend(str(x) for x in value)

    return " ".join(parts)


def entry_score(entry: dict[str, Any], question_tokens: set[str]) -> int:
    if not question_tokens:
        return 0

    text_tokens = tokenize(entry_text(entry))
    return len(text_tokens & question_tokens)


def is_core_entry(entry: dict[str, Any], family: str) -> bool:
    placeholder = str(entry.get("placeholder") or "")
    canonical_uri = str(entry.get("canonical_uri") or "")

    core_placeholders = {
        "pgmr:has_contribution",
        "pgmr:publication_year",
        "pgmrc:empirical_research_practice_contribution",
        "pgmrc:nlp4re_contribution",
    }
    core_uris = {
        "orkgp:P31",
        "orkgp:P29",
        "orkgc:C27001",
        "orkgc:C121001",
    }

    return placeholder in core_placeholders or canonical_uri in core_uris


def relevant_memory_entries(
    family: str,
    question: str,
    *,
    max_items: int = 30,
) -> list[dict[str, Any]]:
    """Return a compact, question-relevant subset of memory entries.

    Selection is intentionally simple and deterministic: always keep core
    entries, then add entries whose labels/aliases/placeholders overlap with
    the question tokens.
    """
    normalized_family = normalize_scope(family)
    entries = list(load_memory_entries(normalized_family))
    question_tokens = tokenize(question)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(entry: dict[str, Any]) -> None:
        key = str(entry.get("placeholder") or entry.get("canonical_uri") or entry.get("label"))
        if key and key not in seen:
            seen.add(key)
            selected.append(entry)

    for entry in entries:
        if is_core_entry(entry, normalized_family):
            add(entry)

    scored_entries = [
        (entry_score(entry, question_tokens), entry)
        for entry in entries
        if not is_core_entry(entry, normalized_family)
    ]

    for score, entry in sorted(scored_entries, key=lambda x: x[0], reverse=True):
        if score <= 0:
            continue
        add(entry)
        if len(selected) >= max_items:
            break

    return selected[:max_items]


def allowed_placeholders_for_family(family: str) -> set[str]:
    """Return placeholders and placeholder aliases from structured memory."""
    allowed: set[str] = set()

    for entry in load_memory_entries(normalize_scope(family)):
        placeholder = entry.get("placeholder")
        if isinstance(placeholder, str) and placeholder.startswith(("pgmr:", "pgmrc:")):
            allowed.add(placeholder)

        aliases = entry.get("placeholder_aliases")
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str) and alias.startswith(("pgmr:", "pgmrc:")):
                    allowed.add(alias)

    return allowed


def format_pgmr_memory_entry(entry: dict[str, Any]) -> str:
    label = entry.get("label") or "unknown"
    placeholder = entry.get("placeholder") or "unknown_placeholder"
    kind = entry.get("kind") or "unknown"
    notes = entry.get("notes") or ""

    if notes:
        return f"- {label} [{kind}]: {placeholder} — {notes}"
    return f"- {label} [{kind}]: {placeholder}"


def format_sparql_memory_entry(entry: dict[str, Any]) -> str:
    label = entry.get("label") or "unknown"
    canonical_uri = entry.get("canonical_uri") or "unknown_uri"
    kind = entry.get("kind") or "unknown"
    placeholder = entry.get("placeholder") or ""

    if placeholder:
        return f"- {label} [{kind}]: {canonical_uri} (PGMR counterpart: {placeholder})"
    return f"- {label} [{kind}]: {canonical_uri}"


def pgmr_memory_context(family: str, question: str) -> str:
    normalized_family = normalize_scope(family)
    entries = relevant_memory_entries(normalized_family, question)

    if not entries:
        return "No structured PGMR memory context loaded."

    if normalized_family == "empirical_research_practice":
        root_class = "pgmrc:empirical_research_practice_contribution"
    elif normalized_family == "nlp4re":
        root_class = "pgmrc:nlp4re_contribution"
    else:
        root_class = "pgmrc:<family_contribution>"

    lines = [
        f"Structured PGMR-lite memory context for family={family}.",
        "Required PGMR-lite core:",
        "?paper pgmr:has_contribution ?contribution .",
        f"?contribution a {root_class} .",
        "Publication year is paper-level: ?paper pgmr:publication_year ?year .",
        "Use only placeholders from this family memory. Do not invent pgmr:/pgmrc: names.",
        "Relevant memory entries:",
    ]
    lines.extend(format_pgmr_memory_entry(entry) for entry in entries)

    return "\n".join(lines)


def sparql_memory_context(family: str, question: str) -> str:
    normalized_family = normalize_scope(family)
    entries = relevant_memory_entries(normalized_family, question)

    if not entries:
        return "No structured SPARQL memory context loaded."

    if normalized_family == "empirical_research_practice":
        root_class = "orkgc:C27001"
    elif normalized_family == "nlp4re":
        root_class = "orkgc:C121001"
    else:
        root_class = "orkgc:<family_contribution_class>"

    lines = [
        f"Structured Direct-SPARQL memory context for family={family}.",
        "Required Direct-SPARQL core:",
        "?paper orkgp:P31 ?contribution .",
        f"?contribution a {root_class} .",
        "Publication year is paper-level: ?paper orkgp:P29 ?year .",
        "Use ORKG predicates/classes/resources for SPARQL rules. Do not use pgmr:/pgmrc: placeholders.",
        "Relevant memory entries:",
    ]
    lines.extend(format_sparql_memory_entry(entry) for entry in entries)

    return "\n".join(lines)


def memory_domain_context(family: str, prediction_format: str, question: str) -> str:
    normalized_format = normalize_scope(prediction_format)

    if normalized_format == "pgmr_lite":
        return pgmr_memory_context(family, question)

    if normalized_format in {"sparql", "direct_sparql"}:
        return sparql_memory_context(family, question)

    return "No structured ORKG memory context loaded for this prediction format."
