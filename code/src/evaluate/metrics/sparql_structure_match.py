from __future__ import annotations

import re
from collections import Counter
from typing import Any

from src.evaluate.query_text_normalization import normalize_sparql_query_text


VARIABLE_RE = re.compile(r"\?[A-Za-z_][A-Za-z0-9_]*")
FILTER_RE = re.compile(r"FILTER\s*\([^)]*\)", flags=re.IGNORECASE)


def _build_non_comparable_metric(reason: str) -> dict[str, Any]:
    return {
        "metric": "sparql_structure_match",
        "type": "query_based",
        "comparable": False,
        "value": None,
        "precision": None,
        "recall": None,
        "f1": None,
        "reason": reason,
        "comparison_mode": "sqm_lite",
        "matched_pattern_count": None,
        "prediction_pattern_count": None,
        "gold_pattern_count": None,
        "missing_gold_patterns": [],
        "extra_predicted_patterns": [],
        "matched_patterns": [],
    }


def _strip_prefix_and_base_lines(normalized_query: str) -> str:
    lines = []
    for line in normalized_query.splitlines():
        upper = line.upper()
        if upper.startswith("PREFIX ") or upper.startswith("BASE "):
            continue
        lines.append(line)
    return " ".join(lines).strip()


def _extract_outer_where_body(normalized_query: str) -> str:
    query = _strip_prefix_and_base_lines(normalized_query)

    start = query.find("{")
    end = query.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return ""

    return query[start + 1 : end].strip()


def _normalize_variables(pattern: str) -> str:
    """Normalize variable names for lightweight structure comparison.

    SQM-lite should primarily capture structural overlap and predicate/class
    usage, not arbitrary variable naming choices such as ?external vs
    ?externalValidity.
    """

    return VARIABLE_RE.sub("?VAR", pattern)


def _normalize_structure_pattern(pattern: str) -> str:
    normalized = " ".join(pattern.split()).strip()

    normalized = normalized.strip("{} ")
    if normalized.endswith("."):
        normalized = normalized[:-1].strip()

    # Remove group keywords that should not prevent pattern overlap.
    normalized = re.sub(
        r"^(OPTIONAL|MINUS)\s+",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).strip()

    normalized = _normalize_variables(normalized)
    normalized = " ".join(normalized.split()).strip()

    return normalized


def _is_statement_dot(text: str, index: int) -> bool:
    previous_char = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""

    # SPARQL statement dots may appear as either:
    #   ?s ?p ?o .
    # or compactly:
    #   ?s ?p ?o.
    #
    # We therefore mainly require that the next character ends the statement.
    # Dots inside IRIs are already protected by the in_iri state in the caller.
    # Decimal literals such as 1.0 are not matched because the next character is
    # not whitespace/end/closing brace.
    previous_ok = previous_char != ""
    next_ok = next_char == "" or next_char.isspace() or next_char == "}"

    return previous_ok and next_ok


def _split_standalone_dot_statements(text: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []

    in_iri = False
    quote_char: str | None = None
    escaped = False

    def flush_current() -> None:
        statement = "".join(current).strip()
        current.clear()
        if statement:
            statements.append(statement)

    index = 0
    while index < len(text):
        char = text[index]

        if quote_char is not None:
            current.append(char)

            if escaped:
                escaped = False
                index += 1
                continue

            if char == "\\":
                escaped = True
                index += 1
                continue

            if char == quote_char:
                quote_char = None

            index += 1
            continue

        if in_iri:
            current.append(char)
            if char == ">":
                in_iri = False
            index += 1
            continue

        if char in {"'", '"'}:
            quote_char = char
            current.append(char)
            index += 1
            continue

        if char == "<":
            in_iri = True
            current.append(char)
            index += 1
            continue

        if char == "." and _is_statement_dot(text, index):
            flush_current()
            index += 1
            continue

        current.append(char)
        index += 1

    flush_current()
    return statements


def _extract_filter_patterns(body: str) -> list[str]:
    patterns: list[str] = []

    for match in FILTER_RE.finditer(body):
        pattern = _normalize_structure_pattern(match.group(0))
        if pattern:
            patterns.append(pattern)

    return patterns


def _remove_filter_patterns(body: str) -> str:
    return FILTER_RE.sub(" ", body)


def _flatten_group_syntax(body: str) -> str:
    """Flatten common SPARQL group syntax for SQM-lite extraction.

    This intentionally does not implement full SPARQL parsing. It makes common
    benchmark patterns easier to compare:

    - OPTIONAL/MINUS wrappers are removed
    - braces become statement boundaries
    - nested OPTIONAL blocks can be split into their inner triple patterns
    """

    body = re.sub(r"\b(?:OPTIONAL|MINUS)\b", " ", body, flags=re.IGNORECASE)

    # Treat group boundaries as statement separators. This is important for
    # OPTIONAL { ?s ?p ?o } patterns that often do not end with a dot.
    body = body.replace("{", " . ")
    body = body.replace("}", " . ")

    return body


def _expand_property_list_statement(statement: str) -> list[str]:
    """Expand simple SPARQL semicolon property lists.

    Example:
    ?paper orkgp:P31 ?contribution ; orkgp:P29 ?year

    becomes:
    ?paper orkgp:P31 ?contribution
    ?paper orkgp:P29 ?year
    """

    statement = " ".join(statement.split()).strip()
    if not statement:
        return []

    parts = [part.strip() for part in statement.split(";") if part.strip()]
    if not parts:
        return []

    first_tokens = parts[0].split()
    if len(first_tokens) < 3:
        return [_normalize_structure_pattern(statement)]

    subject = first_tokens[0]
    patterns = [_normalize_structure_pattern(parts[0])]

    for part in parts[1:]:
        tokens = part.split()
        if len(tokens) < 2:
            continue

        patterns.append(
            _normalize_structure_pattern(f"{subject} {part}")
        )

    return [pattern for pattern in patterns if pattern]


def _split_body_statements(body: str) -> list[str]:
    if not body:
        return []

    filter_patterns = _extract_filter_patterns(body)

    body_without_filters = _remove_filter_patterns(body)
    flattened_body = _flatten_group_syntax(body_without_filters)

    raw_statements = _split_standalone_dot_statements(flattened_body)

    patterns: list[str] = []
    for statement in raw_statements:
        patterns.extend(_expand_property_list_statement(statement))

    patterns.extend(filter_patterns)

    # Remove empty and obviously broken one-token fragments.
    cleaned_patterns = []
    for pattern in patterns:
        pattern = _normalize_structure_pattern(pattern)
        if not pattern:
            continue
        if pattern in {".", ";"}:
            continue
        if len(pattern.split()) < 2 and not pattern.upper().startswith("FILTER"):
            continue
        cleaned_patterns.append(pattern)

    return cleaned_patterns


def extract_sparql_structure_patterns(query: str | None) -> list[str]:
    """Extract lightweight structural patterns from a SPARQL query.

    This is SQM-lite, not full SPARQL algebra comparison.

    The extraction is intentionally relaxed:
    - query text is normalized first
    - outer WHERE body is extracted
    - OPTIONAL wrappers are flattened
    - semicolon property lists are expanded
    - variable names are normalized to ?VAR
    - FILTER expressions are kept as separate structural patterns
    """

    if query is None:
        return []

    if not isinstance(query, str):
        raise ValueError("query must be a string or None.")

    normalized_query = normalize_sparql_query_text(query)
    body = _extract_outer_where_body(normalized_query)
    return _split_body_statements(body)


def _counter_intersection_count(
    prediction_counter: Counter[str],
    gold_counter: Counter[str],
) -> int:
    return sum((prediction_counter & gold_counter).values())


def _counter_difference_items(
    left: Counter[str],
    right: Counter[str],
) -> list[str]:
    diff = left - right

    items: list[str] = []
    for pattern in sorted(diff):
        items.extend([pattern] * diff[pattern])

    return items


def compute_sparql_structure_match(
    *,
    prediction_query: str | None,
    gold_query: str | None,
) -> dict[str, Any]:
    """Compute SQM-lite structural match over normalized SPARQL patterns.

    This metric is query-based. It ignores the order of extracted WHERE-body
    patterns and computes precision, recall, and F1 over pattern overlap.
    """

    if prediction_query is None or not str(prediction_query).strip():
        return _build_non_comparable_metric("prediction_query_missing")

    if gold_query is None or not str(gold_query).strip():
        return _build_non_comparable_metric("gold_query_missing")

    prediction_patterns = extract_sparql_structure_patterns(prediction_query)
    gold_patterns = extract_sparql_structure_patterns(gold_query)

    prediction_counter = Counter(prediction_patterns)
    gold_counter = Counter(gold_patterns)

    prediction_pattern_count = sum(prediction_counter.values())
    gold_pattern_count = sum(gold_counter.values())
    matched_pattern_count = _counter_intersection_count(
        prediction_counter,
        gold_counter,
    )

    if prediction_pattern_count == 0 and gold_pattern_count == 0:
        precision = 1.0
        recall = 1.0
        f1 = 1.0
    else:
        precision = (
            0.0
            if prediction_pattern_count == 0
            else matched_pattern_count / prediction_pattern_count
        )
        recall = (
            0.0
            if gold_pattern_count == 0
            else matched_pattern_count / gold_pattern_count
        )
        f1 = (
            0.0
            if (precision + recall) == 0.0
            else (2.0 * precision * recall) / (precision + recall)
        )

    missing_gold_patterns = _counter_difference_items(
        gold_counter,
        prediction_counter,
    )
    extra_predicted_patterns = _counter_difference_items(
        prediction_counter,
        gold_counter,
    )
    matched_patterns = _counter_difference_items(
        prediction_counter & gold_counter,
        Counter(),
    )

    return {
        "metric": "sparql_structure_match",
        "type": "query_based",
        "comparable": True,
        "value": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "comparison_mode": "sqm_lite",
        "matched_pattern_count": matched_pattern_count,
        "prediction_pattern_count": prediction_pattern_count,
        "gold_pattern_count": gold_pattern_count,
        "missing_gold_patterns": missing_gold_patterns,
        "extra_predicted_patterns": extra_predicted_patterns,
        "matched_patterns": matched_patterns,
    }
