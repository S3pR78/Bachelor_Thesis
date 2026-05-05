from __future__ import annotations

from pathlib import Path

from src.ace.online.loop import (
    OnlineAceConfig,
    OnlineAceEvaluationInput,
    OnlineAceGenerationInput,
)
from src.ace.online.pipeline import (
    OnlineAcePipeline,
    build_online_prompt,
    flatten_validation_metrics,
    render_online_ace_context,
)


def test_render_online_ace_context_uses_existing_bullet_renderer() -> None:
    context = render_online_ace_context(
        [
            {
                "id": "rule-1",
                "family": "nlp4re",
                "mode": "pgmr_lite",
                "category": "routing",
                "title": "Use contribution path",
                "content": "Connect paper to contribution first.",
                "positive_pattern": "?paper pgmr:has_contribution ?contribution .",
                "priority": 80,
                "enabled": True,
            }
        ]
    )

    assert "ACE playbook rules learned during this online run" in context
    assert "Use contribution path" in context
    assert "?paper pgmr:has_contribution ?contribution ." in context


def test_build_online_prompt_for_meta_mode_prepends_in_memory_rules(
    tmp_path: Path,
) -> None:
    config = OnlineAceConfig(
        model="mock_model",
        dataset=tmp_path / "dataset.json",
        prompt_mode="pgmr_lite_meta",
        prediction_format="pgmr_lite",
        sparql_endpoint="",
        initial_playbook=tmp_path / "missing.json",
        output_dir=tmp_path / "run",
        family="nlp4re",
    )

    prompt = build_online_prompt(
        OnlineAceGenerationInput(
            config=config,
            item={
                "id": "1",
                "family": "nlp4re",
                "question": "Which papers use guidelines?",
                "answer_type": "list",
                "query_shape": "tree",
            },
            iteration=0,
            context_rules=[
                {
                    "id": "rule-1",
                    "family": "nlp4re",
                    "mode": "pgmr_lite",
                    "category": "routing",
                    "title": "Use contribution path",
                    "content": "Connect paper to contribution first.",
                    "priority": 80,
                    "enabled": True,
                }
            ],
        )
    )

    assert prompt.startswith("ACE playbook rules learned during this online run")
    assert "question: Which papers use guidelines?" in prompt
    assert "pgmr_sparql:" in prompt


def test_flatten_validation_metrics_extracts_online_metric_surface() -> None:
    flattened = flatten_validation_metrics(
        {
            "query_extracted": {"value": 1.0},
            "prediction_execution_success": {"value": 1.0},
            "gold_execution_success": {"value": 1.0},
            "answer_exact_match": {"value": 0.0},
            "answer_precision_recall_f1": {"f1": 0.5},
            "kg_ref_match": {"f1": 0.75},
            "predicate_ref_match": {"f1": 0.25},
            "primary_error_category": "answer_mismatch",
        }
    )

    assert flattened == {
        "query_extracted": True,
        "prediction_execution_success": True,
        "gold_execution_success": True,
        "answer_exact_match": False,
        "answer_f1": 0.5,
        "kg_ref_f1": 0.75,
        "predicate_ref_f1": 0.25,
        "error_category": "answer_mismatch",
    }


def test_pipeline_evaluate_uses_existing_metrics_without_endpoint(
    tmp_path: Path,
) -> None:
    config = OnlineAceConfig(
        model="mock_model",
        dataset=tmp_path / "dataset.json",
        prompt_mode="zero_shot",
        prediction_format="sparql",
        sparql_endpoint="",
        initial_playbook=tmp_path / "missing.json",
        output_dir=tmp_path / "run",
        family="nlp4re",
    )
    pipeline = OnlineAcePipeline(
        config=config,
        inference_session={"provider": "mock", "model_config": {}},
        allowed_kg_refs=frozenset(),
    )

    result = pipeline.evaluate(
        OnlineAceEvaluationInput(
            config=config,
            item={
                "id": "1",
                "family": "nlp4re",
                "question": "Q?",
                "gold_sparql": "SELECT ?s WHERE { ?s ?p ?o . }",
            },
            iteration=0,
            generation={
                "raw_model_output": "SELECT ?s WHERE { ?s ?p ?o . }",
            },
        )
    )

    assert result["query_extracted"] is True
    assert result["prediction_query_form"] == "select"
    assert result["query_execution"]["reason"] == "no_endpoint_configured"
    assert result["error_category"] == "not_evaluated_no_endpoint"
