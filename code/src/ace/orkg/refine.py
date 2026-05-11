from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ace.llm import timed_llm_call
from ace.playbook_utils import extract_json_from_text, parse_playbook_line
from ace.orkg.adapter import compact_json
from ace.orkg.context import domain_prompt_context
from ace.orkg.safety import filter_safe_operations


PLAYBOOK_SECTIONS = (
    "## STRATEGIES & INSIGHTS",
    "",
    "## COMMON MISTAKES TO AVOID",
    "",
    "## OTHERS",
)


def extract_rules_from_playbook(playbook_text: str) -> list[dict[str, Any]]:
    """Extract existing playbook bullets into compact rule records."""
    rules: list[dict[str, Any]] = []
    current_section = "others"

    for line in playbook_text.splitlines():
        stripped = line.strip()

        if stripped.startswith("##"):
            current_section = stripped[2:].strip().lower().replace(" ", "_").replace("&", "and")
            continue

        parsed = parse_playbook_line(line)
        if not parsed:
            continue

        rules.append(
            {
                "id": parsed["id"],
                "section": current_section,
                "helpful": parsed["helpful"],
                "harmful": parsed["harmful"],
                "content": parsed["content"],
            }
        )

    return rules


def rule_to_operation(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "ADD",
        "section": rule.get("section") or "strategies_and_insights",
        "content": rule.get("content") or "",
    }


def deterministic_prefilter_rules(
    rules: list[dict[str, Any]],
    *,
    family: str,
    prediction_format: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply deterministic safety checks before LLM refine."""
    operations = [rule_to_operation(rule) for rule in rules]
    safe_operations, rejected_operations = filter_safe_operations(
        operations,
        family=family,
        prediction_format=prediction_format,
    )

    safe_contents = {op["content"] for op in safe_operations}
    safe_rules = [rule for rule in rules if rule.get("content") in safe_contents]

    return safe_rules, rejected_operations


def build_refine_prompt(
    *,
    family: str,
    prediction_format: str,
    playbook_text: str,
    rules: list[dict[str, Any]],
) -> str:
    context = domain_prompt_context(
        family=family,
        prediction_format=prediction_format,
        question=(
            "Refine the ACE playbook rules for this ORKG Text-to-SPARQL family and "
            "prediction format."
        ),
    )

    return (
        "You are the ORKG ACE Playbook Refiner.\n\n"
        "Your job is to refine one family- and prediction-format-specific ACE playbook.\n"
        "This is the REFINE step of ACE grow-and-refine: do not add new knowledge from outside the playbook; "
        "only clean, merge, rewrite, and compact the existing rules.\n\n"
        "CRITICAL: Respond with valid JSON only. Do not use markdown or code blocks.\n\n"
        "Scope:\n"
        f"- family: {family}\n"
        f"- prediction_format: {prediction_format}\n\n"
        "Domain context:\n"
        f"{context}\n\n"
        "Refinement goals:\n"
        "- Merge duplicate or strongly overlapping rules, but do not over-compress the playbook into vague advice.\n"
        "- Remove weak or generic rules that do not teach reusable ORKG structure.\n"
        "- Remove harmful, unsafe, or format-inconsistent rules.\n"
        "- Rewrite overly example-specific rules into reusable family-specific structural guidance while preserving the concrete template path when it is useful.\n"
        "- Keep useful concrete structure: answer variables, projection behavior, join paths, placeholders, ORKG predicates/classes, and required intermediate nodes.\n"
        "- Preserve concrete placeholder chains or ORKG paths when they are correct; do not replace them with vague phrases such as 'connect necessary variables' or 'use correct mappings'.\n"
        "- Prefer fewer high-quality rules over many repetitive rules, but keep enough rules to cover distinct template areas.\n"
        "- Do not copy full example queries.\n"
        "- Do not mention gold query, reference query, gold answer, expected answer, or hidden labels.\n\n"
        "Format constraints:\n"
        "- For PGMR-lite playbooks, final rules must use pgmr:/pgmrc: placeholder language only.\n"
        "- For PGMR-lite playbooks, do not mention ORKG URIs, ORKG IDs, ORKG predicates, ORKG classes, ORKG resources, or identifiers such as orkgp:/orkgc:/orkgr:.\n"
        "- For PGMR-lite playbooks, say 'use allowed family placeholders' or name concrete pgmr:/pgmrc: placeholders. Do not tell the model to output ORKG identifiers.\n"
        "- For Direct-SPARQL playbooks, final rules may use ORKG identifiers such as orkgp:/orkgc:/orkgr:, but must not contain pgmr:/pgmrc: placeholders.\n"
        "- If a concrete path is uncertain, use safer wording such as 'the family-valid path to ...' instead of inventing a path.\n\n"
        "Quality constraints:\n"
        "- Do not turn specific useful rules into generic rules.\n"
        "- Do not copy the original natural-language question verbatim into the final rule. Generalize it into a reusable question pattern.\n"
        "- Avoid final rules that only say 'use correct placeholders', 'include necessary nodes', 'apply filters', or 'map correctly' unless they also name the concrete answer role or path.\n"
        "- Keep separate rules for clearly different template areas, such as research questions, data collection, data analysis/statistics, threats to validity, NLP tasks, datasets, annotation, evaluation, and implemented approaches.\n"
        "- Preserve correct concrete paths, but rewrite wrong or uncertain paths into safer family-valid wording.\n"
        "- For PGMR-lite, publication year is paper-level. Use `?paper pgmr:publication_year ?year .`; never describe publication year as coming from `?contribution`.\n"
        "- For Direct SPARQL, publication year is paper-level. Use `?paper orkgp:P29 ?year .`; never describe publication year as coming from `?contribution`.\n"
        "- For empirical_research_practice PGMR-lite data-collection-method questions, prefer the path pattern: `?contribution pgmr:data_collection ?dataCollection . ?dataCollection pgmr:method ?method .` and then bind method attributes such as `pgmr:method_type` or `pgmr:method_name` when relevant.\n"
        "- For nlp4re PGMR-lite annotation/guideline questions, prefer the path pattern: `?contribution pgmr:annotation_process ?annotationProcess . ?annotationProcess pgmr:annotation_scheme ?annotationScheme .` and then bind guideline-related attributes when relevant.\n"
        "- A good refined rule should usually have the shape: WHEN this question pattern appears, DO this concrete path/projection action, AVOID this concrete mistake.\n\n"
        "Output JSON schema:\n"
        "{\n"
        '  "rules": [\n'
        "    {\n"
        '      "section": "strategies_and_insights",\n'
        '      "content": "WHEN ... DO ... AVOID ..."\n'
        "    }\n"
        "  ],\n"
        '  "removed_reasons": [\n'
        "    {\n"
        '      "content_preview": "short preview of removed or merged rule",\n'
        '      "reason": "duplicate | generic | unsafe | merged | too_specific | harmful | format_mismatch"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Current playbook text:\n"
        f"{playbook_text}\n\n"
        "Parsed current rules:\n"
        f"{compact_json(rules)}"
    )


def cleaned_playbook_from_rules(rules: list[dict[str, Any]]) -> str:
    """Render a cleaned playbook from refined rules with fresh IDs."""
    by_section: dict[str, list[str]] = {
        "strategies_and_insights": [],
        "common_mistakes_to_avoid": [],
        "others": [],
    }

    for rule in rules:
        section = str(rule.get("section") or "strategies_and_insights").lower()
        section = section.replace(" ", "_").replace("&", "and")
        if section not in by_section:
            section = "strategies_and_insights"
        content = str(rule.get("content") or "").strip()
        if content:
            by_section[section].append(content)

    lines: list[str] = ["## STRATEGIES & INSIGHTS", ""]
    for idx, content in enumerate(by_section["strategies_and_insights"], start=1):
        lines.append(f"[sai-{idx:05d}] helpful=0 harmful=0 :: {content}")

    lines.extend(["## COMMON MISTAKES TO AVOID", ""])
    for idx, content in enumerate(by_section["common_mistakes_to_avoid"], start=1):
        lines.append(f"[err-{idx:05d}] helpful=0 harmful=0 :: {content}")

    lines.extend(["## OTHERS", ""])
    for idx, content in enumerate(by_section["others"], start=1):
        lines.append(f"[oth-{idx:05d}] helpful=0 harmful=0 :: {content}")

    return "\n".join(lines).rstrip() + "\n"


def parse_refiner_response(response: str) -> dict[str, Any]:
    parsed = extract_json_from_text(response)
    if not isinstance(parsed, dict):
        raise ValueError("Refiner response did not contain a JSON object.")

    if "rules" not in parsed or not isinstance(parsed["rules"], list):
        raise ValueError("Refiner JSON missing list field 'rules'.")

    if "removed_reasons" not in parsed:
        parsed["removed_reasons"] = []

    return parsed


def refine_playbook_with_llm(
    *,
    playbook_text: str,
    family: str,
    prediction_format: str,
    api_client: Any,
    api_provider: str,
    model: str,
    max_tokens: int,
    call_id: str,
    log_dir: str | None = None,
) -> dict[str, Any]:
    """Run LLM-based playbook refinement and deterministic post-safety."""
    original_rules = extract_rules_from_playbook(playbook_text)
    prefiltered_rules, pre_rejections = deterministic_prefilter_rules(
        original_rules,
        family=family,
        prediction_format=prediction_format,
    )

    prompt = build_refine_prompt(
        family=family,
        prediction_format=prediction_format,
        playbook_text=playbook_text,
        rules=prefiltered_rules,
    )

    response, call_info = timed_llm_call(
        api_client,
        api_provider,
        model,
        prompt,
        role="playbook_refiner",
        call_id=call_id,
        max_tokens=max_tokens,
        log_dir=log_dir,
        use_json_mode=True,
    )

    parsed = parse_refiner_response(response)
    candidate_rules = parsed["rules"]

    operations = []
    for rule in candidate_rules:
        if not isinstance(rule, dict):
            continue
        operations.append(
            {
                "type": "ADD",
                "section": rule.get("section", "strategies_and_insights"),
                "content": rule.get("content", ""),
            }
        )

    safe_operations, post_rejections = filter_safe_operations(
        operations,
        family=family,
        prediction_format=prediction_format,
    )

    safe_rules = [
        {
            "section": op.get("section", "strategies_and_insights"),
            "content": op.get("content", ""),
        }
        for op in safe_operations
    ]

    cleaned_playbook = cleaned_playbook_from_rules(safe_rules)

    return {
        "family": family,
        "prediction_format": prediction_format,
        "original_rule_count": len(original_rules),
        "prefiltered_rule_count": len(prefiltered_rules),
        "refined_rule_count": len(safe_rules),
        "pre_rejections": pre_rejections,
        "post_rejections": post_rejections,
        "removed_reasons": parsed.get("removed_reasons", []),
        "raw_response": response,
        "call_info": call_info,
        "cleaned_playbook": cleaned_playbook,
    }
