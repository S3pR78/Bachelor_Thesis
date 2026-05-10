from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from ace.core.reflector import Reflector
from ace.core.curator import Curator
from ace.playbook_utils import (
    apply_curator_operations,
    extract_playbook_bullets,
    get_next_global_id,
    get_playbook_stats,
)
from ace.orkg.adapter import (
    compact_json,
    get_family,
    get_prediction_format,
    get_validation_metric,
    get_f1,
    get_nested,
    select_gold_target,
    build_reasoning_trace,
    build_predicted_answer,
    build_environment_feedback,
    build_question_context,
)
from ace.orkg.offline import load_raw_items, playbook_output_path
from ace.orkg.planner import plan_question_with_llm
from ace.orkg.rule_retrieval import (
    load_playbook_rules,
    select_top_k_rules,
    build_temporary_playbook_from_plan_and_rules,
)
from ace.orkg.safety import filter_safe_operations
from src.evaluate.run_io import get_benchmark_raw_output_path


SUPPORTED_ONLINE_MODES = {"playbook_refinement", "test_time_repair"}


def load_dataset(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected dataset JSON list: {path}")
    return data


def write_single_item_dataset(item: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([item], ensure_ascii=False, indent=2), encoding="utf-8")


def copy_initial_playbooks(
    *,
    source_playbook_dir: Path,
    working_playbook_dir: Path,
    generator_model_key: str,
) -> None:
    src = source_playbook_dir / generator_model_key
    dst = working_playbook_dir / generator_model_key

    if not src.exists():
        raise FileNotFoundError(f"Initial playbook directory not found: {src}")

    if dst.exists():
        shutil.rmtree(dst)

    shutil.copytree(src, dst)


def family_playbook_path(
    *,
    playbook_dir: Path,
    generator_model_key: str,
    family: str,
    prediction_format: str,
) -> Path:
    return playbook_output_path(
        playbook_dir,
        generator_model_key=generator_model_key,
        family=family,
        prediction_format=prediction_format,
    )


def read_playbook_or_empty(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return """## STRATEGIES & INSIGHTS

## COMMON MISTAKES TO AVOID

## OTHERS"""


def run_one_item_evaluation(
    *,
    item: dict[str, Any],
    dataset_path: Path,
    run_dir: Path,
    model_key: str,
    inference_session: dict[str, Any],
    prompt_mode: str,
    prediction_format: str,
    playbook_dir: Path,
    ace_max_bullets: int,
    sparql_endpoint: str,
    pgmr_memory_dir: str,
    pgmr_similarity_mapping: bool,
) -> tuple[dict[str, Any], Path]:
    """Run the evaluation pipeline for one item and return its benchmark_raw entry."""
    from src.evaluate.runner import execute_evaluate_task

    write_single_item_dataset(item, dataset_path)

    eval_args = argparse.Namespace(
        model=model_key,
        dataset=str(dataset_path),
        limit=None,
        prompt_mode=prompt_mode,
        sparql_endpoint=sparql_endpoint,
        prediction_format=prediction_format,
        postprocess_pgmr=False,
        pgmr_memory_dir=pgmr_memory_dir,
        pgmr_similarity_mapping=pgmr_similarity_mapping,
        pgmr_auto_map_threshold=0.90,
        pgmr_suggestion_threshold=0.75,
        pgmr_min_margin=0.08,
        kg_memory_path="code/data/orkg_memory/templates",
        ace_playbook=None,
        ace_playbook_dir=str(playbook_dir),
        ace_mode=None,
        ace_max_bullets=ace_max_bullets,
    )

    execute_evaluate_task(
        eval_args,
        inference_session=inference_session,
        run_dir_override=run_dir,
    )

    raw_path = get_benchmark_raw_output_path(run_dir)
    raw_items = load_raw_items(raw_path)

    if not raw_items:
        raise ValueError(f"Evaluation raw file contains no items: {raw_path}")

    return raw_items[0], raw_path


def supervised_score(item: dict[str, Any]) -> tuple[int, int, float, float, int]:
    """Gold-aware score for ace_playbook online refinement."""
    exact = 1 if get_validation_metric(item, "answer_exact_match") is True else 0
    exec_ok = 1 if get_validation_metric(item, "prediction_execution_success") is True else 0
    answer_f1 = float(get_f1(item, "answer_cell_value_precision_recall_f1") or 0.0)
    kg_f1 = float(get_f1(item, "kg_ref_match") or 0.0)
    extracted = 1 if get_validation_metric(item, "query_extracted") is True else 0
    return (exact, exec_ok, answer_f1, kg_f1, extracted)


def diagnostic_score(item: dict[str, Any]) -> int:
    """Non-gold score for test-time repair.

    This must not use gold answers, answer F1, exact match, KG-ref F1, or any
    metric that compares to the gold query/answer.
    """
    score = 0

    if get_validation_metric(item, "query_extracted") is True:
        score += 10

    extraction_status = str(item.get("extraction_status") or "").lower()
    if "ok" in extraction_status:
        score += 8
    if "missing" in extraction_status or "failure" in extraction_status:
        score -= 6

    if get_validation_metric(item, "prediction_execution_success") is True:
        score += 15

    query_execution_status = str(get_nested(item, "query_execution", "status") or "").lower()
    if query_execution_status == "ok":
        score += 5
    if "error" in query_execution_status:
        score -= 8

    execution_error = item.get("execution_error") or item.get("error")
    if execution_error:
        score -= 8
    else:
        score += 2

    if get_validation_metric(item, "uri_hallucination") is True:
        score -= 8

    pgmr_unmapped = get_validation_metric(item, "pgmr_unmapped_placeholders")
    if pgmr_unmapped:
        score -= 8

    # Empty-result information is non-gold, but only a weak signal.
    result_type = str(get_nested(item, "query_execution", "result_type") or "").lower()
    response_json = get_nested(item, "query_execution", "response_json")
    if result_type == "select" and isinstance(response_json, dict):
        bindings = (
            response_json.get("results", {}).get("bindings")
            if isinstance(response_json.get("results"), dict)
            else None
        )
        if bindings == []:
            score -= 2

    return score


def is_attempt_good_enough(item: dict[str, Any], *, online_mode: str) -> bool:
    if online_mode == "playbook_refinement":
        return get_validation_metric(item, "answer_exact_match") is True

    # test_time_repair: only non-gold diagnostics
    return diagnostic_score(item) >= 30


def compare_attempts(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    online_mode: str,
) -> tuple[str, dict[str, Any]]:
    """Classify a candidate rule outcome."""
    if online_mode == "playbook_refinement":
        s1 = supervised_score(before)
        s2 = supervised_score(after)
        comparison = {
            "comparison_mode": "supervised",
            "before_score": s1,
            "after_score": s2,
        }
    else:
        s1 = diagnostic_score(before)
        s2 = diagnostic_score(after)
        comparison = {
            "comparison_mode": "diagnostic_non_gold",
            "before_score": s1,
            "after_score": s2,
        }

    if s2 > s1:
        return "accepted_helpful", comparison
    if s2 < s1:
        return "rejected_harmful", comparison
    return "rejected_unchanged", comparison


def non_gold_environment_feedback(item: dict[str, Any]) -> str:
    """Environment feedback for test-time repair without gold-derived metrics."""
    feedback = {
        "prediction_execution_success": get_validation_metric(item, "prediction_execution_success"),
        "query_extracted": get_validation_metric(item, "query_extracted"),
        "extraction_status": item.get("extraction_status"),
        "postprocessing_status": item.get("postprocessing_status"),
        "query_execution_status": get_nested(item, "query_execution", "status"),
        "query_execution_result_type": get_nested(item, "query_execution", "result_type"),
        "execution_error": item.get("execution_error") or item.get("error"),
        "uri_hallucination": get_validation_metric(item, "uri_hallucination"),
        "pgmr_unmapped_placeholders": get_validation_metric(item, "pgmr_unmapped_placeholders"),
        "diagnostic_score": diagnostic_score(item),
        "note": (
            "Test-time repair mode: feedback excludes gold query, gold answer, "
            "answer_exact_match, answer F1, KG-reference F1, and other gold-derived scores."
        ),
    }
    return compact_json({k: v for k, v in feedback.items() if v not in (None, "", [])})


def build_online_question_context(
    item: dict[str, Any],
    *,
    online_mode: str,
    gold_field: str | None,
) -> str:
    if online_mode == "playbook_refinement":
        return build_question_context(
            item,
            gold_field or "gold_target",
            run_note=(
                "Online ACE playbook refinement on ace_playbook split. Gold-derived "
                "feedback may be used for rule construction and acceptance."
            ),
        )

    return build_question_context(
        item,
        "none_for_test_time_repair",
        run_note=(
            "Online ACE test-time repair mode. Rule construction and attempt selection "
            "must use only non-gold diagnostic feedback. Temporary repair rules are not "
            "carried over to later benchmark items."
        ),
    )


def write_temp_playbook_dir(
    *,
    base_playbook_dir: Path,
    generator_model_key: str,
    family: str,
    prediction_format: str,
    playbook_text: str,
) -> Path:
    model_dir = base_playbook_dir / generator_model_key
    model_dir.mkdir(parents=True, exist_ok=True)
    path = family_playbook_path(
        playbook_dir=base_playbook_dir,
        generator_model_key=generator_model_key,
        family=family,
        prediction_format=prediction_format,
    )
    path.write_text(playbook_text, encoding="utf-8")
    return base_playbook_dir


def build_item_temp_playbook(
    *,
    source_playbook_text: str,
    source_playbook_path: Path,
    question: str,
    plan: dict[str, Any],
    family: str,
    prediction_format: str,
    top_k_rules: int,
    extra_rule_operations: list[dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    rules = load_playbook_rules(source_playbook_path)
    selected_rules = select_top_k_rules(
        question=question,
        plan=plan,
        rules=rules,
        top_k=top_k_rules,
    )

    extra_rules = []
    if extra_rule_operations:
        for idx, op in enumerate(extra_rule_operations, start=1):
            content = str(op.get("content") or "").strip()
            if not content:
                continue
            extra_rules.append(
                {
                    "id": f"tmp-{idx:05d}",
                    "section": op.get("section", "strategies_and_insights"),
                    "helpful": 0,
                    "harmful": 0,
                    "content": content,
                    "source": "temporary_candidate_rule",
                }
            )

    temp_playbook = build_temporary_playbook_from_plan_and_rules(
        plan=plan,
        selected_rules=selected_rules,
        family=family,
        prediction_format=prediction_format,
        extra_rules=extra_rules,
    )

    return temp_playbook, selected_rules


def run_online_ace(
    *,
    dataset_path: Path,
    generator_model_key: str,
    prompt_mode: str,
    prediction_format: str,
    planner_client: Any,
    planner_provider: str,
    planner_model: str,
    planner_max_tokens: int,
    reflector: Reflector,
    curator: Curator,
    initial_playbook_dir: Path,
    out_dir: Path,
    online_mode: str,
    limit: int | None = None,
    top_k_rules: int = 8,
    ace_max_bullets: int = -1,
    max_attempts: int = 2,
    sparql_endpoint: str = "https://www.orkg.org/triplestore",
    pgmr_memory_dir: str = "code/data/orkg_memory/templates",
    pgmr_similarity_mapping: bool = True,
    publish_final_playbooks: bool = False,
    refine_every_accepted: int = 0,
    generator_inference_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if online_mode not in SUPPORTED_ONLINE_MODES:
        raise ValueError(f"Unsupported online_mode={online_mode!r}")

    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "llm_logs").mkdir(parents=True, exist_ok=True)

    working_playbook_dir = out_dir / "working_playbooks"
    copy_initial_playbooks(
        source_playbook_dir=initial_playbook_dir,
        working_playbook_dir=working_playbook_dir,
        generator_model_key=generator_model_key,
    )

    dataset = load_dataset(dataset_path)
    selected_items = dataset[:limit] if limit is not None else dataset

    item_runs_dir = out_dir / "item_runs"
    item_runs_dir.mkdir(parents=True, exist_ok=True)

    if generator_inference_session is None:
        from src.query.inference_session import prepare_inference_session

        generator_inference_session = prepare_inference_session(generator_model_key)

    attempts_log: list[dict[str, Any]] = []
    decisions_log: list[dict[str, Any]] = []
    planner_log: list[dict[str, Any]] = []

    accepted_rule_count = 0
    rejected_unchanged_count = 0
    rejected_harmful_count = 0
    rejected_unsafe_count = 0
    already_good_count = 0
    reflected_count = 0
    attempt_counts: dict[int, int] = {}

    for idx, source_item in enumerate(selected_items, start=1):
        item_id = str(source_item.get("id") or f"item_{idx:04d}")
        item_dir = item_runs_dir / item_id
        item_dir.mkdir(parents=True, exist_ok=True)

        family = get_family(source_item)
        question = source_item.get("question") or ""

        full_playbook_path = family_playbook_path(
            playbook_dir=working_playbook_dir,
            generator_model_key=generator_model_key,
            family=family,
            prediction_format=prediction_format,
        )
        full_playbook_text = read_playbook_or_empty(full_playbook_path)

        plan, planner_call_info = plan_question_with_llm(
            question=question,
            family=family,
            prediction_format=prediction_format,
            api_client=planner_client,
            api_provider=planner_provider,
            model=planner_model,
            max_tokens=planner_max_tokens,
            call_id=f"online_plan_{idx:04d}_{item_id}",
            log_dir=str(out_dir / "llm_logs"),
        )

        planner_log.append(
            {
                "idx": idx,
                "id": item_id,
                "family": family,
                "prediction_format": prediction_format,
                "plan": plan,
                "call_info": planner_call_info,
            }
        )

        accepted_operations_for_item: list[dict[str, Any]] = []
        previous_attempt_item: dict[str, Any] | None = None
        previous_attempt_raw: Path | None = None

        item_had_helpful_rule = False
        item_attempts = 0

        for attempt in range(1, max_attempts + 1):
            item_attempts += 1
            attempt_counts[attempt] = attempt_counts.get(attempt, 0) + 1

            temp_playbook_text, selected_rules = build_item_temp_playbook(
                source_playbook_text=full_playbook_text,
                source_playbook_path=full_playbook_path,
                question=question,
                plan=plan,
                family=family,
                prediction_format=prediction_format,
                top_k_rules=top_k_rules,
                extra_rule_operations=accepted_operations_for_item,
            )

            attempt_playbook_dir = item_dir / f"attempt_{attempt}_playbooks"
            write_temp_playbook_dir(
                base_playbook_dir=attempt_playbook_dir,
                generator_model_key=generator_model_key,
                family=family,
                prediction_format=prediction_format,
                playbook_text=temp_playbook_text,
            )

            attempt_item, attempt_raw = run_one_item_evaluation(
                item=source_item,
                dataset_path=item_dir / f"attempt_{attempt}_dataset.json",
                run_dir=item_dir / f"attempt_{attempt}_evaluation",
                model_key=generator_model_key,
                inference_session=generator_inference_session,
                prompt_mode=prompt_mode,
                prediction_format=prediction_format,
                playbook_dir=attempt_playbook_dir,
                ace_max_bullets=ace_max_bullets,
                sparql_endpoint=sparql_endpoint,
                pgmr_memory_dir=pgmr_memory_dir,
                pgmr_similarity_mapping=pgmr_similarity_mapping,
            )

            attempts_log.append(
                {
                    "idx": idx,
                    "id": item_id,
                    "family": family,
                    "attempt": attempt,
                    "raw_path": str(attempt_raw),
                    "diagnostic_score": diagnostic_score(attempt_item),
                    "supervised_score": supervised_score(attempt_item)
                    if online_mode == "playbook_refinement"
                    else None,
                    "selected_rule_ids": [rule.get("id") for rule in selected_rules],
                    "temporary_rule_count": len(accepted_operations_for_item),
                }
            )

            if attempt == 1:
                previous_attempt_item = attempt_item
                previous_attempt_raw = attempt_raw

                if is_attempt_good_enough(attempt_item, online_mode=online_mode):
                    already_good_count += 1
                    decisions_log.append(
                        {
                            "idx": idx,
                            "id": item_id,
                            "family": family,
                            "attempt": attempt,
                            "decision": "skip_reflection_already_good",
                            "online_mode": online_mode,
                        }
                    )
                    break

                if max_attempts == 1:
                    break

            else:
                assert previous_attempt_item is not None
                decision, comparison = compare_attempts(
                    before=previous_attempt_item,
                    after=attempt_item,
                    online_mode=online_mode,
                )

                latest_ops = accepted_operations_for_item[-1:] if accepted_operations_for_item else []

                if decision == "accepted_helpful":
                    item_had_helpful_rule = True

                    if online_mode == "playbook_refinement":
                        # Persist only helpful rules in playbook_refinement.
                        full_playbook_text, _next_id = apply_curator_operations(
                            full_playbook_text,
                            latest_ops,
                            get_next_global_id(full_playbook_text),
                        )
                        full_playbook_path.parent.mkdir(parents=True, exist_ok=True)
                        full_playbook_path.write_text(full_playbook_text, encoding="utf-8")
                        accepted_rule_count += len(latest_ops)

                    decisions_log.append(
                        {
                            "idx": idx,
                            "id": item_id,
                            "family": family,
                            "attempt": attempt,
                            "online_mode": online_mode,
                            "decision": decision,
                            "comparison": comparison,
                            "candidate_operations": latest_ops,
                        }
                    )
                    break

                if decision == "rejected_harmful":
                    rejected_harmful_count += len(latest_ops) or 1
                else:
                    rejected_unchanged_count += len(latest_ops) or 1

                decisions_log.append(
                    {
                        "idx": idx,
                        "id": item_id,
                        "family": family,
                        "attempt": attempt,
                        "online_mode": online_mode,
                        "decision": decision,
                        "comparison": comparison,
                        "candidate_operations": latest_ops,
                    }
                )

                previous_attempt_item = attempt_item
                previous_attempt_raw = attempt_raw

                if attempt >= max_attempts:
                    break

            # If the latest attempt was not good enough and more attempts remain,
            # generate one new temporary candidate rule for the next attempt.
            if attempt >= max_attempts:
                break

            reflected_count += 1

            if online_mode == "playbook_refinement":
                gold_target, gold_field = select_gold_target(attempt_item)
                environment_feedback = build_environment_feedback(attempt_item)
                use_ground_truth = True
            else:
                gold_target = None
                gold_field = None
                environment_feedback = non_gold_environment_feedback(attempt_item)
                use_ground_truth = False

            current_prompt_playbook = temp_playbook_text
            bullets_used = extract_playbook_bullets(current_prompt_playbook, [])

            reflection, _bullet_tags, _ = reflector.reflect(
                question=attempt_item.get("question") or question,
                reasoning_trace=build_reasoning_trace(attempt_item),
                predicted_answer=build_predicted_answer(attempt_item),
                ground_truth=gold_target,
                environment_feedback=environment_feedback,
                bullets_used=bullets_used,
                use_ground_truth=use_ground_truth,
                use_json_mode=True,
                call_id=f"online_reflect_{idx:04d}_{item_id}_attempt_{attempt}",
                log_dir=str(out_dir / "llm_logs"),
            )

            _unsafe_playbook, _unsafe_next_id, operations, _ = curator.curate(
                current_playbook=current_prompt_playbook,
                recent_reflection=reflection,
                question_context=build_online_question_context(
                    attempt_item,
                    online_mode=online_mode,
                    gold_field=gold_field,
                ),
                current_step=idx,
                total_samples=len(selected_items),
                token_budget=4000,
                playbook_stats=get_playbook_stats(current_prompt_playbook),
                use_ground_truth=use_ground_truth,
                use_json_mode=True,
                call_id=f"online_curate_{idx:04d}_{item_id}_attempt_{attempt}",
                log_dir=str(out_dir / "llm_logs"),
                next_global_id=get_next_global_id(current_prompt_playbook),
            )

            safe_operations, rejected_operations = filter_safe_operations(
                operations,
                family=family,
                prediction_format=prediction_format,
            )

            if not safe_operations:
                rejected_unsafe_count += len(rejected_operations) or 1
                decisions_log.append(
                    {
                        "idx": idx,
                        "id": item_id,
                        "family": family,
                        "attempt": attempt,
                        "online_mode": online_mode,
                        "decision": "rejected_unsafe",
                        "rejected_operations": rejected_operations,
                    }
                )
                break

            # Use only the first safe rule for the next attempt. This keeps the
            # per-attempt attribution clear: one candidate rule -> one retry.
            accepted_operations_for_item.append(safe_operations[0])

        if online_mode == "test_time_repair":
            # Candidate rules are intentionally discarded after each item.
            pass

    final_playbook_dir = out_dir / "final_playbooks"
    if final_playbook_dir.exists():
        shutil.rmtree(final_playbook_dir)
    shutil.copytree(working_playbook_dir, final_playbook_dir)

    if publish_final_playbooks and online_mode == "playbook_refinement":
        target_dir = initial_playbook_dir / generator_model_key
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in (final_playbook_dir / generator_model_key).glob("*.txt"):
            shutil.copy2(path, target_dir / path.name)

    summary = {
        "dataset_path": str(dataset_path),
        "generator_model_key": generator_model_key,
        "prompt_mode": prompt_mode,
        "prediction_format": prediction_format,
        "online_mode": online_mode,
        "total_items": len(selected_items),
        "already_good_count": already_good_count,
        "reflected_count": reflected_count,
        "attempt_counts": attempt_counts,
        "accepted_rule_count": accepted_rule_count,
        "rejected_unchanged_count": rejected_unchanged_count,
        "rejected_harmful_count": rejected_harmful_count,
        "rejected_unsafe_count": rejected_unsafe_count,
        "top_k_rules": top_k_rules,
        "max_attempts": max_attempts,
        "final_playbook_dir": str(final_playbook_dir),
        "published_final_playbooks": publish_final_playbooks and online_mode == "playbook_refinement",
    }

    (out_dir / "online_plans.json").write_text(compact_json(planner_log), encoding="utf-8")
    (out_dir / "online_attempts.json").write_text(compact_json(attempts_log), encoding="utf-8")
    (out_dir / "online_rule_decisions.json").write_text(
        compact_json(decisions_log),
        encoding="utf-8",
    )
    (out_dir / "online_summary.json").write_text(compact_json(summary), encoding="utf-8")

    return summary
