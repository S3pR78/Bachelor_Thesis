from __future__ import annotations

from src.ace.llm_reflector import (
    build_llm_reflection_prompt,
    extract_json_object,
    normalize_llm_delta_report,
)


def test_extract_json_object_from_fenced_response() -> None:
    response = """```json
{
  "schema_version": "ace_delta_v1",
  "deltas": []
}
```"""

    payload = extract_json_object(response)

    assert payload["schema_version"] == "ace_delta_v1"
    assert payload["deltas"] == []


def test_build_llm_reflection_prompt_contains_trace_context() -> None:
    trace_report = {
        "category_counts": {"pgmr_unmapped_placeholders": 2},
        "traces": [
            {
                "item_id": "1",
                "family": "nlp4re",
                "mode": "pgmr_lite",
                "question": "Which metrics are used?",
                "categories": ["pgmr_unmapped_placeholders"],
                "extracted_query": "SELECT ?m WHERE { ?x pgmr:unknown_metric ?m . }",
            }
        ],
    }

    prompt = build_llm_reflection_prompt(
        trace_report=trace_report,
        trace_path="ace_error_traces.json",
        family="nlp4re",
        mode="pgmr_lite",
        generator_model="t5_base_pgmr_mini_15ep",
        max_traces=5,
    )

    assert "ACE" in prompt
    assert "pgmr_unmapped_placeholders" in prompt
    assert "Which metrics are used?" in prompt
    assert "valid JSON" in prompt


def test_normalize_llm_delta_report_validates_and_adds_source() -> None:
    payload = {
        "schema_version": "ace_delta_v1",
        "deltas": [
            {
                "operation": "add",
                "reason": "The model invented placeholders.",
                "evidence": {"support_count": 1, "evidence_item_ids": ["1"]},
                "bullet": {
                    "family": "nlp4re",
                    "mode": "pgmr_lite",
                    "category": "pgmr_unmapped_placeholders",
                    "title": "Avoid invented PGMR tokens",
                    "content": "Use only PGMR tokens visible in the prompt or known core patterns.",
                    "priority": 90,
                    "avoid": "Do not invent pgmr:unknown_metric.",
                    "evidence_item_ids": ["1"],
                },
            }
        ],
    }

    report = normalize_llm_delta_report(
        payload=payload,
        family="nlp4re",
        mode="pgmr_lite",
        trace_path="ace_error_traces.json",
        reflector_model="gpt_4o_mini",
    )

    assert report["delta_count"] == 1
    bullet = report["deltas"][0]["bullet"]
    assert bullet["id"]
    assert bullet["source"]["type"] == "llm_ace_reflector"
    assert bullet["source"]["reflector_model"] == "gpt_4o_mini"
