"""Cost tracking for online ACE reflection calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.evaluate.costs import estimate_openai_cost_usd, normalize_usage_payload


CostSummary = dict[str, int | float | None]


def _empty_cost_summary() -> CostSummary:
    return {
        "reflection_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
    }


def _aggregate_call_costs(calls: list[dict[str, Any]]) -> CostSummary:
    summary = _empty_cost_summary()
    estimated_total = 0.0
    has_unknown_cost = False

    for call in calls:
        summary["reflection_calls"] = int(summary["reflection_calls"] or 0) + 1
        summary["prompt_tokens"] = int(summary["prompt_tokens"] or 0) + int(
            call.get("prompt_tokens") or 0
        )
        summary["completion_tokens"] = int(
            summary["completion_tokens"] or 0
        ) + int(call.get("completion_tokens") or 0)
        summary["total_tokens"] = int(summary["total_tokens"] or 0) + int(
            call.get("total_tokens") or 0
        )

        estimated_cost_usd = call.get("estimated_cost_usd")
        if estimated_cost_usd is None:
            has_unknown_cost = True
        else:
            estimated_total += float(estimated_cost_usd)

    summary["estimated_cost_usd"] = (
        None if has_unknown_cost else round(estimated_total, 8)
    )
    return summary


@dataclass
class OnlineCostTracker:
    """Aggregate reflection usage for online ACE runs."""

    provider: str = "openai"

    def __post_init__(self) -> None:
        self._calls: list[dict[str, Any]] = []

    def add_usage(
        self,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: str,
        total_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Record one reflector usage event and return its normalized cost."""
        usage = normalize_usage_payload(
            {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        )

        estimated_cost_usd = None
        if self.provider == "openai":
            estimated_cost_usd = estimate_openai_cost_usd(
                model_name=model,
                usage=usage,
            )

        call = {
            "model": model,
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "total_tokens": usage["total_tokens"],
            "estimated_cost_usd": estimated_cost_usd,
        }
        self._calls.append(call)
        return call

    def snapshot(self) -> CostSummary:
        """Return cumulative reflection cost so far."""
        return _aggregate_call_costs(self._calls)

    def diff_since(self, previous_snapshot: CostSummary) -> CostSummary:
        """Return costs added since a previous snapshot from this tracker."""
        previous_call_count = int(previous_snapshot.get("reflection_calls") or 0)
        return _aggregate_call_costs(self._calls[previous_call_count:])


def format_cost_block(title: str, cost: CostSummary) -> str:
    """Format a terminal cost summary block."""
    estimated_cost_usd = cost.get("estimated_cost_usd")
    cost_text = (
        "unknown"
        if estimated_cost_usd is None
        else f"${float(estimated_cost_usd):.4f}"
    )

    return "\n".join(
        [
            f"{title}:",
            f"  Reflection calls: {int(cost.get('reflection_calls') or 0)}",
            f"  Prompt tokens: {int(cost.get('prompt_tokens') or 0)}",
            f"  Completion tokens: {int(cost.get('completion_tokens') or 0)}",
            f"  Total tokens: {int(cost.get('total_tokens') or 0)}",
            f"  Estimated cost: {cost_text}",
        ]
    )

