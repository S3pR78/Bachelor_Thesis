from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ace.playbook_utils import parse_playbook_line


TOKEN_RE = re.compile(r"[a-zA-Z0-9_:/?]+")


def tokenize(text: str) -> set[str]:
    raw_tokens = TOKEN_RE.findall(text.lower())
    tokens: set[str] = set()

    for token in raw_tokens:
        token = token.strip("`'\".,;()[]{}")
        if len(token) < 2:
            continue
        tokens.add(token)

        # Split placeholder/predicate-style tokens into useful parts.
        for part in re.split(r"[:/_\-]+", token):
            if len(part) >= 2:
                tokens.add(part)

    return tokens


def load_playbook_rules(playbook_path: Path) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    current_section = "others"

    if not playbook_path.exists():
        return rules

    for line in playbook_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if stripped.startswith("##"):
            current_section = stripped[2:].strip().lower().replace(" ", "_").replace("&", "and")
            continue

        parsed = parse_playbook_line(line)
        if not parsed:
            continue

        content = str(parsed.get("content") or "").strip()
        if not content:
            continue

        rules.append(
            {
                "id": parsed["id"],
                "section": current_section,
                "helpful": parsed["helpful"],
                "harmful": parsed["harmful"],
                "content": content,
            }
        )

    return rules


def plan_terms(plan: dict[str, Any]) -> set[str]:
    pieces: list[str] = []

    for key in (
        "question_intent",
        "expected_query_form",
    ):
        value = plan.get(key)
        if value:
            pieces.append(str(value))

    for key in (
        "answer_variables",
        "required_paths",
        "relevant_terms",
        "common_risks",
    ):
        value = plan.get(key)
        if isinstance(value, list):
            pieces.extend(str(item) for item in value)
        elif value:
            pieces.append(str(value))

    return tokenize(" ".join(pieces))


def score_rule(
    rule: dict[str, Any],
    *,
    question_tokens: set[str],
    plan_token_set: set[str],
) -> float:
    content = str(rule.get("content") or "")
    rule_tokens = tokenize(content)

    if not rule_tokens:
        return 0.0

    question_overlap = len(rule_tokens & question_tokens)
    plan_overlap = len(rule_tokens & plan_token_set)

    helpful = int(rule.get("helpful") or 0)
    harmful = int(rule.get("harmful") or 0)

    # Weights are intentionally simple and deterministic.
    score = 1.0 * question_overlap + 2.0 * plan_overlap
    score += min(helpful, 5) * 0.5
    score -= min(harmful, 5) * 1.0

    # Prefer concrete structural rules.
    concrete_markers = (
        "pgmr:",
        "pgmrc:",
        "orkgp:",
        "orkgc:",
        "?paper",
        "?contribution",
        "select",
        "ask",
        "count",
        "filter",
        "optional",
    )
    if any(marker in content.lower() for marker in concrete_markers):
        score += 1.0

    return score


def select_top_k_rules(
    *,
    question: str,
    plan: dict[str, Any],
    rules: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    if top_k <= 0:
        return []

    question_tokens = tokenize(question)
    plan_token_set = plan_terms(plan)

    scored = [
        (
            score_rule(
                rule,
                question_tokens=question_tokens,
                plan_token_set=plan_token_set,
            ),
            idx,
            rule,
        )
        for idx, rule in enumerate(rules)
    ]

    # Keep deterministic ordering for ties.
    ranked = sorted(scored, key=lambda item: (-item[0], item[1]))

    selected = [
        {
            **rule,
            "retrieval_score": score,
        }
        for score, _idx, rule in ranked
        if score > 0
    ]

    return selected[:top_k]


def render_rules_as_playbook(rules: list[dict[str, Any]]) -> str:
    """Render selected rules as a temporary ACE playbook."""
    lines: list[str] = ["## STRATEGIES & INSIGHTS", ""]

    for idx, rule in enumerate(rules, start=1):
        content = str(rule.get("content") or "").strip()
        if content:
            lines.append(f"[sai-{idx:05d}] helpful=0 harmful=0 :: {content}")

    lines.extend(["## COMMON MISTAKES TO AVOID", "", "## OTHERS", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_selected_rules_block(rules: list[dict[str, Any]]) -> str:
    lines = ["SELECTED ACE RULES:"]
    for idx, rule in enumerate(rules, start=1):
        lines.append(f"{idx}. {rule.get('content')}")
    return "\n".join(lines)


def render_plan_as_rule(
    *,
    plan: dict[str, Any],
    family: str,
    prediction_format: str,
) -> dict[str, Any]:
    """Render a planner output as one temporary playbook rule."""
    expected_form = str(plan.get("expected_query_form") or "").strip()
    answer_variables = plan.get("answer_variables") or []
    required_paths = plan.get("required_paths") or []
    relevant_terms = plan.get("relevant_terms") or []
    common_risks = plan.get("common_risks") or []

    pieces: list[str] = [
        f"ACE QUERY PLAN for family={family}, prediction_format={prediction_format}:"
    ]

    if expected_form:
        pieces.append(f"expected query form = {expected_form}")

    if answer_variables:
        pieces.append("answer variables/entities = " + ", ".join(map(str, answer_variables)))

    if required_paths:
        pieces.append("required path hints = " + " | ".join(map(str, required_paths)))

    if relevant_terms:
        pieces.append("relevant terms/placeholders/predicates = " + ", ".join(map(str, relevant_terms)))

    if common_risks:
        pieces.append("avoid = " + "; ".join(map(str, common_risks)))

    return {
        "id": "plan-00001",
        "section": "strategies_and_insights",
        "helpful": 0,
        "harmful": 0,
        "content": " ".join(pieces),
        "source": "planner",
    }


def build_temporary_playbook_from_plan_and_rules(
    *,
    plan: dict[str, Any],
    selected_rules: list[dict[str, Any]],
    family: str,
    prediction_format: str,
    extra_rules: list[dict[str, Any]] | None = None,
) -> str:
    """Build a temporary playbook for one item.

    It contains:
    1. the planner's query plan as a rule
    2. top-k retrieved rules from the frozen/current playbook
    3. optional temporary repair rules for later attempts
    """
    rules: list[dict[str, Any]] = [
        render_plan_as_rule(
            plan=plan,
            family=family,
            prediction_format=prediction_format,
        )
    ]

    rules.extend(selected_rules)

    if extra_rules:
        rules.extend(extra_rules)

    return render_rules_as_playbook(rules)
