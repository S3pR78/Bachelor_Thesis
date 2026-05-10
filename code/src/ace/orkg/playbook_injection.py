from __future__ import annotations

from pathlib import Path
from typing import Any

from ace.playbook_utils import parse_playbook_line


def normalize_scope(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def infer_prediction_format_from_prompt_mode(
    *,
    prediction_format: str | None,
    prompt_mode: str | None,
    ace_mode: str | None = None,
) -> str:
    if prediction_format:
        return normalize_scope(prediction_format)

    if ace_mode and normalize_scope(ace_mode) not in {"any", ""}:
        mode = normalize_scope(ace_mode)
        if mode == "direct_sparql":
            return "sparql"
        return mode

    normalized_prompt = normalize_scope(prompt_mode)
    if "pgmr" in normalized_prompt:
        return "pgmr_lite"

    return "sparql"


def resolve_playbook_path(
    *,
    ace_playbook_path: str | None = None,
    ace_playbook_dir: str | None = None,
    model_key: str | None = None,
    family: str | None = None,
    prediction_format: str | None = None,
) -> Path | None:
    if ace_playbook_path:
        path = Path(ace_playbook_path)
        return path if path.exists() else None

    if not ace_playbook_dir or not model_key or not family or not prediction_format:
        return None

    path = Path(ace_playbook_dir) / model_key / f"{family}__{prediction_format}.txt"
    return path if path.exists() else None


def extract_playbook_rules(playbook_text: str, max_bullets: int) -> list[str]:
    rules: list[str] = []

    for line in playbook_text.splitlines():
        parsed = parse_playbook_line(line)
        if not parsed:
            continue

        content = str(parsed.get("content") or "").strip()
        if not content:
            continue

        rules.append(content)

        if max_bullets > 0 and len(rules) >= max_bullets:
            break

    return rules


def render_ace_context(playbook_path: Path, max_bullets: int) -> str:
    """Render ACE playbook rules as compact prompt context.

    max_bullets:
      0  -> disabled by caller
      >0 -> first N rules
      <0 -> all rules
    """
    text = playbook_path.read_text(encoding="utf-8")
    rules = extract_playbook_rules(text, max_bullets=max_bullets)

    if not rules:
        return ""

    lines = [
        "ACE PLAYBOOK RULES:",
        "Use the following family- and format-specific guidance when it is relevant.",
        "Do not force irrelevant rules.",
    ]

    for idx, rule in enumerate(rules, start=1):
        lines.append(f"{idx}. {rule}")

    return "\n".join(lines)


def insert_ace_context_near_generation_point(prompt: str, ace_context: str) -> str:
    """Insert ACE context close to the question/output marker when possible."""
    context = ace_context.strip()
    text = prompt.strip()

    if not context:
        return prompt

    if "ACE PLAYBOOK RULES:" in text:
        return prompt

    if "\nquestion:" in text:
        before, after = text.rsplit("\nquestion:", 1)
        return f"{before.rstrip()}\n\n{context}\n\nquestion:{after}"

    if "\n## Input" in text:
        before, after = text.rsplit("\n## Input", 1)
        return f"{before.rstrip()}\n\n{context}\n\n## Input{after}"

    return f"{context}\n\n{text}"


def append_ace_context_to_prompt(
    *,
    prompt: str,
    family: str | None,
    prompt_mode: str | None,
    model_key: str | None,
    prediction_format: str | None = None,
    ace_playbook_path: str | None = None,
    ace_playbook_dir: str | None = None,
    ace_mode: str | None = None,
    ace_max_bullets: int = 0,
) -> str:
    """Insert the matching ACE playbook into a prompt.

    This intentionally injects only the matching model/family/prediction_format
    playbook, not all playbooks.
    """
    if ace_max_bullets == 0:
        return prompt

    if not family and not ace_playbook_path:
        return prompt

    resolved_format = infer_prediction_format_from_prompt_mode(
        prediction_format=prediction_format,
        prompt_mode=prompt_mode,
        ace_mode=ace_mode,
    )

    playbook_path = resolve_playbook_path(
        ace_playbook_path=ace_playbook_path,
        ace_playbook_dir=ace_playbook_dir,
        model_key=model_key,
        family=family,
        prediction_format=resolved_format,
    )

    if not playbook_path:
        return prompt

    context = render_ace_context(playbook_path, max_bullets=ace_max_bullets).strip()
    if not context:
        return prompt

    return insert_ace_context_near_generation_point(prompt, context)
