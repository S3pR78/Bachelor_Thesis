from __future__ import annotations

import re


SOLUTION_MODIFIER_PATTERN = re.compile(
    r"\b(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET)\b",
    flags=re.IGNORECASE,
)


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()

    cleaned = re.sub(
        r"^\s*```(?:sparql|sql|ttl|turtle)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    return cleaned.strip()


def split_solution_modifiers(text: str) -> tuple[str, str]:
    match = SOLUTION_MODIFIER_PATTERN.search(text)
    if not match:
        return text.strip(), ""

    return text[: match.start()].strip(), text[match.start():].strip()


def add_missing_where_braces(query: str) -> str:
    text = query.strip()

    match = re.search(r"\bWHERE\b", text, flags=re.IGNORECASE)
    if not match:
        return text

    if re.search(r"\bWHERE\s*\{", text, flags=re.IGNORECASE):
        return text

    before_where = text[: match.end()].strip()
    after_where = text[match.end():].strip()

    if not after_where:
        return text

    body, modifiers = split_solution_modifiers(after_where)

    fixed = f"{before_where} {{ {body} }}"
    if modifiers:
        fixed = f"{fixed} {modifiers}"

    return fixed.strip()


def move_solution_modifiers_outside_where(query: str) -> str:
    text = query.strip()

    where_match = re.search(r"\bWHERE\s*\{", text, flags=re.IGNORECASE)
    if not where_match:
        return text

    open_brace_index = text.find("{", where_match.start())
    if open_brace_index < 0:
        return text

    depth = 0
    close_brace_index = -1

    for i in range(open_brace_index, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                close_brace_index = i
                break

    if close_brace_index == -1:
        before_body = text[: open_brace_index + 1]
        body = text[open_brace_index + 1:].strip()
        after_body = ""
    else:
        before_body = text[: open_brace_index + 1]
        body = text[open_brace_index + 1: close_brace_index].strip()
        after_body = text[close_brace_index + 1:].strip()

    body_without_modifiers, modifiers_from_body = split_solution_modifiers(body)

    fixed = f"{before_body} {body_without_modifiers} }}"
    combined_modifiers = " ".join(
        part for part in [modifiers_from_body, after_body] if part
    ).strip()

    if combined_modifiers:
        fixed = f"{fixed} {combined_modifiers}"

    return fixed.strip()


def wrap_bare_optional_patterns(query: str) -> str:
    pattern = re.compile(
        r"\bOPTIONAL\s+(?!\{)"
        r"(\?[A-Za-z_][A-Za-z0-9_]*\s+"
        r"(?:[A-Za-z_][A-Za-z0-9_]*:)?[A-Za-z_][A-Za-z0-9_]*\s+"
        r"\?[A-Za-z_][A-Za-z0-9_]*)(\s*\.)?",
        flags=re.IGNORECASE,
    )

    def repl(match: re.Match[str]) -> str:
        triple = match.group(1).strip()
        return f"OPTIONAL {{ {triple} . }}"

    return pattern.sub(repl, query)

def postprocess_pgmr_query(query: str) -> str:
    fixed = strip_markdown_fences(query)
    fixed = normalize_spaces(fixed)

    # normalize_spaces can turn fenced markdown into one line:
    # ```sparql SELECT ... ```
    fixed = strip_markdown_fences(fixed)

    fixed = add_missing_where_braces(fixed)
    fixed = wrap_bare_optional_patterns(fixed)
    fixed = move_solution_modifiers_outside_where(fixed)

    fixed = normalize_spaces(fixed)
    fixed = strip_markdown_fences(fixed)
    fixed = normalize_spaces(fixed)
    return fixed
