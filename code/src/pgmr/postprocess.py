"""Lightweight cleanup for model-generated PGMR-lite/SPARQL text."""

from __future__ import annotations

import re


SOLUTION_MODIFIER_PATTERN = re.compile(
    r"\b(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET)\b",
    flags=re.IGNORECASE,
)
VARIABLE_PATTERN = r"\?[A-Za-z_][A-Za-z0-9_]*"
SIMPLE_TRIPLE_PATTERN = re.compile(
    rf"\s*(?P<subject>{VARIABLE_PATTERN})\s+"
    r"(?P<predicate>a|[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_-]*)\s+"
    rf"(?P<object>{VARIABLE_PATTERN}|[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_-]*|"
    r'"(?:\\.|[^"\\])*")\s*\.',
    flags=re.IGNORECASE,
)
LABEL_TRIPLE_PATTERN = re.compile(
    rf"(?P<triple>(?P<subject>{VARIABLE_PATTERN})\s+rdfs:label\s+"
    rf"(?P<label>{VARIABLE_PATTERN})\s*\.)",
    flags=re.IGNORECASE,
)
FILTER_REGEX_PATTERN = re.compile(
    r"\bFILTER\s*(?P<filter_open>\()\s*REGEX\s*(?P<regex_open>\()",
    flags=re.IGNORECASE,
)
FILTER_NOT_EXISTS_PATTERN = re.compile(
    r"\bFILTER\s+NOT\s+EXISTS\b(?!\s*\{)",
    flags=re.IGNORECASE,
)
BLOCK_START_PATTERN = re.compile(
    r"\s*(?:\}|(?:OPTIONAL|FILTER|BIND|VALUES|UNION|SERVICE|MINUS|SELECT|"
    r"WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET)\b)",
    flags=re.IGNORECASE,
)


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _scan_matching_delimiter(
    text: str,
    open_index: int,
    open_char: str,
    close_char: str,
) -> int | None:
    """Return the matching delimiter index, ignoring delimiters in strings."""
    if open_index < 0 or open_index >= len(text) or text[open_index] != open_char:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(open_index, len(text)):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index

    return None


def _has_top_level_equality_without_comma(text: str) -> bool:
    depth = 0
    in_string = False
    escaped = False
    has_equality = False

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif depth == 0 and char == ",":
            return False
        elif depth == 0 and char == "=":
            before = text[index - 1] if index > 0 else ""
            after = text[index + 1] if index + 1 < len(text) else ""
            if before not in "!<>" and after != "=":
                has_equality = True

    return has_equality


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
    """Wrap a bare WHERE body in braces when the model omitted them."""
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
    """Move GROUP BY/LIMIT/etc. out of the WHERE body when needed."""
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
    """Turn `OPTIONAL ?s ?p ?o` into legal `OPTIONAL { ?s ?p ?o . }`."""
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


def repair_malformed_filter_not_exists(query: str) -> str:
    """Wrap simple malformed `FILTER NOT EXISTS` triple chains in braces."""
    parts: list[str] = []
    cursor = 0

    while True:
        match = FILTER_NOT_EXISTS_PATTERN.search(query, cursor)
        if not match:
            parts.append(query[cursor:])
            break

        parts.append(query[cursor: match.start()])
        scan_index = match.end()
        triples: list[str] = []
        previous_object: str | None = None

        while True:
            if BLOCK_START_PATTERN.match(query, scan_index):
                break

            triple_match = SIMPLE_TRIPLE_PATTERN.match(query, scan_index)
            if not triple_match:
                break

            subject = triple_match.group("subject")
            object_value = triple_match.group("object")
            if triples and subject != previous_object:
                break

            triples.append(triple_match.group(0).strip())
            previous_object = (
                object_value if re.fullmatch(VARIABLE_PATTERN, object_value) else None
            )
            scan_index = triple_match.end()

            if previous_object is None:
                break

        if triples:
            parts.append(f"FILTER NOT EXISTS {{ {' '.join(triples)} }}")
            cursor = scan_index
        else:
            parts.append(match.group(0))
            cursor = match.end()

    return "".join(parts)


def normalize_malformed_regex_equality_filters(query: str) -> str:
    """Turn malformed `FILTER(REGEX(A = B))` wrappers into equality filters."""
    parts: list[str] = []
    cursor = 0
    search_start = 0

    while True:
        match = FILTER_REGEX_PATTERN.search(query, search_start)
        if not match:
            parts.append(query[cursor:])
            break

        filter_open = match.start("filter_open")
        regex_open = match.start("regex_open")
        regex_close = _scan_matching_delimiter(query, regex_open, "(", ")")
        if regex_close is None:
            search_start = match.end()
            continue

        content = query[regex_open + 1: regex_close].strip()
        if not _has_top_level_equality_without_comma(content):
            search_start = regex_close + 1
            continue

        filter_close = _scan_matching_delimiter(query, filter_open, "(", ")")
        replacement_end = (
            filter_close + 1 if filter_close is not None else regex_close + 1
        )
        parts.append(query[cursor: match.start()])
        parts.append(f"FILTER({content})")
        cursor = replacement_end
        search_start = replacement_end

    return "".join(parts)


def _optional_ranges(query: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for match in re.finditer(r"\bOPTIONAL\s*\{", query, flags=re.IGNORECASE):
        open_index = query.find("{", match.start())
        close_index = _scan_matching_delimiter(query, open_index, "{", "}")
        if close_index is not None:
            ranges.append((match.start(), close_index + 1))
    return ranges


def _inside_ranges(index: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in ranges)


def _label_variable_used_as_constraint(
    query: str,
    label_variable: str,
    current_span: tuple[int, int],
) -> bool:
    masked_query = (
        query[: current_span[0]]
        + (" " * (current_span[1] - current_span[0]))
        + query[current_span[1]:]
    )
    escaped_variable = re.escape(label_variable)

    keyword_use_pattern = re.compile(
        rf"\b(?:FILTER|BIND|HAVING)\b(?:(?!\b(?:OPTIONAL|SELECT|WHERE|"
        rf"GROUP\s+BY|ORDER\s+BY|LIMIT|OFFSET)\b).)*{escaped_variable}\b",
        flags=re.IGNORECASE,
    )
    if keyword_use_pattern.search(masked_query):
        return True

    for triple_match in SIMPLE_TRIPLE_PATTERN.finditer(masked_query):
        if (
            triple_match.group("subject") == label_variable
            or triple_match.group("object") == label_variable
        ):
            return True

    return False


def wrap_output_label_triples(query: str) -> str:
    """Wrap unconstrained output/helper `rdfs:label` triples in OPTIONAL blocks."""
    optional_ranges = _optional_ranges(query)
    parts: list[str] = []
    cursor = 0

    for match in LABEL_TRIPLE_PATTERN.finditer(query):
        if _inside_ranges(match.start(), optional_ranges):
            continue

        if _label_variable_used_as_constraint(
            query,
            match.group("label"),
            match.span("triple"),
        ):
            continue

        parts.append(query[cursor: match.start("triple")])
        parts.append(f"OPTIONAL {{ {match.group('triple').strip()} }}")
        cursor = match.end("triple")

    if not parts:
        return query

    parts.append(query[cursor:])
    return "".join(parts)


def postprocess_pgmr_query(query: str) -> str:
    """Apply the PGMR cleanup steps used before restoration/execution."""
    fixed = strip_markdown_fences(query)
    fixed = normalize_spaces(fixed)

    # normalize_spaces can turn fenced markdown into one line:
    # ```sparql SELECT ... ```
    fixed = strip_markdown_fences(fixed)

    fixed = add_missing_where_braces(fixed)
    fixed = wrap_bare_optional_patterns(fixed)
    fixed = repair_malformed_filter_not_exists(fixed)
    fixed = normalize_malformed_regex_equality_filters(fixed)
    fixed = move_solution_modifiers_outside_where(fixed)
    fixed = wrap_output_label_triples(fixed)

    fixed = normalize_spaces(fixed)
    fixed = strip_markdown_fences(fixed)
    fixed = normalize_spaces(fixed)
    return fixed
