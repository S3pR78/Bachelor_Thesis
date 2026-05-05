from __future__ import annotations

from src.ace.online.reporting import (
    format_final_report,
    format_item_context_update,
    format_iteration_report,
    format_start_report,
)


def test_format_start_report_includes_run_metadata() -> None:
    report = format_start_report(
        {
            "model": "mock_model",
            "reflect_model": "gpt_4o_mini",
            "dataset": "dataset.json",
            "family_filter": "nlp4re",
            "num_items": 3,
            "max_iterations": 2,
            "prompt_mode": "pgmr_mini",
            "prediction_format": "pgmr_lite",
            "output_dir": "outputs/run",
            "shuffle": True,
            "sample_seed": 42,
        }
    )

    assert "Online ACE run" in report
    assert "Model: mock_model" in report
    assert "Selected items: 3" in report
    assert "Shuffle: yes (sample seed: 42)" in report


def test_format_iteration_report_includes_attempt_metrics() -> None:
    report = format_iteration_report(
        {
            "iteration": 0,
            "prediction_execution_success": True,
            "answer_exact_match": False,
            "answer_f1": 0.5,
            "kg_ref_f1": 0.25,
            "error_category": "answer_mismatch",
            "reflection_used": True,
            "new_rule_added": True,
            "quality_score": 0.55,
        }
    )

    assert "Iteration 1" in report
    assert "Prediction execution success: yes" in report
    assert "answer_f1: 0.5000" in report
    assert "Reflection used: yes" in report
    assert "New rule added: yes" in report


def test_format_item_context_update_handles_empty_ids() -> None:
    report = format_item_context_update(
        helpful_rule_ids=[],
        harmful_rule_ids=["bad-rule"],
        disabled_rule_ids=[],
        enabled_rule_count=4,
    )

    assert "Helpful rules for this item: none" in report
    assert "Harmful rules for this item: bad-rule" in report
    assert "Rules disabled for this item: none" in report
    assert "Current enabled rules: 4" in report


def test_format_final_report_handles_numeric_and_unknown_cost() -> None:
    report = format_final_report(
        {
            "num_items": 2,
            "total_attempts": 3,
            "solved_initially": 1,
            "solved_after_reflection": 1,
            "still_unsolved": 0,
            "rules_added": 1,
            "rules_enabled": 1,
            "rules_disabled": 0,
            "rules_deleted": 0,
            "top_helpful_rules": [{"id": "rule-1", "helpful_count": 2}],
            "top_harmful_rules": [],
            "cost_summary": {
                "total_tokens": 123,
                "estimated_cost_usd": None,
            },
        }
    )

    assert "Total items: 2" in report
    assert "Top helpful rules: rule-1 (2)" in report
    assert "Total reflection tokens: 123" in report
    assert "Estimated reflection cost: unknown" in report

