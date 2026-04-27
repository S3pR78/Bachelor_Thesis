from __future__ import annotations

import re


CODE_FENCE_RE = re.compile(
    r"^\s*```(?:sparql)?\s*|\s*```\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

PREFIX_RE = re.compile(
    r"^\s*PREFIX\s+(?P<prefix>[A-Za-z][A-Za-z0-9_-]*):\s*<(?P<iri>[^>]+)>\s*$",
    flags=re.IGNORECASE,
)

BASE_RE = re.compile(
    r"^\s*BASE\s+<(?P<iri>[^>]+)>\s*$",
    flags=re.IGNORECASE,
)


def strip_markdown_code_fences(text: str) -> str:
    return CODE_FENCE_RE.sub("", text).strip()


def strip_sparql_comments(text: str) -> str:
    """Remove SPARQL comments while keeping # inside quoted string literals."""

    result: list[str] = []
    i = 0
    quote_char: str | None = None
    triple_quote = False
    escaped = False

    while i < len(text):
        char = text[i]

        if quote_char is None:
            if char in {"'", '"'}:
                if text[i : i + 3] == char * 3:
                    quote_char = char
                    triple_quote = True
                    result.append(char * 3)
                    i += 3
                    continue

                quote_char = char
                triple_quote = False
                result.append(char)
                i += 1
                continue

            if char == "#":
                while i < len(text) and text[i] != "\n":
                    i += 1
                continue

            result.append(char)
            i += 1
            continue

        result.append(char)

        if escaped:
            escaped = False
            i += 1
            continue

        if char == "\\":
            escaped = True
            i += 1
            continue

        if triple_quote and text[i : i + 3] == quote_char * 3:
            # We already appended the first quote above. Append the remaining
            # two quotes and close the triple-quoted string.
            result.append(quote_char * 2)
            i += 3
            quote_char = None
            triple_quote = False
            continue

        if not triple_quote and char == quote_char:
            quote_char = None

        i += 1

    return "".join(result)


def _normalize_prefix_line(line: str) -> str | None:
    match = PREFIX_RE.match(line)
    if not match:
        return None

    prefix = match.group("prefix").lower()
    iri = match.group("iri").strip()
    return f"PREFIX {prefix}: <{iri}>"


def _normalize_base_line(line: str) -> str | None:
    match = BASE_RE.match(line)
    if not match:
        return None

    iri = match.group("iri").strip()
    return f"BASE <{iri}>"


def _normalize_body_spacing(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()

    # Normalize spacing around punctuation that is safe outside IRIs.
    # We intentionally do not normalize "." because dots can occur inside IRIs
    # and numeric literals.
    text = re.sub(r"\s*([{}();,])\s*", r" \1 ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_sparql_query_text(query: str | None) -> str:
    """Normalize SPARQL text for lightweight query-string comparison.

    This is not a semantic SPARQL equivalence checker. It performs conservative
    text normalization:

    - remove Markdown code fences
    - remove comments outside string literals
    - normalize whitespace
    - normalize and sort PREFIX declarations
    - normalize BASE declarations
    - keep the query body order unchanged

    The output is intended for normalized exact match and token-based metrics
    such as BLEU.
    """

    if query is None:
        return ""

    if not isinstance(query, str):
        raise ValueError("query must be a string or None.")

    text = strip_markdown_code_fences(query)
    text = strip_sparql_comments(text)

    prefix_lines: set[str] = set()
    base_lines: set[str] = set()
    body_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        prefix_line = _normalize_prefix_line(line)
        if prefix_line is not None:
            prefix_lines.add(prefix_line)
            continue

        base_line = _normalize_base_line(line)
        if base_line is not None:
            base_lines.add(base_line)
            continue

        body_lines.append(line)

    normalized_parts: list[str] = []
    normalized_parts.extend(sorted(base_lines))
    normalized_parts.extend(sorted(prefix_lines))

    body = _normalize_body_spacing(" ".join(body_lines))
    if body:
        normalized_parts.append(body)

    return "\n".join(normalized_parts)


def tokenize_normalized_sparql(query: str | None) -> list[str]:
    normalized = normalize_sparql_query_text(query)
    if not normalized:
        return []

    return normalized.replace("\n", " ").split()
