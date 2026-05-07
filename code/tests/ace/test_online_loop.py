from __future__ import annotations

import json
from pathlib import Path

from src.ace.online.loop import (
    OnlineAceConfig,
    OnlineAceEvaluationInput,
    OnlineAceGenerationInput,
    OnlineAceHooks,
    OnlineAceReflectionInput,
    compute_quality_score,
    compute_quality_score_with_metric,
    run_online_ace_loop,
)


def _write_dataset(path: Path, items: list[dict] | None = None) -> None:
    path.write_text(
        json.dumps(
            items
            or [
                {
                    "id": "1",
                    "family": "nlp4re",
                    "question": "Which papers use guidelines?",
                    "gold_sparql": "SELECT ?paper WHERE {}",
                }
            ]
        ),
        encoding="utf-8",
    )


def _config(tmp_path: Path, *, iterations: int = 3) -> OnlineAceConfig:
    dataset_path = tmp_path / "dataset.json"
    _write_dataset(dataset_path)
    return OnlineAceConfig(
        model="mock_model",
        dataset=dataset_path,
        prompt_mode="pgmr_mini",
        prediction_format="pgmr_lite",
        sparql_endpoint="https://example.invalid/sparql",
        initial_playbook=tmp_path / "missing_initial_playbook.json",
        output_dir=tmp_path / "run",
        family="nlp4re",
        iterations=iterations,
        reflect_model="mock_reflector",
    )


def _generation(_: OnlineAceGenerationInput) -> dict:
    return {
        "raw_model_output": "SELECT ?paper WHERE {}",
        "extracted_query": "SELECT ?paper WHERE {}",
        "selected_prediction_query": "SELECT ?paper WHERE {}",
    }


def _failed_eval(_: OnlineAceEvaluationInput) -> dict:
    return {
        "query_extracted": True,
        "prediction_execution_success": True,
        "gold_execution_success": True,
        "answer_exact_match": False,
        "answer_f1": 0.0,
        "kg_ref_f1": 0.0,
        "predicate_ref_f1": 0.0,
        "error_category": "answer_mismatch",
    }


def _solved_eval(_: OnlineAceEvaluationInput) -> dict:
    return {
        "query_extracted": True,
        "prediction_execution_success": True,
        "gold_execution_success": True,
        "answer_exact_match": True,
        "answer_f1": 1.0,
        "kg_ref_f1": 1.0,
        "predicate_ref_f1": 1.0,
    }


def _reflection(_: OnlineAceReflectionInput) -> dict:
    return {
        "rule": {
            "id": "rule-1",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "routing",
            "title": "Use contribution path",
            "content": "Connect papers to contributions before template fields.",
            "priority": 80,
            "enabled": True,
        },
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "total_tokens": 110,
        },
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_quality_score_calculation() -> None:
    score = compute_quality_score(
        {
            "answer_f1": 0.5,
            "kg_ref_f1": 0.25,
            "prediction_execution_success": True,
            "query_extracted": True,
        }
    )

    assert score == 0.4625


def test_quality_score_prefers_answer_cell_value_f1_when_available() -> None:
    score, metric_used = compute_quality_score_with_metric(
        {
            "answer_cell_value_f1": 0.8,
            "answer_f1": 0.2,
            "kg_ref_f1": 0.0,
            "predicate_ref_f1": 0.0,
            "prediction_execution_success": False,
            "query_extracted": True,
        }
    )
    assert metric_used == "answer_cell_value_f1"
    assert score == 0.42


def test_quality_score_falls_back_to_answer_f1_and_none() -> None:
    score_fallback, metric_fallback = compute_quality_score_with_metric(
        {
            "answer_f1": 0.5,
            "kg_ref_f1": 0.0,
            "predicate_ref_f1": 0.0,
            "prediction_execution_success": True,
            "query_extracted": False,
        }
    )
    score_none, metric_none = compute_quality_score_with_metric(
        {
            "kg_ref_f1": 0.0,
            "predicate_ref_f1": 0.0,
            "prediction_execution_success": True,
            "query_extracted": True,
        }
    )
    assert metric_fallback == "answer_f1"
    assert score_fallback == 0.3
    assert metric_none == "none"
    assert score_none == 0.2


def test_online_loop_respects_max_iterations(tmp_path: Path) -> None:
    calls = {"generate": 0, "evaluate": 0, "reflect": 0}

    def generate(payload: OnlineAceGenerationInput) -> dict:
        calls["generate"] += 1
        return _generation(payload)

    def evaluate(payload: OnlineAceEvaluationInput) -> dict:
        calls["evaluate"] += 1
        return _failed_eval(payload)

    def reflect(payload: OnlineAceReflectionInput) -> dict:
        calls["reflect"] += 1
        return _reflection(payload)

    run_online_ace_loop(
        _config(tmp_path, iterations=3),
        hooks=OnlineAceHooks(generate=generate, evaluate=evaluate, reflect=reflect),
    )

    summary = _read_json(tmp_path / "run" / "online_ace_summary.json")

    assert calls == {"generate": 3, "evaluate": 3, "reflect": 2}
    assert summary["total_attempts"] == 3
    assert summary["still_unsolved"] == 1


def test_solved_item_does_not_trigger_reflection(tmp_path: Path) -> None:
    reflect_calls = 0

    def reflect(_: OnlineAceReflectionInput) -> dict:
        nonlocal reflect_calls
        reflect_calls += 1
        return _reflection(_)

    run_online_ace_loop(
        _config(tmp_path, iterations=3),
        hooks=OnlineAceHooks(
            generate=_generation,
            evaluate=_solved_eval,
            reflect=reflect,
        ),
    )

    summary = _read_json(tmp_path / "run" / "online_ace_summary.json")
    trace = _read_json(tmp_path / "run" / "online_ace_trace.json")

    assert reflect_calls == 0
    assert summary["solved_initially"] == 1
    assert summary["total_attempts"] == 1
    assert trace["items"][0]["iterations"][0]["reflection_used"] is False


def test_failed_iteration_adds_context_rule_and_retries_item(tmp_path: Path) -> None:
    evaluations = [_failed_eval, _solved_eval]

    def evaluate(payload: OnlineAceEvaluationInput) -> dict:
        return evaluations[payload.iteration](payload)

    run_online_ace_loop(
        _config(tmp_path, iterations=2),
        hooks=OnlineAceHooks(
            generate=_generation,
            evaluate=evaluate,
            reflect=_reflection,
        ),
    )

    trace = _read_json(tmp_path / "run" / "online_ace_trace.json")
    summary = _read_json(tmp_path / "run" / "online_ace_summary.json")
    playbook = _read_json(tmp_path / "run" / "online_ace_playbook_final.json")

    assert len(trace["items"][0]["iterations"]) == 2
    assert trace["items"][0]["iterations"][0]["new_rule_added"] is True
    assert trace["items"][0]["iterations"][1]["context_rule_ids_used"] == ["rule-1"]
    assert trace["items"][0]["iterations"][1]["helpful_rule_ids"] == ["rule-1"]
    assert (
        trace["items"][0]["iterations"][1]["quality_score_answer_metric_used"]
        == "answer_f1"
    )
    assert summary["solved_after_reflection"] == 1
    assert summary["rules_added"] == 1
    assert playbook["bullets"][0]["id"] == "rule-1"
    assert playbook["bullets"][0]["helpful_count"] == 1


def test_online_trace_records_multiple_iterations_for_same_item(
    tmp_path: Path,
) -> None:
    run_online_ace_loop(
        _config(tmp_path, iterations=2),
        hooks=OnlineAceHooks(
            generate=_generation,
            evaluate=_failed_eval,
            reflect=_reflection,
        ),
    )

    trace = _read_json(tmp_path / "run" / "online_ace_trace.json")

    assert len(trace["items"]) == 1
    assert [attempt["iteration"] for attempt in trace["items"][0]["iterations"]] == [
        0,
        1,
    ]
    assert {
        attempt["item_id"] for attempt in trace["items"][0]["iterations"]
    } == {"1"}


def test_online_trace_records_merged_rule_metadata(tmp_path: Path) -> None:
    initial_playbook = tmp_path / "initial_playbook.json"
    initial_playbook.write_text(
        json.dumps(
            {
                "schema_version": "ace_playbook_v1",
                "family": "nlp4re",
                "mode": "pgmr_lite",
                "bullets": [
                    {
                        "id": "existing_rule",
                        "family": "nlp4re",
                        "mode": "pgmr_lite",
                        "category": "routing",
                        "title": "Use data production time path",
                        "content": "Use pgmr:nlp_data_production_time and avoid projecting ?nlpDataset for time questions.",
                        "priority": 80,
                        "enabled": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    cfg = _config(tmp_path, iterations=2)
    cfg = OnlineAceConfig(**{**cfg.to_dict(), "initial_playbook": initial_playbook})

    def reflect(_: OnlineAceReflectionInput) -> dict:
        return {
            "rule": {
                "id": "new_rule_candidate",
                "family": "nlp4re",
                "mode": "pgmr_lite",
                "category": "routing",
                "title": "Use data production time path",
                "content": "Use pgmr:nlp_data_production_time. Do not project ?nlpDataset for data production time.",
                "priority": 81,
                "enabled": True,
            }
        }

    run_online_ace_loop(
        cfg,
        hooks=OnlineAceHooks(generate=_generation, evaluate=_failed_eval, reflect=reflect),
    )
    trace = _read_json(tmp_path / "run" / "online_ace_trace.json")
    summary = _read_json(tmp_path / "run" / "online_ace_summary.json")
    first = trace["items"][0]["iterations"][0]
    assert first["new_rule_added"] is False
    assert first["rule_merged"] is True
    assert first["merged_into_rule_id"] == "existing_rule"
    assert first["proposed_rule"]["id"] == "new_rule_candidate"
    assert first["active_rule"]["id"] == "existing_rule"
    assert summary["rules_merged"] == 1
