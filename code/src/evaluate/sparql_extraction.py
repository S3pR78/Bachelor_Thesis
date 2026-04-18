from __future__ import annotations

import re


QUERY_START_PATTERN = re.compile(
    r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b",
    flags=re.IGNORECASE,
)


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()

    fenced_match = re.search(
        r"```(?:sparql|sql)?\s*(.*?)```",
        stripped,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced_match:
        return fenced_match.group(1).strip()

    return stripped


def _remove_comment_lines(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _remove_prefix_lines(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        if re.match(r"^\s*PREFIX\b", line, flags=re.IGNORECASE):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def extract_sparql_query(raw_output: str) -> str | None:
    if not isinstance(raw_output, str) or not raw_output.strip():
        return None

    text = _strip_code_fences(raw_output)
    text = _remove_comment_lines(text)
    text = _remove_prefix_lines(text)

    match = QUERY_START_PATTERN.search(text)
    if not match:
        return None

    extracted = text[match.start():].strip()
    return extracted or None