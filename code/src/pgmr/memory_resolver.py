"""Resolve PGMR-lite placeholders against template memory."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.pgmr.memory import load_memory_dir


PGMR_TOKEN_PATTERN = re.compile(r"\b(?:pgmr|pgmrc):[A-Za-z_][A-Za-z0-9_]*\b")
ORKG_TOKEN_PATTERN = re.compile(r"\b(?:orkgp|orkgc|orkgr):[A-Za-z0-9_]+\b")

DEFAULT_AUTO_MAP_THRESHOLD = 0.90
DEFAULT_SUGGESTION_THRESHOLD = 0.75
DEFAULT_MIN_MARGIN = 0.08

SYNONYM_TOKENS: dict[str, tuple[str, ...]] = {
    "data": ("dataset",),
    "datasource": ("data", "source"),
    "source": ("data", "source"),
    "url": ("location",),
    "uri": ("location",),
    "question": ("research", "question"),
    "answer": ("research", "answer"),
    "task": ("nlp", "task"),
    "re": ("requirements", "engineering"),
    "metric": ("evaluation", "metric"),
    "measure": ("metric",),
    "technique": ("method",),
}


@dataclass(frozen=True)
class PgmrResolutionOptions:
    """Controls optional similarity-based PGMR placeholder mapping."""

    enable_similarity_mapping: bool = False
    auto_map_threshold: float = DEFAULT_AUTO_MAP_THRESHOLD
    suggestion_threshold: float = DEFAULT_SUGGESTION_THRESHOLD
    min_margin: float = DEFAULT_MIN_MARGIN


@dataclass(frozen=True)
class PgmrMemoryEntry:
    """One restorable PGMR memory row."""

    family: str
    placeholder: str
    canonical_uri: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedPlaceholder:
    """Normalized token view used for conservative similarity scoring."""

    token: str
    tokens: tuple[str, ...]
    text: str
    reasons: tuple[str, ...] = ()


@dataclass
class PgmrMemoryIndex:
    """Family-scoped lookup index for PGMR memory entries."""

    entries: list[PgmrMemoryEntry]
    exact: dict[str, PgmrMemoryEntry] = field(default_factory=dict)
    aliases: dict[str, PgmrMemoryEntry] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateScore:
    """Similarity score for a missing placeholder and one memory candidate."""

    entry: PgmrMemoryEntry
    score: float
    reason: str


@dataclass
class PgmrRestoreResult:
    """Restoration output plus mapping diagnostics for report files."""

    restored_query: str
    missing_mapping_tokens: list[str]
    remaining_pgmr_tokens: list[str]
    used_mapping_count: int
    alias_mappings: list[dict[str, Any]]
    auto_mappings: list[dict[str, Any]]
    mapping_suggestions: list[dict[str, Any]]
    unmapped_placeholders: list[str]


def canonicalize_pgmr_token(token: str) -> str:
    """Normalize PGMR relation placeholder casing."""
    if ":" not in token:
        return token

    prefix, local_name = token.split(":", 1)
    if prefix == "pgmr":
        return f"{prefix}:{local_name.lower()}"
    return token


def _split_local_name(local_name: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", local_name)
    parts = re.split(r"[_\-\s]+", spaced.lower())
    return [part for part in parts if part]


def _singularize_token(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith(("ss", "us", "is")):
        return token
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s"):
        return token[:-1]
    return token


def _collapse_consecutive_duplicates(tokens: list[str]) -> tuple[list[str], list[str]]:
    collapsed: list[str] = []
    reasons: list[str] = []

    for token in tokens:
        if collapsed and collapsed[-1] == token:
            reasons.append(f"collapsed repeated token suffix: {token}_{token} -> {token}")
            continue
        collapsed.append(token)

    return collapsed, reasons


def normalize_placeholder(token: str) -> NormalizedPlaceholder:
    """Build the canonical token sequence used for similarity matching."""
    local_name = token.split(":", 1)[1] if ":" in token else token
    raw_tokens = [_singularize_token(part) for part in _split_local_name(local_name)]
    collapsed_raw, duplicate_reasons = _collapse_consecutive_duplicates(raw_tokens)

    synonym_tokens: list[str] = []
    for part in collapsed_raw:
        synonym_tokens.extend(SYNONYM_TOKENS.get(part, (part,)))

    normalized_tokens, synonym_duplicate_reasons = _collapse_consecutive_duplicates(
        synonym_tokens
    )
    reasons = duplicate_reasons + synonym_duplicate_reasons

    return NormalizedPlaceholder(
        token=token,
        tokens=tuple(normalized_tokens),
        text="_".join(normalized_tokens),
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _score_candidate(
    missing_token: str,
    candidate: PgmrMemoryEntry,
) -> CandidateScore:
    missing = normalize_placeholder(missing_token)
    target = normalize_placeholder(candidate.placeholder)

    missing_tokens = set(missing.tokens)
    target_tokens = set(target.tokens)
    union = missing_tokens | target_tokens
    token_jaccard = (
        len(missing_tokens & target_tokens) / len(union) if union else 0.0
    )
    sequence_ratio = difflib.SequenceMatcher(None, missing.text, target.text).ratio()

    substring_bonus = 0.0
    if missing.text and target.text and (
        missing.text in target.text or target.text in missing.text
    ):
        substring_bonus = 0.03

    exact_bonus = 0.0
    if missing.tokens == target.tokens:
        exact_bonus = 0.07

    score = min(
        1.0,
        (0.55 * token_jaccard)
        + (0.45 * sequence_ratio)
        + substring_bonus
        + exact_bonus,
    )

    reason = (
        "; ".join(missing.reasons)
        if missing.reasons
        else "normalized placeholder similarity"
    )

    return CandidateScore(entry=candidate, score=round(score, 4), reason=reason)


def _placeholder_prefix(token: str) -> str:
    return token.split(":", 1)[0] if ":" in token else ""


def _rank_candidates(
    missing_token: str,
    index: PgmrMemoryIndex,
) -> list[CandidateScore]:
    missing_prefix = _placeholder_prefix(missing_token)
    scores = [
        _score_candidate(missing_token, entry)
        for entry in index.entries
        if _placeholder_prefix(entry.placeholder) == missing_prefix
    ]
    return sorted(scores, key=lambda item: item.score, reverse=True)


def _entry_from_raw(item: dict[str, Any], fallback_family: str) -> PgmrMemoryEntry | None:
    family = str(item.get("family") or fallback_family).strip()
    placeholder = item.get("placeholder")
    canonical_uri = item.get("canonical_uri")

    if not family:
        return None
    if not isinstance(placeholder, str) or not placeholder.strip():
        return None
    if not isinstance(canonical_uri, str) or not canonical_uri.strip():
        return None

    aliases: list[str] = []
    for field_name in ("aliases", "placeholder_aliases"):
        value = item.get(field_name, [])
        if not isinstance(value, list):
            continue
        for alias in value:
            if isinstance(alias, str) and alias.strip():
                aliases.append(alias.strip())

    return PgmrMemoryEntry(
        family=family,
        placeholder=placeholder.strip(),
        canonical_uri=canonical_uri.strip(),
        aliases=tuple(dict.fromkeys(aliases)),
    )


def build_memory_index(entries: list[PgmrMemoryEntry]) -> PgmrMemoryIndex:
    index = PgmrMemoryIndex(entries=list(entries))

    for entry in entries:
        index.exact[entry.placeholder] = entry
        index.exact[canonicalize_pgmr_token(entry.placeholder)] = entry

        for alias in entry.aliases:
            if PGMR_TOKEN_PATTERN.fullmatch(alias):
                index.aliases[alias] = entry
                index.aliases[canonicalize_pgmr_token(alias)] = entry

    return index


def load_pgmr_memory_by_family(memory_dir: Path) -> dict[str, PgmrMemoryIndex]:
    """Load PGMR memory templates grouped by family."""
    raw_entries = load_memory_dir(memory_dir)
    grouped: dict[str, list[PgmrMemoryEntry]] = {}

    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        entry = _entry_from_raw(item, fallback_family="")
        if entry is None:
            continue
        grouped.setdefault(entry.family, []).append(entry)

    return {
        family: build_memory_index(entries)
        for family, entries in sorted(grouped.items())
    }


def build_entry_memory_index(
    entry: dict[str, Any],
    memory: dict[str, PgmrMemoryIndex],
) -> PgmrMemoryIndex:
    """Return the family-scoped memory index for a dataset entry."""
    family = str(entry.get("family", "")).strip()
    selected_entries: list[PgmrMemoryEntry] = []

    if family:
        selected_entries.extend(memory.get(family, PgmrMemoryIndex([])).entries)

    metadata = entry.get("entry_metadata")
    if isinstance(metadata, dict):
        metadata_family = str(metadata.get("family", "")).strip()
        if metadata_family and metadata_family != family:
            selected_entries.extend(
                memory.get(metadata_family, PgmrMemoryIndex([])).entries
            )

    return build_memory_index(selected_entries)


def _second_best_score(scores: list[CandidateScore]) -> float:
    return scores[1].score if len(scores) > 1 else 0.0


def _mapping_payload(
    *,
    missing_placeholder: str,
    candidate: CandidateScore,
    second_best_score: float,
    decision: str,
    candidate_field: str,
) -> dict[str, Any]:
    payload = {
        "missing_placeholder": missing_placeholder,
        candidate_field: candidate.entry.placeholder,
        "canonical_uri": candidate.entry.canonical_uri,
        "score": candidate.score,
        "second_best_score": second_best_score,
        "decision": decision,
        "reason": candidate.reason,
    }
    return payload


def restore_pgmr_query_with_diagnostics(
    pgmr_query: str,
    index: PgmrMemoryIndex,
    options: PgmrResolutionOptions | None = None,
) -> PgmrRestoreResult:
    """Restore PGMR placeholders and collect alias/similarity diagnostics."""
    options = options or PgmrResolutionOptions()
    missing: set[str] = set()
    alias_mappings: dict[str, dict[str, Any]] = {}
    auto_mappings: dict[str, dict[str, Any]] = {}
    suggestions: dict[str, dict[str, Any]] = {}

    def replace_token(match: re.Match[str]) -> str:
        token = match.group(0)

        entry = index.exact.get(token)
        if entry is None:
            entry = index.exact.get(canonicalize_pgmr_token(token))
        if entry is not None:
            return entry.canonical_uri

        entry = index.aliases.get(token)
        if entry is None:
            entry = index.aliases.get(canonicalize_pgmr_token(token))
        if entry is not None:
            alias_mappings[token] = {
                "alias": token,
                "mapped_to_placeholder": entry.placeholder,
                "canonical_uri": entry.canonical_uri,
                "decision": "mapped_exact_alias",
            }
            return entry.canonical_uri

        scores = _rank_candidates(token, index)
        best = scores[0] if scores else None
        second_best = _second_best_score(scores)

        if best is not None and options.enable_similarity_mapping:
            if (
                best.score >= options.auto_map_threshold
                and best.score - second_best >= options.min_margin
            ):
                auto_mappings[token] = _mapping_payload(
                    missing_placeholder=token,
                    candidate=best,
                    second_best_score=second_best,
                    decision="auto_mapped_similarity",
                    candidate_field="mapped_to_placeholder",
                )
                return best.entry.canonical_uri

        if best is not None and best.score >= options.suggestion_threshold:
            suggestions[token] = _mapping_payload(
                missing_placeholder=token,
                candidate=best,
                second_best_score=second_best,
                decision="suggested_manual_review",
                candidate_field="candidate_placeholder",
            )

        missing.add(token)
        return token

    restored = PGMR_TOKEN_PATTERN.sub(replace_token, pgmr_query)
    remaining = sorted(set(PGMR_TOKEN_PATTERN.findall(restored)))
    unmapped = sorted(missing)

    return PgmrRestoreResult(
        restored_query=restored,
        missing_mapping_tokens=unmapped,
        remaining_pgmr_tokens=remaining,
        used_mapping_count=len(index.exact),
        alias_mappings=list(alias_mappings.values()),
        auto_mappings=list(auto_mappings.values()),
        mapping_suggestions=list(suggestions.values()),
        unmapped_placeholders=unmapped,
    )
