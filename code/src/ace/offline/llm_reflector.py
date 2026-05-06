"""Ask an LLM to propose ACE playbook deltas from error traces."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.ace.playbook import AceDelta
from src.core.openai_provider import generate_raw_response_openai
from src.utils.config_loader import get_model_entry, load_json_config


LLM_DELTA_SCHEMA_VERSION = "ace_delta_v1"

ALLOWED_LLM_CATEGORIES = {
    "output_format",
    "pgmr_format",
    "pgmr_allowed_vocabulary",
    "pgmr_unmapped_placeholders",
    "pgmr_restore_error",
    "contribution_pattern",
    "missing_contribution_pattern",
    "query_form_mismatch",
    "answer_mismatch",
    "predicate_ref_mismatch",
    "class_ref_mismatch",
    "resource_ref_mismatch",
    "venue_filter",
    "missing_venue_filter",
    "execution_error",
    "endpoint_bad_request",
    "family_structure",
}


def load_trace_report(path: str | Path) -> dict[str, Any]:
    """Load an ACE trace report produced from evaluation errors."""
    trace_path = Path(path)
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ACE trace report must be a JSON object.")
    return payload


def compact_trace(trace: dict[str, Any], *, max_text_chars: int = 900) -> dict[str, Any]:
    """Keep only the fields an LLM reflector needs.

    This avoids sending full raw outputs or huge queries when a short error
    summary is enough to derive a playbook rule.
    """

    def shorten(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if len(text) <= max_text_chars:
            return text
        return text[:max_text_chars].rstrip() + " ..."

    return {
        "item_id": trace.get("item_id"),
        "family": trace.get("family"),
        "mode": trace.get("mode"),
        "split": trace.get("split"),
        "question": shorten(trace.get("question")),
        "categories": trace.get("categories", []),
        "metrics": trace.get("metrics", {}),
        "raw_model_output": shorten(trace.get("raw_model_output")),
        "extracted_query": shorten(trace.get("extracted_query")),
        "restored_query": shorten(trace.get("restored_query")),
        "gold_sparql": shorten(trace.get("gold_sparql")),
        "error_text": shorten(trace.get("error_text")),
    }


def select_error_traces(
    trace_report: dict[str, Any],
    *,
    family: str | None,
    mode: str | None,
    max_traces: int,
) -> list[dict[str, Any]]:
    """Select the highest-signal error traces for one family/mode."""
    traces = []

    for trace in trace_report.get("traces", []):
        if family and trace.get("family") != family:
            continue
        if mode and trace.get("mode") not in {mode, None, ""}:
            continue
        if not trace.get("categories"):
            continue
        traces.append(trace)

    # Prioritize traces with many categories because they contain richer failure signals.
    traces.sort(
        key=lambda item: (
            -len(item.get("categories", [])),
            str(item.get("item_id", "")),
        )
    )

    return traces[:max_traces]


def build_llm_reflection_prompt(
    *,
    trace_report: dict[str, Any],
    trace_path: str,
    family: str,
    mode: str,
    generator_model: str | None,
    max_traces: int = 12,
) -> str:
    """Build the reflection prompt sent to the LLM."""
    traces = select_error_traces(
        trace_report,
        family=family,
        mode=mode,
        max_traces=max_traces,
    )
    compact_traces = [compact_trace(trace) for trace in traces]

    category_counts = trace_report.get("category_counts", {})

    return f"""
You are the Reflector in an Agentic Context Engineering (ACE) system for Text-to-SPARQL over ORKG templates.

Task:
Analyze development-set error traces from a generator model and produce candidate ACE playbook delta rules.

Important constraints:
- Use only the provided traces.
- Do not use or mention test/benchmark data.
- Do not invent ORKG predicates, classes, or PGMR placeholders.
- Prefer short, actionable rules that can be prepended to a prompt.
- The final model output must remain only SPARQL or PGMR-lite, not reasoning.
- Produce only valid JSON. No markdown. No commentary.

Context:
- Template family: {family}
- Mode: {mode}
- Generator model: {generator_model or "unknown"}
- Source trace file: {trace_path}

Observed category counts:
{json.dumps(category_counts, indent=2, ensure_ascii=False)}

Allowed categories for rules:
{json.dumps(sorted(ALLOWED_LLM_CATEGORIES), indent=2, ensure_ascii=False)}

Input traces:
{json.dumps(compact_traces, indent=2, ensure_ascii=False)}

Output JSON schema:
{{
  "schema_version": "ace_delta_v1",
  "deltas": [
    {{
      "operation": "add",
      "reason": "Short explanation based only on the traces.",
      "evidence": {{
        "support_count": 1,
        "evidence_item_ids": ["..."]
      }},
      "bullet": {{
        "family": "{family}",
        "mode": "{mode}",
        "category": "one_allowed_category",
        "title": "Short imperative title",
        "content": "One concise rule. Must be directly useful in a prompt.",
        "bullet_type": "llm_validation_lesson",
        "priority": 50,
        "enabled": true,
        "positive_pattern": null,
        "avoid": "Short anti-pattern to avoid.",
        "applicability": [],
        "source": {{
          "type": "llm_ace_reflector",
          "trace_path": "{trace_path}"
        }},
        "evidence_item_ids": ["..."],
        "helpful_count": 0,
        "harmful_count": 0
      }}
    }}
  ]
}}

Rules:
- Generate at most 6 deltas.
- Prefer specific rules over generic ones.
- If several traces show the same failure, create one consolidated rule.
- For T5-style small models, keep rules especially short.
- If a positive PGMR/SPARQL pattern is obvious from the traces, include it in positive_pattern.
- If no useful rule can be derived, return an empty deltas list.
""".strip()


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from an LLM response.

    The LLM is instructed to return JSON only, but this makes the tool robust
    against accidental ```json fences or short surrounding text.
    """
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"```$", "", cleaned.strip())

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(cleaned[start : end + 1])

    if not isinstance(payload, dict):
        raise ValueError("LLM reflector response must be a JSON object.")

    return payload


def normalize_llm_delta_report(
    *,
    payload: dict[str, Any],
    family: str,
    mode: str,
    trace_path: str,
    reflector_model: str,
) -> dict[str, Any]:
    deltas_payload = payload.get("deltas", [])
    if not isinstance(deltas_payload, list):
        raise ValueError("LLM delta report must contain a list field 'deltas'.")

    normalized_deltas: list[dict[str, Any]] = []

    for delta_payload in deltas_payload:
        if not isinstance(delta_payload, dict):
            continue

        bullet = delta_payload.get("bullet")
        if not isinstance(bullet, dict):
            continue

        bullet["family"] = str(bullet.get("family") or family)
        bullet["mode"] = str(bullet.get("mode") or mode)
        bullet["category"] = str(bullet.get("category") or "answer_mismatch")

        if bullet["category"] not in ALLOWED_LLM_CATEGORIES:
            bullet["category"] = "answer_mismatch"

        bullet["bullet_type"] = str(
            bullet.get("bullet_type") or "llm_validation_lesson"
        )
        bullet["enabled"] = bool(bullet.get("enabled", True))
        bullet["priority"] = int(bullet.get("priority", 70))
        bullet["applicability"] = list(bullet.get("applicability", []))
        bullet["evidence_item_ids"] = list(bullet.get("evidence_item_ids", []))
        bullet["helpful_count"] = int(bullet.get("helpful_count", 0))
        bullet["harmful_count"] = int(bullet.get("harmful_count", 0))

        source = dict(bullet.get("source", {}))
        source.update(
            {
                "type": "llm_ace_reflector",
                "trace_path": trace_path,
                "reflector_model": reflector_model,
            }
        )
        bullet["source"] = source

        if not str(bullet.get("title", "")).strip():
            continue
        if not str(bullet.get("content", "")).strip():
            continue

        normalized_delta = {
            "operation": str(delta_payload.get("operation") or "add"),
            "reason": str(delta_payload.get("reason") or "LLM-derived ACE rule."),
            "evidence": dict(delta_payload.get("evidence", {})),
            "bullet": bullet,
        }

        # Validate using the existing AceDelta parser. This also creates a stable ID
        # if the LLM did not provide one.
        parsed_delta = AceDelta.from_dict(normalized_delta)
        normalized_deltas.append(parsed_delta.to_dict())

    return {
        "schema_version": LLM_DELTA_SCHEMA_VERSION,
        "source_trace_path": trace_path,
        "reflector_model": reflector_model,
        "family": family,
        "mode": mode,
        "delta_count": len(normalized_deltas),
        "deltas": normalized_deltas,
    }


def run_llm_reflector(
    *,
    traces_path: str | Path,
    reflector_model: str,
    family: str,
    mode: str,
    generator_model: str | None = None,
    model_config_path: str | Path = "code/config/model_config.json",
    max_traces: int = 12,
    max_output_tokens: int | None = None,
    temperature: float | None = None,
    save_prompt_path: str | Path | None = None,
) -> dict[str, Any]:
    trace_report = load_trace_report(traces_path)
    trace_path = str(traces_path)

    prompt = build_llm_reflection_prompt(
        trace_report=trace_report,
        trace_path=trace_path,
        family=family,
        mode=mode,
        generator_model=generator_model,
        max_traces=max_traces,
    )

    if save_prompt_path:
        Path(save_prompt_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_prompt_path).write_text(prompt, encoding="utf-8")

    full_config = load_json_config(model_config_path)
    model_entry = get_model_entry(full_config, reflector_model)

    provider = str(model_entry.get("provider", "")).lower()
    if provider != "openai":
        raise ValueError(
            "LLM-assisted ACE reflector currently expects an OpenAI model config entry."
        )

    generation = model_entry.get("generation", {})
    api = model_entry.get("api", {})

    response = generate_raw_response_openai(
        model_id=model_entry.get("model_id"),
        prompt=prompt,
        max_output_tokens=max_output_tokens
        or generation.get("max_output_tokens", 2048),
        temperature=temperature
        if temperature is not None
        else generation.get("temperature", 0.0),
        developer_message=(
            "You are an ACE Reflector for ORKG Text-to-SPARQL. "
            "Return only valid JSON that matches the requested schema."
        ),
        env_var_name=api.get("api_key_env") or api.get("env_var_name", "OPENAI_API_KEY"),
    )

    raw_payload = extract_json_object(response)

    return normalize_llm_delta_report(
        payload=raw_payload,
        family=family,
        mode=mode,
        trace_path=trace_path,
        reflector_model=reflector_model,
    )


def save_llm_delta_report(report: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
