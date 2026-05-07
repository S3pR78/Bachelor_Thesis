from __future__ import annotations

import json
from pathlib import Path

from src.ace.online.loop import OnlineAceConfig, OnlineAceReflectionInput
from src.ace.online.reflector import (
    OnlineAceReflector,
    OnlineReflectorConfig,
    build_online_reflection_prompt,
    is_concrete_online_rule,
    normalize_online_rule,
)


def _reflection_input(tmp_path: Path) -> OnlineAceReflectionInput:
    config = OnlineAceConfig(
        model="mock_generator",
        dataset=tmp_path / "dataset.json",
        prompt_mode="pgmr_mini",
        prediction_format="pgmr_lite",
        sparql_endpoint="https://example.invalid/sparql",
        initial_playbook=tmp_path / "missing.json",
        output_dir=tmp_path / "run",
        family="nlp4re",
        reflect_model="gpt_4o_mini",
    )
    return OnlineAceReflectionInput(
        config=config,
        item={
            "id": "item-1",
            "family": "nlp4re",
            "question": "Which papers are associated with annotation guidelines?",
            "gold_sparql": "SELECT ?paper WHERE { ?paper orkgp:P31 ?c . }",
        },
        iteration=0,
        generation={
            "raw_model_output": "SELECT ?paper WHERE { ?paper pgmr:foo ?x . }",
            "selected_prediction_query": "SELECT ?paper WHERE { ?paper pgmr:foo ?x . }",
        },
        evaluation={
            "query_extracted": True,
            "prediction_execution_success": True,
            "gold_execution_success": True,
            "answer_exact_match": False,
            "answer_f1": 0.0,
            "kg_ref_f1": 0.2,
            "predicate_ref_f1": 0.0,
            "error_category": "predicate_ref_mismatch",
        },
        context_rules=[
            {
                "id": "existing",
                "title": "Use contribution path",
                "content": "Connect paper to contribution first.",
                "category": "routing",
                "priority": 90,
                "enabled": True,
            }
        ],
    )


def test_build_online_reflection_prompt_is_compact_json(tmp_path: Path) -> None:
    prompt = build_online_reflection_prompt(_reflection_input(tmp_path))
    payload = json.loads(prompt)

    assert payload["run_context"]["family"] == "nlp4re"
    assert payload["failed_item"]["question"].startswith("Which papers")
    assert "current_context_rules" in payload
    assert "execution_results" not in payload
    assert payload["output_schema"]["source_item_id"] == "item-1"


def test_normalize_online_rule_fills_required_fields() -> None:
    rule = normalize_online_rule(
        {
            "category": "predicate_ref_mismatch",
            "title": "Use guideline availability path",
            "content": "For guideline questions, traverse annotation process to scheme.",
            "priority": 80,
        },
        family="nlp4re",
        mode="pgmr_lite",
        source_item_id="item-1",
        source_iteration=0,
    )

    assert rule["id"]
    assert rule["family"] == "nlp4re"
    assert rule["mode"] == "pgmr_lite"
    assert rule["source_item_id"] == "item-1"
    assert rule["source_iteration"] == 0
    assert rule["source"]["type"] == "online_llm_reflector"


def test_normalize_online_rule_backfills_missing_title_and_content() -> None:
    rule = normalize_online_rule(
        {
            "category": "predicate_ref_mismatch",
            "positive_pattern": "?contribution pgmr:nlp_data_type ?type .",
            "priority": 80,
        },
        family="nlp4re",
        mode="pgmr_lite",
        source_item_id="item-1",
        source_iteration=0,
    )

    assert rule["title"] == "Use concrete query pattern"
    assert rule["content"] == "?contribution pgmr:nlp_data_type ?type ."
    assert rule["id"]


def test_online_reflector_uses_injected_completion_without_openai_call(
    tmp_path: Path,
) -> None:
    calls: list[dict] = []

    def fake_completion(**kwargs) -> dict:
        calls.append(kwargs)
        return {
            "text": json.dumps(
                {
                    "id": "rule-annotation-guideline",
                    "family": "nlp4re",
                    "mode": "pgmr_lite",
                    "category": "predicate_ref_mismatch",
                    "title": "Use annotation scheme path",
                    "content": "For guideline questions, go through annotation process and scheme.",
                    "positive_pattern": "?annotationProcess pgmr:annotation_scheme ?annotationScheme .",
                    "avoid": "Do not attach guideline fields directly to the paper.",
                    "priority": 80,
                    "enabled": True,
                    "source_item_id": "item-1",
                    "source_iteration": 0,
                    "created_at_utc": "2026-01-01T00:00:00+00:00",
                }
            ),
            "usage": {
                "prompt_tokens": 123,
                "completion_tokens": 45,
                "total_tokens": 168,
            },
        }

    reflector = OnlineAceReflector(
        OnlineReflectorConfig(
            reflector_model="gpt_4o_mini",
            model_config_path=Path("code/config/model_config.json"),
        ),
        completion_fn=fake_completion,
    )

    result = reflector.reflect(_reflection_input(tmp_path))

    assert len(calls) == 1
    assert calls[0]["model_id"] == "gpt-4o-mini"
    assert calls[0]["temperature"] == 0.0
    assert result["rule"]["id"] == "rule-annotation-guideline"
    assert result["rule"]["source_item_id"] == "item-1"
    assert result["usage"] == {
        "prompt_tokens": 123,
        "completion_tokens": 45,
        "total_tokens": 168,
    }
    assert result["model"] == "gpt_4o_mini"


def test_is_concrete_online_rule_requires_pattern_or_aggregation() -> None:
    assert is_concrete_online_rule(
        {
            "title": "Use baseline path",
            "content": "Add ?evaluation pgmr:baseline ?baseline .",
        }
    )
    assert is_concrete_online_rule(
        {
            "title": "Count papers",
            "content": "Use COUNT(?paper) with GROUP BY ?type.",
        }
    )
    assert not is_concrete_online_rule(
        {
            "title": "Clarify baseline comparison requirements.",
            "content": "Ensure requirements are clearly defined.",
        }
    )


def test_online_reflector_regenerates_once_when_first_rule_is_vague(
    tmp_path: Path,
) -> None:
    calls: list[dict] = []

    def fake_completion(**kwargs) -> dict:
        calls.append(kwargs)
        if len(calls) == 1:
            return {
                "text": json.dumps(
                    {
                        "title": "Clarify baseline comparison requirements.",
                        "content": "Ensure the baseline requirements are clear.",
                        "category": "extraction",
                    }
                ),
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
        return {
            "text": json.dumps(
                {
                    "title": "Count papers by type",
                    "content": "For how-many questions, use COUNT(?paper) with GROUP BY ?type.",
                    "category": "extraction",
                }
            ),
            "usage": {"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18},
        }

    reflector = OnlineAceReflector(
        OnlineReflectorConfig(reflector_model="gpt_4o_mini"),
        completion_fn=fake_completion,
    )
    result = reflector.reflect(_reflection_input(tmp_path))

    assert len(calls) == 2
    assert result["rule"]["content"].startswith("For how-many questions")
    assert result["usage"] == {
        "prompt_tokens": 22,
        "completion_tokens": 11,
        "total_tokens": 33,
    }


def test_online_reflector_returns_fallback_rule_instead_of_raising_on_repeated_vague_output(
    tmp_path: Path,
) -> None:
    def fake_completion(**kwargs) -> dict:
        return {
            "text": json.dumps(
                {
                    "title": "Clarify requirements",
                    "content": "Ensure requirements are clear.",
                    "category": "extraction",
                }
            ),
            "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
        }

    reflector = OnlineAceReflector(
        OnlineReflectorConfig(reflector_model="gpt_4o_mini"),
        completion_fn=fake_completion,
    )
    result = reflector.reflect(_reflection_input(tmp_path))

    assert result.get("fallback_used") is True
    assert "rule" in result
    assert result["rule"]["title"]
    assert result["rule"]["content"]
