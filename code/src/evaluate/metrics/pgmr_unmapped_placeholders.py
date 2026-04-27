from __future__ import annotations

import re
from typing import Any


CURLY_PLACEHOLDER_RE = re.compile(
    r"\{\{\s*[A-Za-z0-9_.:-]+\s*\}\}"
)

SQUARE_PLACEHOLDER_RE = re.compile(
    r"\[\s*(?:UNMAPPED|UNKNOWN|PLACEHOLDER|TODO)[A-Za-z0-9_.:-]*\s*\]",
    flags=re.IGNORECASE,
)

# Conservative angle placeholder pattern:
# detects <NLP_TASK>, <PREDICATE_RE_TASK>, <UNKNOWN_CLASS>
# but does not match real IRIs like <http://orkg.org/...>.
ANGLE_PLACEHOLDER_RE = re.compile(
    r"<\s*(?!https?://)(?!urn:)(?!mailto:)[A-Z][A-Z0-9_:-]{2,}\s*>"
)

TOKEN_PLACEHOLDER_RE = re.compile(
    r"(?<![<\[\{A-Za-z0-9_:-])"
    r"(?:PGMR_UNKNOWN|PGMR_UNMAPPED|UNMAPPED|UNKNOWN|PLACEHOLDER)"
    r"[A-Z0-9_:-]*"
    r"(?![>\]\}A-Za-z0-9_:-])"
)


def extract_pgmr_unmapped_placeholders(query_text: str | None) -> list[str]:
    """Extract likely unresolved PGMR-lite placeholders from query text.

    This function is intentionally conservative. It detects common placeholder
    patterns without treating normal SPARQL variables or full IRIs as unmapped.
    """

    if query_text is None:
        return []

    if not isinstance(query_text, str):
        raise ValueError("query_text must be a string or None.")

    placeholders: set[str] = set()

    for regex in [
        CURLY_PLACEHOLDER_RE,
        SQUARE_PLACEHOLDER_RE,
        ANGLE_PLACEHOLDER_RE,
        TOKEN_PLACEHOLDER_RE,
    ]:
        for match in regex.finditer(query_text):
            placeholders.add(match.group(0).strip())

    return sorted(placeholders)



def build_pgmr_unmapped_placeholders_not_applicable(
    *,
    reason: str = "not_pgmr_mode",
) -> dict[str, Any]:
    return {
        "metric": "pgmr_unmapped_placeholders",
        "type": "pgmr_based",
        "comparable": False,
        "value": None,
        "has_unmapped_placeholders": None,
        "unmapped_placeholder_count": None,
        "unmapped_placeholders": [],
        "reason": reason,
    }

def compute_pgmr_unmapped_placeholders(
    *,
    prediction_query: str | None,
) -> dict[str, Any]:
    """Detect unresolved PGMR-lite placeholders in a predicted query.

    value semantics:
    - 0.0 means no unresolved placeholder was detected
    - 1.0 means at least one unresolved placeholder was detected
    """

    if prediction_query is None or not str(prediction_query).strip():
        return {
            "metric": "pgmr_unmapped_placeholders",
            "type": "pgmr_based",
            "comparable": False,
            "value": None,
            "has_unmapped_placeholders": None,
            "unmapped_placeholder_count": None,
            "unmapped_placeholders": [],
            "reason": "prediction_query_missing",
        }

    placeholders = extract_pgmr_unmapped_placeholders(prediction_query)
    has_unmapped_placeholders = len(placeholders) > 0

    return {
        "metric": "pgmr_unmapped_placeholders",
        "type": "pgmr_based",
        "comparable": True,
        "value": 1.0 if has_unmapped_placeholders else 0.0,
        "has_unmapped_placeholders": has_unmapped_placeholders,
        "unmapped_placeholder_count": len(placeholders),
        "unmapped_placeholders": placeholders,
    }
