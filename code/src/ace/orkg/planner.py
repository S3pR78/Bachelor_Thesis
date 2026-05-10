from __future__ import annotations

import json
from typing import Any

from ace.llm import timed_llm_call
from ace.playbook_utils import extract_json_from_text
from ace.orkg.context import domain_prompt_context


def build_planner_prompt(
    *,
    question: str,
    family: str,
    prediction_format: str,
) -> str:
    """Build a compact planning prompt for ORKG ACE rule retrieval.

    The planner must not see gold queries or gold answers. It only sees the
    question, family, prediction format, and domain memory context.
    """
    domain_context = domain_prompt_context(
        family=family,
        prediction_format=prediction_format,
        question=question,
    )

    return (
        "You are the ORKG ACE Query Planner.\n\n"
        "Your job is to create a compact, inference-time plan for selecting "
        "relevant ACE playbook rules before query generation.\n\n"
        "CRITICAL: Respond with valid JSON only. Do not use markdown or code blocks.\n\n"
        "You are NOT allowed to use gold queries, gold answers, reference outputs, "
        "or benchmark labels. Only use the question, family, prediction format, "
        "and domain context below.\n\n"
        "Scope:\n"
        f"- family: {family}\n"
        f"- prediction_format: {prediction_format}\n\n"
        "Domain context:\n"
        f"{domain_context}\n\n"
        "Planning requirements:\n"
        "- Identify the likely query form: SELECT, ASK, or COUNT.\n"
        "- Identify likely answer variables/entities.\n"
        "- Identify the required paper/contribution/template path.\n"
        "- Every relation placeholder/predicate that is needed to answer the question must appear in required_paths.\n"
        "- Do not stop at the contribution node when the question asks for a nested entity. Include the full parent path to the requested target.\n"
        "- If the domain context says a relation is nested under another entity, include the parent relation first.\n"
        "- For PGMR-lite, use pgmr:/pgmrc: placeholders only; do not use real ORKG IDs.\n"
        "- For Direct SPARQL, use ORKG predicates/classes/resources only; do not use pgmr:/pgmrc: placeholders.\n"
        "- For empirical_research_practice method questions, prefer the path contribution -> data_collection -> method -> method_type/method_name when relevant.\n"
        "- For empirical_research_practice threat/validity questions, prefer the path contribution -> threat_to_validity -> specific validity property when relevant.\n"
        "- For nlp4re annotation/guideline questions, prefer the path contribution -> annotation_process -> annotation_scheme -> guideline_availability.\n"
        "- For nlp4re task-combination questions, include both contribution -> re_task and contribution -> nlp_task.\n"
        "- For year/time questions, publication year is paper-level: ?paper pgmr:publication_year ?year or ?paper orkgp:P29 ?year.\n"
        "- Keep the plan compact and reusable.\n"
        "- Do not write a full query.\n\n"
        "Output JSON schema:\n"
        "{\n"
        '  "question_intent": "short description",\n'
        '  "expected_query_form": "SELECT | ASK | COUNT",\n'
        '  "answer_variables": ["?paper", "?paperLabel"],\n'
        '  "required_paths": ["short path or partial skeleton"],\n'
        '  "relevant_terms": ["term", "placeholder_or_predicate"],\n'
        '  "common_risks": ["risk to avoid"]\n'
        "}\n\n"
        "Question:\n"
        f"{question}"
    )


def parse_plan_response(response: str) -> dict[str, Any]:
    parsed = extract_json_from_text(response)
    if not isinstance(parsed, dict):
        raise ValueError("Planner response did not contain a JSON object.")

    # Normalize expected fields so downstream retrieval is robust.
    return {
        "question_intent": str(parsed.get("question_intent") or "").strip(),
        "expected_query_form": str(parsed.get("expected_query_form") or "").strip(),
        "answer_variables": _as_string_list(parsed.get("answer_variables")),
        "required_paths": _as_string_list(parsed.get("required_paths")),
        "relevant_terms": _as_string_list(parsed.get("relevant_terms")),
        "common_risks": _as_string_list(parsed.get("common_risks")),
    }


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def plan_question_with_llm(
    *,
    question: str,
    family: str,
    prediction_format: str,
    api_client: Any,
    api_provider: str,
    model: str,
    max_tokens: int,
    call_id: str,
    log_dir: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt = build_planner_prompt(
        question=question,
        family=family,
        prediction_format=prediction_format,
    )

    response, call_info = timed_llm_call(
        api_client,
        api_provider,
        model,
        prompt,
        role="planner",
        call_id=call_id,
        max_tokens=max_tokens,
        log_dir=log_dir,
        use_json_mode=True,
    )

    return parse_plan_response(response), call_info


def compact_plan_text(plan: dict[str, Any]) -> str:
    """Render a plan as text for debugging or prompt context."""
    return json.dumps(plan, ensure_ascii=False, indent=2)
