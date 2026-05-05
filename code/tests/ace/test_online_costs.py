from __future__ import annotations

from src.ace.online.costs import OnlineCostTracker, format_cost_block


def test_cost_tracker_aggregates_multiple_reflection_calls() -> None:
    tracker = OnlineCostTracker()

    first = tracker.add_usage(
        model="gpt_4o_mini",
        prompt_tokens=1000,
        completion_tokens=100,
    )
    second = tracker.add_usage(
        model="gpt_4o_mini",
        prompt_tokens=2000,
        completion_tokens=200,
    )

    snapshot = tracker.snapshot()

    assert snapshot["reflection_calls"] == 2
    assert snapshot["prompt_tokens"] == 3000
    assert snapshot["completion_tokens"] == 300
    assert snapshot["total_tokens"] == 3300
    assert snapshot["estimated_cost_usd"] == round(
        first["estimated_cost_usd"] + second["estimated_cost_usd"],
        8,
    )


def test_diff_since_returns_per_question_cost() -> None:
    tracker = OnlineCostTracker()
    tracker.add_usage(
        model="gpt_4o_mini",
        prompt_tokens=100,
        completion_tokens=10,
    )
    before_question = tracker.snapshot()

    tracker.add_usage(
        model="gpt_4o_mini",
        prompt_tokens=200,
        completion_tokens=20,
    )
    tracker.add_usage(
        model="gpt_4o_mini",
        prompt_tokens=300,
        completion_tokens=30,
    )

    question_cost = tracker.diff_since(before_question)

    assert question_cost["reflection_calls"] == 2
    assert question_cost["prompt_tokens"] == 500
    assert question_cost["completion_tokens"] == 50
    assert question_cost["total_tokens"] == 550


def test_cumulative_cost_increases_after_each_item() -> None:
    tracker = OnlineCostTracker()

    first_snapshot = tracker.snapshot()
    tracker.add_usage(
        model="gpt_4o_mini",
        prompt_tokens=100,
        completion_tokens=10,
    )
    second_snapshot = tracker.snapshot()
    tracker.add_usage(
        model="gpt_4o_mini",
        prompt_tokens=200,
        completion_tokens=20,
    )
    third_snapshot = tracker.snapshot()

    assert first_snapshot["reflection_calls"] == 0
    assert second_snapshot["reflection_calls"] == 1
    assert third_snapshot["reflection_calls"] == 2
    assert third_snapshot["total_tokens"] > second_snapshot["total_tokens"]


def test_unknown_pricing_keeps_estimated_cost_null() -> None:
    tracker = OnlineCostTracker()

    call = tracker.add_usage(
        model="unknown_reflector_model",
        prompt_tokens=100,
        completion_tokens=10,
    )

    assert call["estimated_cost_usd"] is None
    assert tracker.snapshot()["estimated_cost_usd"] is None


def test_format_cost_block_handles_numeric_cost() -> None:
    block = format_cost_block(
        "Cost for this question",
        {
            "reflection_calls": 2,
            "prompt_tokens": 4812,
            "completion_tokens": 693,
            "total_tokens": 5505,
            "estimated_cost_usd": 0.0028,
        },
    )

    assert "Cost for this question:" in block
    assert "Reflection calls: 2" in block
    assert "Estimated cost: $0.0028" in block


def test_format_cost_block_handles_unknown_cost() -> None:
    block = format_cost_block(
        "Cumulative cost",
        {
            "reflection_calls": 1,
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "total_tokens": 110,
            "estimated_cost_usd": None,
        },
    )

    assert "Cumulative cost:" in block
    assert "Estimated cost: unknown" in block

