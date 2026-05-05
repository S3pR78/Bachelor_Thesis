"""Terminal reporting helpers for online ACE runs."""

from __future__ import annotations

from typing import Any, Callable

from src.ace.online.costs import format_cost_block


def _value(value: Any, default: str = "unknown") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _fmt_bool(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _fmt_float(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "0.0000"


def _fmt_ids(ids: list[str] | None) -> str:
    return ", ".join(ids or []) if ids else "none"


def format_start_report(metadata: dict[str, Any]) -> str:
    """Format the run-start terminal report."""
    return "\n".join(
        [
            "Online ACE run",
            f"  Model: {_value(metadata.get('model'))}",
            f"  Reflect model: {_value(metadata.get('reflect_model'))}",
            f"  Dataset: {_value(metadata.get('dataset'))}",
            f"  Family filter: {_value(metadata.get('family_filter'), 'all')}",
            f"  Selected items: {int(metadata.get('num_items') or 0)}",
            f"  Max iterations: {int(metadata.get('max_iterations') or 0)}",
            f"  Prompt mode: {_value(metadata.get('prompt_mode'))}",
            f"  Prediction format: {_value(metadata.get('prediction_format'))}",
            f"  Output dir: {_value(metadata.get('output_dir'))}",
            (
                "  Shuffle: "
                f"{_fmt_bool(metadata.get('shuffle'))} "
                f"(sample seed: {metadata.get('sample_seed')})"
            ),
        ]
    )


def format_item_header(
    *,
    index: int,
    total: int,
    item_id: str,
    family: str,
    question: str | None,
) -> str:
    """Format the per-item terminal header."""
    return "\n".join(
        [
            f"Item {index}/{total}",
            f"  ID: {item_id}",
            f"  Family: {_value(family)}",
            f"  Question: {_value(question)}",
        ]
    )


def format_iteration_report(attempt: dict[str, Any]) -> str:
    """Format one iteration/attempt progress line."""
    return "\n".join(
        [
            f"  Iteration {int(attempt.get('iteration') or 0) + 1}",
            (
                "    Prediction execution success: "
                f"{_fmt_bool(attempt.get('prediction_execution_success'))}"
            ),
            f"    Answer exact match: {_fmt_bool(attempt.get('answer_exact_match'))}",
            f"    answer_f1: {_fmt_float(attempt.get('answer_f1'))}",
            f"    kg_ref_f1: {_fmt_float(attempt.get('kg_ref_f1'))}",
            f"    Error category: {_value(attempt.get('error_category'), 'none')}",
            f"    Reflection used: {_fmt_bool(attempt.get('reflection_used'))}",
            f"    New rule added: {_fmt_bool(attempt.get('new_rule_added'))}",
            f"    Quality score: {_fmt_float(attempt.get('quality_score'))}",
        ]
    )


def format_item_context_update(
    *,
    helpful_rule_ids: list[str],
    harmful_rule_ids: list[str],
    disabled_rule_ids: list[str],
    enabled_rule_count: int,
) -> str:
    """Format the per-item context update summary."""
    return "\n".join(
        [
            "Context update summary:",
            f"  Helpful rules for this item: {_fmt_ids(helpful_rule_ids)}",
            f"  Harmful rules for this item: {_fmt_ids(harmful_rule_ids)}",
            f"  Rules disabled for this item: {_fmt_ids(disabled_rule_ids)}",
            f"  Current enabled rules: {enabled_rule_count}",
        ]
    )


def format_final_report(summary: dict[str, Any]) -> str:
    """Format the final online ACE run report."""
    cost_summary = summary.get("cost_summary") or {}
    return "\n".join(
        [
            "Online ACE final summary",
            f"  Total items: {int(summary.get('num_items') or 0)}",
            f"  Total attempts: {int(summary.get('total_attempts') or 0)}",
            f"  Solved initially: {int(summary.get('solved_initially') or 0)}",
            (
                "  Solved after reflection: "
                f"{int(summary.get('solved_after_reflection') or 0)}"
            ),
            f"  Still unsolved: {int(summary.get('still_unsolved') or 0)}",
            f"  Rules added: {int(summary.get('rules_added') or 0)}",
            f"  Rules kept enabled: {int(summary.get('rules_enabled') or 0)}",
            f"  Rules disabled: {int(summary.get('rules_disabled') or 0)}",
            f"  Rules deleted: {int(summary.get('rules_deleted') or 0)}",
            f"  Top helpful rules: {_format_top_rules(summary.get('top_helpful_rules'))}",
            f"  Top harmful rules: {_format_top_rules(summary.get('top_harmful_rules'))}",
            (
                "  Total reflection tokens: "
                f"{int(cost_summary.get('total_tokens') or 0)}"
            ),
            (
                "  Estimated reflection cost: "
                f"{_format_estimated_cost(cost_summary.get('estimated_cost_usd'))}"
            ),
        ]
    )


def _format_top_rules(rules: Any) -> str:
    if not isinstance(rules, list) or not rules:
        return "none"
    formatted = []
    for rule in rules[:5]:
        if not isinstance(rule, dict):
            continue
        count_key = "helpful_count" if "helpful_count" in rule else "harmful_count"
        formatted.append(f"{rule.get('id')} ({rule.get(count_key, 0)})")
    return ", ".join(formatted) if formatted else "none"


def _format_estimated_cost(value: Any) -> str:
    if value is None:
        return "unknown"
    try:
        return f"${float(value):.4f}"
    except (TypeError, ValueError):
        return "unknown"


class OnlineAceReporter:
    """Small printer wrapper for online ACE progress."""

    def __init__(self, emit: Callable[[str], None] = print) -> None:
        self.emit = emit

    def start(self, metadata: dict[str, Any]) -> None:
        self.emit(format_start_report(metadata))

    def item_header(
        self,
        *,
        index: int,
        total: int,
        item_id: str,
        family: str,
        question: str | None,
    ) -> None:
        self.emit(
            format_item_header(
                index=index,
                total=total,
                item_id=item_id,
                family=family,
                question=question,
            )
        )

    def iteration(self, attempt: dict[str, Any]) -> None:
        self.emit(format_iteration_report(attempt))

    def item_context_update(
        self,
        *,
        helpful_rule_ids: list[str],
        harmful_rule_ids: list[str],
        disabled_rule_ids: list[str],
        enabled_rule_count: int,
    ) -> None:
        self.emit(
            format_item_context_update(
                helpful_rule_ids=helpful_rule_ids,
                harmful_rule_ids=harmful_rule_ids,
                disabled_rule_ids=disabled_rule_ids,
                enabled_rule_count=enabled_rule_count,
            )
        )

    def item_costs(
        self,
        *,
        question_cost: dict[str, Any],
        cumulative_cost: dict[str, Any],
    ) -> None:
        self.emit(format_cost_block("Cost for this question", question_cost))
        self.emit(format_cost_block("Cumulative cost", cumulative_cost))

    def final(self, summary: dict[str, Any]) -> None:
        self.emit(format_final_report(summary))

