from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, T5Tokenizer

from src.core.model_loader import get_model_dir
from src.utils.config_loader import get_model_entry, load_json_config
from string import Formatter


PGMR_TOKEN_PATTERN = re.compile(r"\b(?:pgmr|pgmrc):[A-Za-z_][A-Za-z0-9_]*\b")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def format_prompt_value(value: Any) -> str:
    if value is None:
        return "none"

    if isinstance(value, list):
        values = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(values) if values else "none"

    if isinstance(value, dict):
        values = [
            f"{key}={val}"
            for key, val in value.items()
            if str(key).strip() and str(val).strip()
        ]
        return ", ".join(values) if values else "none"

    text = str(value).strip()
    return text if text else "none"


def build_prompt(entry: dict[str, Any], prompt_template: str) -> str:
    format_values: dict[str, str] = {}

    for _, field_name, _, _ in Formatter().parse(prompt_template):
        if not field_name:
            continue

        value = entry.get(field_name)

        if field_name in {"family", "question"} and (value is None or not str(value).strip()):
            raise ValueError(f"Missing required prompt field '{field_name}' for id={entry.get('id')}")

        format_values[field_name] = format_prompt_value(value)

    return prompt_template.format(**format_values)

def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


SOLUTION_MODIFIER_PATTERN = re.compile(
    r"\b(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|OFFSET)\b",
    flags=re.IGNORECASE,
)


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
    """
    Fix bare OPTIONAL triple patterns:
      OPTIONAL ?x rdfs:label ?label .
      OPTIONAL ?x rdfs:label ?label }
    into:
      OPTIONAL { ?x rdfs:label ?label . }

    This intentionally targets simple one-triple OPTIONAL patterns.
    """
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
    fixed = normalize_spaces(query)
    fixed = add_missing_where_braces(fixed)
    fixed = wrap_bare_optional_patterns(fixed)
    fixed = move_solution_modifiers_outside_where(fixed)
    fixed = normalize_spaces(fixed)
    return fixed

def has_balanced_braces(query: str) -> bool:
    return query.count("{") == query.count("}")


def classify_output(raw: str, postprocessed: str) -> dict[str, Any]:
    raw_norm = normalize_spaces(raw)
    post_norm = normalize_spaces(postprocessed)

    starts_with_query_type = bool(re.match(r"^(SELECT|ASK)\b", raw_norm, flags=re.IGNORECASE))
    has_where = bool(re.search(r"\bWHERE\b", raw_norm, flags=re.IGNORECASE))
    has_where_block_raw = bool(re.search(r"\bWHERE\s*\{", raw_norm, flags=re.IGNORECASE))
    has_where_block_post = bool(re.search(r"\bWHERE\s*\{", post_norm, flags=re.IGNORECASE))
    balanced_post = has_balanced_braces(post_norm)

    bad_fragments = []
    for fragment in ["phmrc:", "pgmrc:nlp4re_consensus", "FILTER(STREAM)", ".n?", "[REEL]", "[TRACE]"]:
        if fragment in raw_norm:
            bad_fragments.append(fragment)

    pgmr_tokens = sorted(set(PGMR_TOKEN_PATTERN.findall(raw_norm)))

    usable_after_postprocess = (
        starts_with_query_type
        and has_where
        and has_where_block_post
        and balanced_post
        and not bad_fragments
    )

    return {
        "starts_with_query_type": starts_with_query_type,
        "has_where": has_where,
        "has_where_block_raw": has_where_block_raw,
        "has_where_block_post": has_where_block_post,
        "balanced_braces_post": balanced_post,
        "usable_after_postprocess": usable_after_postprocess,
        "bad_fragments": bad_fragments,
        "pgmr_tokens": pgmr_tokens,
    }


def generate(
    model,
    tokenizer,
    prompt: str,
    device: str,
    max_source_length: int,
    max_new_tokens: int,
    num_beams: int,
) -> str:
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=max_source_length,
    )

    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            num_beams=num_beams,
            do_sample=False,
        )

    return tokenizer.decode(output_ids[0], skip_special_tokens=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate PGMR model outputs on a dataset split.")
    parser.add_argument("--model", required=True, help="Model key from model_config.json.")
    parser.add_argument("--dataset", type=Path, required=True, help="Dataset JSON file.")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON report.")
    parser.add_argument("--model-config", type=Path, default=Path("code/config/model_config.json"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-source-length", type=int, default=192)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--num-beams", type=int, default=4)
    parser.add_argument(
        "--prompt-template",
        default="task: text_to_pgmr_sparql\nfamily: {family}\nquestion: {question}\npgmr_sparql:",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    data = load_json(args.dataset)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON list.")

    selected = data[: args.limit] if args.limit is not None else data

    config = load_json_config(args.model_config)
    model_config = get_model_entry(config, args.model)
    model_dir = get_model_dir(model_config)

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, use_fast=False)
    except Exception:
        tokenizer = T5Tokenizer.from_pretrained(model_dir, local_files_only=True)

    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir, local_files_only=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    model.eval()

    results = []

    counters = {
        "total": 0,
        "starts_with_query_type": 0,
        "has_where": 0,
        "has_where_block_raw": 0,
        "has_where_block_post": 0,
        "balanced_braces_post": 0,
        "usable_after_postprocess": 0,
    }

    for index, entry in enumerate(selected):
        prompt = build_prompt(entry, args.prompt_template)
        raw = generate(
            model=model,
            tokenizer=tokenizer,
            prompt=prompt,
            device=device,
            max_source_length=args.max_source_length,
            max_new_tokens=args.max_new_tokens,
            num_beams=args.num_beams,
        )
        postprocessed = postprocess_pgmr_query(raw)
        checks = classify_output(raw, postprocessed)

        counters["total"] += 1
        for key in counters:
            if key == "total":
                continue
            if checks.get(key):
                counters[key] += 1

        results.append(
            {
                "index": index,
                "id": entry.get("id"),
                "family": entry.get("family"),
                "question": entry.get("question"),
                "gold_pgmr_sparql": entry.get("gold_pgmr_sparql"),
                "prompt": prompt,
                "raw_prediction": raw,
                "postprocessed_prediction": postprocessed,
                "checks": checks,
            }
        )

        print(f"[{index + 1}/{len(selected)}] id={entry.get('id')} usable={checks['usable_after_postprocess']}")

    summary = {
        "model": args.model,
        "dataset": str(args.dataset),
        "model_dir": str(model_dir),
        "device": device,
        "limit": args.limit,
        "generation": {
            "max_source_length": args.max_source_length,
            "max_new_tokens": args.max_new_tokens,
            "num_beams": args.num_beams,
            "do_sample": False,
        },
        "counts": counters,
        "rates": {
            key: (value / counters["total"] if counters["total"] else 0)
            for key, value in counters.items()
            if key != "total"
        },
    }

    report = {
        "summary": summary,
        "results": results,
    }

    save_json(args.output, report)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
