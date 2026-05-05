"""Skeleton for the true online ACE loop.

Online ACE updates context during a run: each failed question can trigger one
small rule update, and the same question is retried with the updated context.
The implementation will be added in small, testable steps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Callable

from src.ace.online.context import OnlineAceContext
from src.ace.online.costs import OnlineCostTracker
from src.ace.online.selection import (
    load_dataset_items,
    select_dataset_items,
    selected_item_ids,
)
from src.ace.online.trace import OnlineAceTraceWriter, build_empty_summary


SOLVED_ANSWER_F1_THRESHOLD = 0.99
RULE_QUALITY_DELTA_THRESHOLD = 0.05


@dataclass(frozen=True)
class OnlineAceConfig:
    """Configuration parsed by the thin online ACE CLI wrapper."""

    model: str
    dataset: Path
    prompt_mode: str
    prediction_format: str
    sparql_endpoint: str
    initial_playbook: Path
    output_dir: Path
    family: str | None = None
    pgmr_memory_dir: Path | None = None
    iterations: int = 3
    limit: int | None = None
    shuffle: bool = False
    sample_seed: int = 42
    reflect_model: str = "gpt_4o_mini"
    ace_max_bullets: int = 3
    disable_harmful_rules: bool = False
    delete_harmful_rules: bool = False
    min_harmful_count: int = 2
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of this config."""
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        return data


@dataclass(frozen=True)
class OnlineAceGenerationInput:
    """Input passed to a pluggable generation hook."""

    config: OnlineAceConfig
    item: dict[str, Any]
    iteration: int
    context_rules: list[dict[str, Any]]


@dataclass(frozen=True)
class OnlineAceEvaluationInput:
    """Input passed to a pluggable evaluation hook."""

    config: OnlineAceConfig
    item: dict[str, Any]
    iteration: int
    generation: dict[str, Any]


@dataclass(frozen=True)
class OnlineAceReflectionInput:
    """Input passed to a pluggable reflection hook."""

    config: OnlineAceConfig
    item: dict[str, Any]
    iteration: int
    generation: dict[str, Any]
    evaluation: dict[str, Any]
    context_rules: list[dict[str, Any]]


@dataclass(frozen=True)
class OnlineAceHooks:
    """Pluggable hooks used by the online loop skeleton."""

    generate: Callable[[OnlineAceGenerationInput], str | dict[str, Any]]
    evaluate: Callable[[OnlineAceEvaluationInput], dict[str, Any]]
    reflect: Callable[[OnlineAceReflectionInput], dict[str, Any] | None]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "success", "passed"}
    return False


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _metric(evaluation: dict[str, Any], key: str) -> Any:
    metrics = evaluation.get("metrics")
    if isinstance(metrics, dict) and key in metrics:
        return metrics[key]
    return evaluation.get(key)


def is_solved(evaluation: dict[str, Any]) -> bool:
    """Return whether an online ACE attempt is solved for the MVP threshold."""
    if not _as_bool(_metric(evaluation, "prediction_execution_success")):
        return False

    return _as_bool(_metric(evaluation, "answer_exact_match")) or (
        _as_float(_metric(evaluation, "answer_f1")) >= SOLVED_ANSWER_F1_THRESHOLD
    )


def compute_quality_score(evaluation: dict[str, Any]) -> float:
    """Compute the rule usefulness quality score."""
    return round(
        0.45 * _as_float(_metric(evaluation, "answer_f1"))
        + 0.30 * _as_float(_metric(evaluation, "kg_ref_f1"))
        + 0.15 * float(_as_bool(_metric(evaluation, "prediction_execution_success")))
        + 0.10 * float(_as_bool(_metric(evaluation, "query_extracted"))),
        6,
    )


def _normalize_generation(generation: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(generation, dict):
        return dict(generation)
    return {"raw_model_output": str(generation)}


def _extract_rule_payload(reflection: dict[str, Any] | None) -> dict[str, Any] | None:
    if not reflection:
        return None
    rule = reflection.get("rule")
    if isinstance(rule, dict):
        return rule
    if {"category", "title", "content"}.issubset(reflection):
        return reflection
    return None


def _record_reflection_cost(
    *,
    reflection: dict[str, Any] | None,
    config: OnlineAceConfig,
    cost_tracker: OnlineCostTracker,
) -> dict[str, Any] | None:
    if not reflection:
        return None

    usage = reflection.get("usage")
    if not isinstance(usage, dict):
        return None

    return cost_tracker.add_usage(
        model=str(reflection.get("model") or config.reflect_model),
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        total_tokens=usage.get("total_tokens"),
    )


def _build_run_metadata(
    *,
    config: OnlineAceConfig,
    num_items: int,
) -> dict[str, Any]:
    return {
        "model": config.model,
        "reflect_model": config.reflect_model,
        "dataset": str(config.dataset),
        "family_filter": config.family,
        "num_items": num_items,
        "max_iterations": config.iterations,
        "prompt_mode": config.prompt_mode,
        "prediction_format": config.prediction_format,
        "output_dir": str(config.output_dir),
        "shuffle": config.shuffle,
        "sample_seed": config.sample_seed,
        "limit": config.limit,
        "dry_run": config.dry_run,
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _mean_metrics(attempts: list[dict[str, Any]]) -> dict[str, float | None]:
    return {
        "answer_f1": _mean(
            [_as_float(_metric(attempt, "answer_f1")) for attempt in attempts]
        ),
        "execution_success": _mean(
            [
                float(_as_bool(_metric(attempt, "prediction_execution_success")))
                for attempt in attempts
            ]
        ),
        "kg_ref_f1": _mean(
            [_as_float(_metric(attempt, "kg_ref_f1")) for attempt in attempts]
        ),
    }


def _delta(final_value: float | None, initial_value: float | None) -> float | None:
    if final_value is None or initial_value is None:
        return None
    return round(final_value - initial_value, 6)


def _build_summary(
    *,
    metadata: dict[str, Any],
    selected_ids: list[str],
    total_attempts: int,
    solved_initially: int,
    solved_after_reflection: int,
    still_unsolved: int,
    rules_added: int,
    context: OnlineAceContext,
    initial_attempts: list[dict[str, Any]],
    final_attempts: list[dict[str, Any]],
    cost_summary: dict[str, Any],
) -> dict[str, Any]:
    summary = build_empty_summary(
        metadata=metadata,
        selected_item_ids=selected_ids,
        cost_summary=cost_summary,
    )
    initial_metrics = _mean_metrics(initial_attempts)
    final_metrics = _mean_metrics(final_attempts)
    disabled_count = sum(1 for rule in context.playbook.bullets if not rule.enabled)

    summary.update(
        {
            "family_filter": metadata.get("family_filter"),
            "shuffle": metadata.get("shuffle"),
            "sample_seed": metadata.get("sample_seed"),
            "limit": metadata.get("limit"),
            "total_attempts": total_attempts,
            "solved_initially": solved_initially,
            "solved_after_reflection": solved_after_reflection,
            "still_unsolved": still_unsolved,
            "rules_added": rules_added,
            "rules_enabled": context.enabled_rule_count(),
            "rules_disabled": disabled_count,
            "rules_deleted": len(context.deleted_rules),
            "top_helpful_rules": _top_rules(context, "helpful_count"),
            "top_harmful_rules": _top_rules(context, "harmful_count"),
            "initial_metrics_mean": initial_metrics,
            "final_metrics_mean": final_metrics,
            "improvements": {
                "answer_f1_delta": _delta(
                    final_metrics["answer_f1"],
                    initial_metrics["answer_f1"],
                ),
                "execution_success_delta": _delta(
                    final_metrics["execution_success"],
                    initial_metrics["execution_success"],
                ),
                "kg_ref_f1_delta": _delta(
                    final_metrics["kg_ref_f1"],
                    initial_metrics["kg_ref_f1"],
                ),
            },
        }
    )
    return summary


def _top_rules(context: OnlineAceContext, field_name: str) -> list[dict[str, Any]]:
    rules = sorted(
        context.playbook.bullets,
        key=lambda rule: (-int(getattr(rule, field_name)), rule.id),
    )
    return [
        {
            "id": rule.id,
            "title": rule.title,
            field_name: int(getattr(rule, field_name)),
        }
        for rule in rules
        if int(getattr(rule, field_name)) > 0
    ][:5]


def run_online_ace_loop(
    config: OnlineAceConfig,
    *,
    hooks: OnlineAceHooks | None = None,
) -> int:
    """Run the online ACE loop.

    With hooks, this executes the lightweight online loop skeleton. The default
    non-hook path still refuses to run until real model/evaluation integration
    is added.
    """
    if config.iterations <= 0:
        raise ValueError("iterations must be positive")

    dataset_items = load_dataset_items(config.dataset)
    selected_items = select_dataset_items(
        dataset_items,
        family=config.family,
        limit=config.limit,
        shuffle=config.shuffle,
        sample_seed=config.sample_seed,
    )
    selected_ids = selected_item_ids(selected_items)
    metadata = _build_run_metadata(config=config, num_items=len(selected_items))

    if config.dry_run:
        print("Online ACE dry run configuration:")
        print(json.dumps(config.to_dict(), indent=2, sort_keys=True))
        print()
        print("Selected item IDs:")
        print(json.dumps(selected_ids, indent=2))
        return 0

    if hooks is None:
        from src.ace.online.pipeline import build_online_ace_hooks

        hooks = build_online_ace_hooks(config)

    context = OnlineAceContext.load(
        initial_playbook_path=config.initial_playbook,
        family=config.family or "global",
        mode=config.prediction_format,
        ace_max_bullets=config.ace_max_bullets,
        disable_harmful_rules=config.disable_harmful_rules,
        delete_harmful_rules=config.delete_harmful_rules,
        min_harmful_count=config.min_harmful_count,
    )
    cost_tracker = OnlineCostTracker()
    trace_writer = OnlineAceTraceWriter(config.output_dir)

    total_attempts = 0
    solved_initially = 0
    solved_after_reflection = 0
    still_unsolved = 0
    added_rule_ids: set[str] = set()
    initial_attempts: list[dict[str, Any]] = []
    final_attempts: list[dict[str, Any]] = []

    for item in selected_items:
        item_id = str(item.get("id"))
        item_family = str(item.get("family") or config.family or "")
        question_snapshot = cost_tracker.snapshot()
        item_trace: dict[str, Any] = {
            "item_id": item_id,
            "family": item_family,
            "question": item.get("question"),
            "iterations": [],
        }
        pending_rule_id: str | None = None
        pending_quality_before: float | None = None
        solved_iteration: int | None = None

        for iteration in range(config.iterations):
            selected_rules = context.select_rules(
                family=item_family or None,
                mode=config.prediction_format,
            )
            context_rule_ids = [rule.id for rule in selected_rules]
            context_rule_payloads = [rule.to_dict() for rule in selected_rules]

            generation = _normalize_generation(
                hooks.generate(
                    OnlineAceGenerationInput(
                        config=config,
                        item=item,
                        iteration=iteration,
                        context_rules=context_rule_payloads,
                    )
                )
            )
            evaluation = hooks.evaluate(
                OnlineAceEvaluationInput(
                    config=config,
                    item=item,
                    iteration=iteration,
                    generation=generation,
                )
            )
            generation.update(
                {
                    "extracted_query": evaluation.get("extracted_query")
                    or generation.get("extracted_query"),
                    "pgmr_restored_query": evaluation.get("pgmr_restored_query")
                    or generation.get("pgmr_restored_query"),
                    "selected_prediction_query": evaluation.get(
                        "selected_prediction_query"
                    )
                    or generation.get("selected_prediction_query"),
                }
            )
            quality_score = compute_quality_score(evaluation)
            total_attempts += 1

            if iteration == 0:
                initial_attempts.append(evaluation)
            final_attempts_for_item = evaluation

            helpful_rule_ids: list[str] = []
            harmful_rule_ids: list[str] = []
            disabled_rule_ids: list[str] = []
            quality_score_before = pending_quality_before
            quality_score_delta = None

            if pending_rule_id is not None and pending_quality_before is not None:
                quality_score_delta = round(quality_score - pending_quality_before, 6)
                if quality_score_delta > RULE_QUALITY_DELTA_THRESHOLD:
                    context.mark_helpful(
                        pending_rule_id,
                        item_id=item_id,
                        delta=quality_score_delta,
                    )
                    helpful_rule_ids.append(pending_rule_id)
                elif quality_score_delta < -RULE_QUALITY_DELTA_THRESHOLD:
                    disabled_rule_ids = context.mark_harmful(
                        pending_rule_id,
                        item_id=item_id,
                        delta=quality_score_delta,
                    )
                    harmful_rule_ids.append(pending_rule_id)
                pending_rule_id = None
                pending_quality_before = None

            solved = is_solved(evaluation)
            reflection_used = False
            new_rule_added = False
            new_rule = None
            reflection_cost = None

            if solved:
                solved_iteration = iteration
            elif iteration < config.iterations - 1:
                reflection_used = True
                reflection = hooks.reflect(
                    OnlineAceReflectionInput(
                        config=config,
                        item=item,
                        iteration=iteration,
                        generation=generation,
                        evaluation=evaluation,
                        context_rules=context_rule_payloads,
                    )
                )
                reflection_cost = _record_reflection_cost(
                    reflection=reflection,
                    config=config,
                    cost_tracker=cost_tracker,
                )
                rule_payload = _extract_rule_payload(reflection)
                if rule_payload is not None:
                    added_rule = context.add_rule(rule_payload)
                    pending_rule_id = added_rule.id
                    pending_quality_before = quality_score
                    new_rule_added = True
                    new_rule = added_rule.to_dict()
                    added_rule_ids.add(added_rule.id)

            attempt_trace = {
                "item_id": item_id,
                "family": item_family,
                "iteration": iteration,
                "question": item.get("question"),
                "context_rule_ids_used": context_rule_ids,
                "raw_model_output": generation.get("raw_model_output"),
                "extracted_query": generation.get("extracted_query"),
                "pgmr_restored_query": generation.get("pgmr_restored_query"),
                "selected_prediction_query": generation.get(
                    "selected_prediction_query"
                ),
                "prediction_execution_success": _as_bool(
                    _metric(evaluation, "prediction_execution_success")
                ),
                "gold_execution_success": _as_bool(
                    _metric(evaluation, "gold_execution_success")
                ),
                "answer_exact_match": _as_bool(
                    _metric(evaluation, "answer_exact_match")
                ),
                "answer_f1": _as_float(_metric(evaluation, "answer_f1")),
                "kg_ref_f1": _as_float(_metric(evaluation, "kg_ref_f1")),
                "predicate_ref_f1": _as_float(
                    _metric(evaluation, "predicate_ref_f1")
                ),
                "error_category": evaluation.get("error_category"),
                "reflection_used": reflection_used,
                "new_rule_added": new_rule_added,
                "new_rule": new_rule,
                "quality_score": quality_score,
                "quality_score_before": quality_score_before,
                "quality_score_after": quality_score,
                "quality_score_delta": quality_score_delta,
                "helpful_rule_ids": helpful_rule_ids,
                "harmful_rule_ids": harmful_rule_ids,
                "disabled_rule_ids": disabled_rule_ids,
                "enabled_rule_count": context.enabled_rule_count(),
                "reflection_cost": reflection_cost,
            }
            item_trace["iterations"].append(attempt_trace)

            if solved:
                break

        final_attempts.append(final_attempts_for_item)
        if solved_iteration == 0:
            solved_initially += 1
        elif solved_iteration is not None:
            solved_after_reflection += 1
        else:
            still_unsolved += 1

        question_cost = cost_tracker.diff_since(question_snapshot)
        cumulative_cost = cost_tracker.snapshot()
        item_trace["question_cost"] = question_cost
        item_trace["cumulative_cost_after_item"] = cumulative_cost
        if item_trace["iterations"]:
            item_trace["iterations"][-1]["question_cost"] = question_cost
            item_trace["iterations"][-1][
                "cumulative_cost_after_item"
            ] = cumulative_cost

        trace_writer.add_item_trace(item_trace)

    cost_summary = cost_tracker.snapshot()
    summary = _build_summary(
        metadata=metadata,
        selected_ids=selected_ids,
        total_attempts=total_attempts,
        solved_initially=solved_initially,
        solved_after_reflection=solved_after_reflection,
        still_unsolved=still_unsolved,
        rules_added=len(added_rule_ids),
        context=context,
        initial_attempts=initial_attempts,
        final_attempts=final_attempts,
        cost_summary=cost_summary,
    )
    trace_writer.write_all(
        metadata=metadata,
        summary=summary,
        playbook_payload=context.to_playbook_dict(),
        cost_summary=cost_summary,
    )

    return 0
