from __future__ import annotations

import re


PREFIX_LINE_RE = re.compile(
    r"^\s*PREFIX\s+[A-Za-z_][\w\-]*:\s*<[^>]+>\s*$",
    re.IGNORECASE,
)

COMMENT_LINE_RE = re.compile(r"^\s*#.*$")


def strip_prefix_lines(query: str) -> str:
    """
    Remove full PREFIX lines from a SPARQL query while preserving the query body.
    """
    lines = query.splitlines()
    kept_lines: list[str] = []

    for line in lines:
        if PREFIX_LINE_RE.match(line):
            continue
        kept_lines.append(line)

    return "\n".join(kept_lines).strip()


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
    - remove PREFIX lines
    - normalize whitespace
    """
    query = strip_leading_comment_lines(query)
    query = strip_prefix_lines(query)
    query = normalize_whitespace(query)
    return query.strip()