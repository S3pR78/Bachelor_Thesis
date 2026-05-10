from __future__ import annotations

from typing import Any
import re

from ace.orkg.context import normalize_scope
from ace.orkg.memory_context import allowed_placeholders_for_family


FORBIDDEN_REFERENCE_TERMS = (
    "gold query",
    "gold answer",
    "reference query",
    "reference answer",
    "expected query",
    "hidden label",
    "hidden reference",
)

PGMR_LITE_FORBIDDEN_TERMS = (
    "orkgp:",
    "orkgc:",
    "orkgr:",
    "orkg predicate",
    "orkg predicates",
    "orkg class",
    "orkg classes",
    "orkg resource",
    "orkg resources",
)


SPARQL_FORBIDDEN_PLACEHOLDER_TERMS = (
    "pgmr:",
    "pgmrc:",
    "pgmr placeholder",
    "pgmr-lite placeholder",
    "pgmr-lite placeholders",
)

PGMR_TOKEN_RE = re.compile(r"\b(?:pgmr|pgmrc):[A-Za-z0-9_]+\b")

VAGUE_RULE_PHRASES = (
    "check the query",
    "verify the query",
    "ensure correctness",
    "use the correct predicates",
    "use correct predicates",
    "avoid mistakes",
    "be accurate",
)


PGMR_BAD_STRUCTURE_PATTERNS = (
    (
        "has_contribution_to_year",
        re.compile(r"pgmr:has_contribution\s+\?year\b", re.IGNORECASE),
    ),
    (
        "publication_year_on_contribution_variable",
        re.compile(r"\?contribution\s+pgmr:publication_year\b", re.IGNORECASE),
    ),
    (
        "publication_year_after_contribution_arrow",
        re.compile(r"contribution\s*(?:->|→).*pgmr:publication_year", re.IGNORECASE),
    ),
    (
        "has_contribution_arrow_publication_year",
        re.compile(r"pgmr:has_contribution\s*(?:->|→).*pgmr:publication_year", re.IGNORECASE),
    ),
)


def operation_content(operation: dict[str, Any]) -> str:
    value = operation.get("content", "")
    return str(value or "").strip()


def is_empty_or_invalid_operation(operation: dict[str, Any]) -> bool:
    if not isinstance(operation, dict):
        return True

    if operation.get("type") != "ADD":
        # The current ACE integration only relies on ADD operations.
        # Other operation types can be supported later when needed.
        return True

    if not operation_content(operation):
        return True

    return False


def contains_forbidden_reference_terms(text: str) -> bool:
    normalized = text.lower()
    return any(term in normalized for term in FORBIDDEN_REFERENCE_TERMS)


def violates_prediction_format(text: str, prediction_format: str) -> bool:
    normalized_format = normalize_scope(prediction_format)
    normalized_text = text.lower()

    if normalized_format == "pgmr_lite":
        return any(term in normalized_text for term in PGMR_LITE_FORBIDDEN_TERMS)

    if normalized_format in {"sparql", "direct_sparql"}:
        return any(term in normalized_text for term in SPARQL_FORBIDDEN_PLACEHOLDER_TERMS)

    return False


def uses_unknown_pgmr_placeholder(text: str, *, family: str, prediction_format: str) -> bool:
    """Reject PGMR-lite rules that mention placeholders outside the family prompt."""
    if normalize_scope(prediction_format) != "pgmr_lite":
        return False

    mentioned = set(PGMR_TOKEN_RE.findall(text))
    if not mentioned:
        return False

    allowed = allowed_placeholders_for_family(family)
    if not allowed:
        # If the family prompt cannot be loaded, do not reject based on this check.
        return False

    return not mentioned.issubset(allowed)


def is_vague_rule(text: str) -> bool:
    normalized = text.lower().strip().rstrip(".")
    return normalized in VAGUE_RULE_PHRASES


def violates_known_pgmr_structure(text: str, *, prediction_format: str) -> bool:
    """Reject known-bad PGMR-lite structural descriptions.

    This is intentionally narrow. It does not try to validate arbitrary PGMR-lite
    syntax; it only blocks recurring harmful playbook-rule patterns.
    """
    if normalize_scope(prediction_format) != "pgmr_lite":
        return False

    return any(pattern.search(text) for _name, pattern in PGMR_BAD_STRUCTURE_PATTERNS)


def validate_operation(
    operation: dict[str, Any],
    *,
    family: str,
    prediction_format: str,
) -> tuple[bool, str | None]:
    """Return whether an ACE curator operation is safe for a playbook.

    The guard is intentionally conservative and format-aware:
    - PGMR-lite rules must not contain real ORKG IDs.
    - SPARQL rules may contain ORKG IDs.
    - No rule may mention gold/reference targets.
    """
    if is_empty_or_invalid_operation(operation):
        return False, "empty_or_unsupported_operation"

    content = operation_content(operation)

    if contains_forbidden_reference_terms(content):
        return False, "mentions_gold_or_reference_target"

    if violates_prediction_format(content, prediction_format):
        return False, "violates_prediction_format"

    if uses_unknown_pgmr_placeholder(content, family=family, prediction_format=prediction_format):
        return False, "unknown_pgmr_placeholder"

    if violates_known_pgmr_structure(content, prediction_format=prediction_format):
        return False, "known_bad_pgmr_structure"

    if is_vague_rule(content):
        return False, "vague_rule"

    # Very light family leakage protection. Keep this narrow because the two
    # ORKG templates intentionally share broad concepts such as data, methods,
    # metrics, and evaluation.
    normalized_family = normalize_scope(family)
    normalized_content = content.lower()

    if normalized_family == "nlp4re" and "empirical_research_practice" in normalized_content:
        return False, "cross_family_leakage"

    if normalized_family == "empirical_research_practice" and "nlp4re" in normalized_content:
        return False, "cross_family_leakage"

    return True, None


def filter_safe_operations(
    operations: list[dict[str, Any]],
    *,
    family: str,
    prediction_format: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter unsafe curator operations.

    Returns:
        (safe_operations, rejected_operations)

    Each rejected operation includes a safety_rejection_reason field.
    """
    safe: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for operation in operations:
        is_valid, reason = validate_operation(
            operation,
            family=family,
            prediction_format=prediction_format,
        )

        if is_valid:
            safe.append(operation)
        else:
            rejected_operation = dict(operation) if isinstance(operation, dict) else {
                "operation": operation
            }
            rejected_operation["safety_rejection_reason"] = reason or "unknown"
            rejected.append(rejected_operation)

    return safe, rejected
