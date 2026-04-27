from __future__ import annotations

from collections import Counter
from typing import Any

from src.evaluate.query_text_normalization import normalize_sparql_query_text


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


def _is_statement_dot(text: str, index: int) -> bool:
    previous_char = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""

    previous_ok = previous_char.isspace()
    next_ok = next_char == "" or next_char.isspace() or next_char == "}"

    return previous_ok and next_ok


def _normalize_structure_pattern(pattern: str) -> str:
    normalized = " ".join(pattern.split()).strip()

    if normalized.endswith("."):
        normalized = normalized[:-1].strip()

    return normalized


def _should_finalize_group_pattern(pattern: str) -> bool:
    upper = _normalize_structure_pattern(pattern).upper()

    return upper.startswith(
        (
            "OPTIONAL {",
            "MINUS {",
            "GRAPH ",
            "SERVICE ",
        )
    )


def _split_body_statements(body: str) -> list[str]:
    """Split a lightweight WHERE body into statement-like patterns.

    The splitter handles the most common benchmark patterns conservatively:
    - top-level triples are split at standalone statement dots
    - dots inside nested groups such as OPTIONAL { ... . } are preserved
    - OPTIONAL/MINUS/GRAPH/SERVICE groups are treated as standalone patterns

    This is still SQM-lite, not a full SPARQL parser.
    """

    if not body:
        return []

    patterns: list[str] = []
    current: list[str] = []

    brace_depth = 0
    in_iri = False
    quote_char: str | None = None
    escaped = False

    def flush_current() -> None:
        pattern = _normalize_structure_pattern("".join(current))
        current.clear()

        if pattern:
            patterns.append(pattern)

    index = 0
    while index < len(body):
        char = body[index]

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

        if char == "{":
            brace_depth += 1
            current.append(char)
            index += 1
            continue

        if char == "}":
            current.append(char)
            if brace_depth > 0:
                brace_depth -= 1

            if brace_depth == 0 and _should_finalize_group_pattern("".join(current)):
                flush_current()

            index += 1
            continue

        if char == "." and brace_depth == 0 and _is_statement_dot(body, index):
            flush_current()
            index += 1
            continue

        current.append(char)
        index += 1

    flush_current()

    return patterns


def extract_sparql_structure_patterns(query: str | None) -> list[str]:
    """Extract lightweight structural patterns from a SPARQL query.

    The function does not perform full SPARQL parsing. It normalizes query text,
    extracts the outer WHERE body, and returns statement-like patterns.

    The result is suitable for SQM-lite style comparison, not for proving
    semantic equivalence.
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
