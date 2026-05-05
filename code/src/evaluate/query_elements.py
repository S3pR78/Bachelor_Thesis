"""Extract ORKG predicates/classes/resources from SPARQL query text."""

from __future__ import annotations

import re


PREFIX_TO_RESULT_KEY = {
    "orkgp": "predicate_refs",
    "orkgc": "class_refs",
    "orkgr": "resource_refs",
}

FULL_IRI_KIND_TO_PREFIX = {
    "predicate": "orkgp",
    "class": "orkgc",
    "resource": "orkgr",
}

FULL_IRI_KIND_TO_RESULT_KEY = {
    "predicate": "predicate_refs",
    "class": "class_refs",
    "resource": "resource_refs",
}

PREFIXED_ORKG_REF_RE = re.compile(
    r"(?<![\w-])(?P<prefix>orkgp|orkgc|orkgr):(?P<local>[A-Za-z_][A-Za-z0-9_-]*)",
    flags=re.IGNORECASE,
)

FULL_ORKG_IRI_RE = re.compile(
    r"https?://(?:www\.)?orkg\.org/orkg/"
    r"(?P<kind>predicate|class|resource)/"
    r"(?P<local>[A-Za-z_][A-Za-z0-9_-]*)",
    flags=re.IGNORECASE,
)

CODE_FENCE_RE = re.compile(
    r"^\s*```(?:sparql)?\s*|\s*```\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

STRING_LITERAL_RE = re.compile(
    r'"""[\s\S]*?"""'
    r"|'''[\s\S]*?'''"
    r'|"(?:\\.|[^"\\])*"'
    r"|'(?:\\.|[^'\\])*'",
    flags=re.MULTILINE,
)


def _empty_result() -> dict[str, frozenset[str]]:
    return {
        "predicate_refs": frozenset(),
        "class_refs": frozenset(),
        "resource_refs": frozenset(),
        "all_refs": frozenset(),
    }


def _strip_code_fences(text: str) -> str:
    return CODE_FENCE_RE.sub("", text)


def _mask_string_literals(text: str) -> str:
    return STRING_LITERAL_RE.sub(" ", text)


def _strip_comments(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        cleaned_lines.append(line.split("#", 1)[0])
    return "\n".join(cleaned_lines)


def _prepare_query_text(sparql_query: str) -> str:
    text = _strip_code_fences(sparql_query)
    text = _mask_string_literals(text)
    text = _strip_comments(text)
    return text


def extract_orkg_query_elements(
    sparql_query: str | None,
) -> dict[str, frozenset[str]]:
    """Extract canonical ORKG references from a SPARQL query.

    The function returns canonical prefixed references grouped by ORKG namespace.

    Examples:
    - orkgp:P181003
    - orkgp:HAS_EVALUATION
    - orkgc:C121001
    - orkgr:R1544125

    Both prefixed references and full ORKG IRIs are supported. Comments,
    string literals, and Markdown code fences are ignored.
    """

    if sparql_query is None:
        return _empty_result()

    if not isinstance(sparql_query, str):
        raise ValueError("sparql_query must be a string or None.")

    if not sparql_query.strip():
        return _empty_result()

    text = _prepare_query_text(sparql_query)

    refs: dict[str, set[str]] = {
        "predicate_refs": set(),
        "class_refs": set(),
        "resource_refs": set(),
    }

    for match in PREFIXED_ORKG_REF_RE.finditer(text):
        prefix = match.group("prefix").lower()
        local = match.group("local")
        result_key = PREFIX_TO_RESULT_KEY[prefix]
        refs[result_key].add(f"{prefix}:{local}")

    for match in FULL_ORKG_IRI_RE.finditer(text):
        kind = match.group("kind").lower()
        local = match.group("local")
        prefix = FULL_IRI_KIND_TO_PREFIX[kind]
        result_key = FULL_IRI_KIND_TO_RESULT_KEY[kind]
        refs[result_key].add(f"{prefix}:{local}")

    all_refs = (
        refs["predicate_refs"]
        | refs["class_refs"]
        | refs["resource_refs"]
    )

    return {
        "predicate_refs": frozenset(refs["predicate_refs"]),
        "class_refs": frozenset(refs["class_refs"]),
        "resource_refs": frozenset(refs["resource_refs"]),
        "all_refs": frozenset(all_refs),
    }


def get_orkg_ref_counts(sparql_query: str | None) -> dict[str, int]:
    elements = extract_orkg_query_elements(sparql_query)

    return {
        "predicate_ref_count": len(elements["predicate_refs"]),
        "class_ref_count": len(elements["class_refs"]),
        "resource_ref_count": len(elements["resource_refs"]),
        "all_ref_count": len(elements["all_refs"]),
    }
