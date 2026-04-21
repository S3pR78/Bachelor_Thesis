from __future__ import annotations

import re


COMMENT_LINE_RE = re.compile(r"^\s*#.*$")

INLINE_PREFIX_RE = re.compile(
    r"""
    \s*PREFIX
    \s+
    [A-Za-z_][\w\-]*:
    \s*
    <[^>]+>
    """,
    re.IGNORECASE | re.VERBOSE,
)


def strip_leading_comment_lines(query: str) -> str:
    """
    Remove leading comment-only lines, but keep inline comments elsewhere untouched.
    """
    lines = query.splitlines()
    start_index = 0

    while start_index < len(lines):
        line = lines[start_index]
        if not line.strip():
            start_index += 1
            continue
        if COMMENT_LINE_RE.match(line):
            start_index += 1
            continue
        break

    return "\n".join(lines[start_index:]).strip()


def strip_prefixes(query: str) -> str:
    """
    Remove leading PREFIX declarations whether they appear:
    - one per line
    - or inline in a single long line before the query body
    """
    remaining = query.lstrip()

    while True:
        match = INLINE_PREFIX_RE.match(remaining)
        if not match:
            break
        remaining = remaining[match.end():].lstrip()

    return remaining.strip()


def normalize_whitespace(query: str) -> str:
    """
    Normalize trailing spaces and collapse repeated blank lines.
    """
    lines = [line.rstrip() for line in query.splitlines()]

    normalized: list[str] = []
    previous_blank = False

    for line in lines:
        is_blank = not line.strip()
        if is_blank:
            if previous_blank:
                continue
            previous_blank = True
            normalized.append("")
        else:
            previous_blank = False
            normalized.append(line)

    return "\n".join(normalized).strip()


def normalize_sparql_for_storage(query: str) -> str:
    """
    Normalize a SPARQL query for dataset storage/comparison:
    - remove leading comments
    - remove leading PREFIX declarations
    - normalize whitespace
    """
    query = strip_leading_comment_lines(query)
    query = strip_prefixes(query)
    query = normalize_whitespace(query)
    return query.strip()