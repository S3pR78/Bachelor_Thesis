from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ace.core.reflector import Reflector
from ace.core.curator import Curator
from ace.playbook_utils import (
    get_playbook_stats,
    extract_playbook_bullets,
    get_next_global_id,
    apply_curator_operations,
)
from ace.orkg.adapter import (
    compact_json,
    get_family,
    get_prediction_format,
    get_validation_metric,
    select_gold_target,
    build_reasoning_trace,
    build_predicted_answer,
    build_environment_feedback,
    build_question_context,
)
from ace.orkg.safety import filter_safe_operations


def load_raw_items(raw_path: Path) -> list[dict[str, Any]]:
    data = json.loads(raw_path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    for key in ("results", "items", "examples", "raw_results"):
        if isinstance(data.get(key), list):
            return data[key]

    raise ValueError(f"Could not find item list in {raw_path}")


def empty_orkg_playbook() -> str:
    return """## STRATEGIES & INSIGHTS

## COMMON MISTAKES TO AVOID

## OTHERS"""


def select_items(
    items: list[dict[str, Any]],
    *,
    limit: int | None = None,
    include_correct: bool = False,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for item in items:
        if not include_correct and get_validation_metric(item, "answer_exact_match") is True:
            continue
        selected.append(item)
        if limit is not None and len(selected) >= limit:
            break

    return selected


def playbook_output_path(
    playbook_dir: Path,
    *,
    generator_model_key: str,
    family: str,
    prediction_format: str,
) -> Path:
    return playbook_dir / generator_model_key / f"{family}__{prediction_format}.txt"


def run_offline_warmup(
    *,
    raw_path: Path,
    generator_model_key: str,
    reflector: Reflector,
    curator: Curator,
    out_dir: Path,
    playbook_dir: Path,
    limit: int | None = None,
    include_correct: bool = False,
    token_budget: int = 4000,
    publish_playbooks: bool = True,
) -> dict[str, Any]:
    """Run ACE offline warmup over an evaluated raw result file.

    The raw file is expected to contain model predictions and evaluation fields.
    Reflector/Curator are run per selected item. Curator operations are safety
    filtered before they are applied to the final playbooks.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "llm_logs").mkdir(parents=True, exist_ok=True)

    items = load_raw_items(raw_path)
    selected = select_items(items, limit=limit, include_correct=include_correct)

    playbooks: dict[tuple[str, str], str] = {}
    next_ids: dict[tuple[str, str], int] = {}

    all_reflections: list[dict[str, Any]] = []
    all_operations: list[dict[str, Any]] = []
    all_rejected_operations: list[dict[str, Any]] = []

    for idx, item in enumerate(selected, start=1):
        family = get_family(item)
        prediction_format = get_prediction_format(item)
        key = (family, prediction_format)

        if key not in playbooks:
            playbooks[key] = empty_orkg_playbook()
            next_ids[key] = get_next_global_id(playbooks[key])

        previous_playbook = playbooks[key]
        previous_next_id = next_ids[key]

        gold_target, gold_field = select_gold_target(item)
        bullets_used = extract_playbook_bullets(previous_playbook, [])

        reflection, bullet_tags, _ = reflector.reflect(
            question=item.get("question") or "",
            reasoning_trace=build_reasoning_trace(item),
            predicted_answer=build_predicted_answer(item),
            ground_truth=gold_target,
            environment_feedback=build_environment_feedback(item),
            bullets_used=bullets_used,
            use_ground_truth=True,
            use_json_mode=True,
            call_id=f"offline_reflect_{idx:04d}",
            log_dir=str(out_dir / "llm_logs"),
        )

        try:
            reflection_obj: Any = json.loads(reflection)
        except Exception:
            reflection_obj = reflection

        all_reflections.append({
            "idx": idx,
            "id": item.get("id"),
            "family": family,
            "prediction_format": prediction_format,
            "reflection": reflection_obj,
            "bullet_tags": bullet_tags,
        })

        _unsafe_playbook, _unsafe_next_id, operations, _ = curator.curate(
            current_playbook=previous_playbook,
            recent_reflection=reflection,
            question_context=build_question_context(
                item,
                gold_field,
                run_note=(
                    "This is an offline ACE warmup run. Final playbook rules must be "
                    "usable at inference time and must not mention gold/reference targets."
                ),
            ),
            current_step=idx,
            total_samples=len(selected),
            token_budget=token_budget,
            playbook_stats=get_playbook_stats(previous_playbook),
            use_ground_truth=True,
            use_json_mode=True,
            call_id=f"offline_curate_{idx:04d}",
            log_dir=str(out_dir / "llm_logs"),
            next_global_id=previous_next_id,
        )

        safe_operations, rejected_operations = filter_safe_operations(
            operations,
            family=family,
            prediction_format=prediction_format,
        )

        updated_playbook, next_id = apply_curator_operations(
            previous_playbook,
            safe_operations,
            previous_next_id,
        )

        playbooks[key] = updated_playbook
        next_ids[key] = next_id

        all_operations.append({
            "idx": idx,
            "id": item.get("id"),
            "family": family,
            "prediction_format": prediction_format,
            "operations": safe_operations,
        })

        if rejected_operations:
            all_rejected_operations.append({
                "idx": idx,
                "id": item.get("id"),
                "family": family,
                "prediction_format": prediction_format,
                "rejected_operations": rejected_operations,
            })

    run_playbook_dir = out_dir / "playbooks"
    run_playbook_dir.mkdir(parents=True, exist_ok=True)

    written_playbooks: list[str] = []
    published_playbooks: list[str] = []

    for (family, prediction_format), playbook_text in playbooks.items():
        run_path = run_playbook_dir / f"{family}__{prediction_format}.txt"
        run_path.write_text(playbook_text, encoding="utf-8")
        written_playbooks.append(str(run_path))

        if publish_playbooks:
            publish_path = playbook_output_path(
                playbook_dir,
                generator_model_key=generator_model_key,
                family=family,
                prediction_format=prediction_format,
            )
            publish_path.parent.mkdir(parents=True, exist_ok=True)
            publish_path.write_text(playbook_text, encoding="utf-8")
            published_playbooks.append(str(publish_path))

    summary = {
        "raw_path": str(raw_path),
        "generator_model_key": generator_model_key,
        "total_items_in_raw": len(items),
        "selected_items": len(selected),
        "include_correct": include_correct,
        "limit": limit,
        "operation_count": sum(len(x["operations"]) for x in all_operations),
        "rejected_operation_count": sum(
            len(x["rejected_operations"]) for x in all_rejected_operations
        ),
        "written_playbooks": written_playbooks,
        "published_playbooks": published_playbooks,
    }

    (out_dir / "reflections.json").write_text(compact_json(all_reflections), encoding="utf-8")
    (out_dir / "operations.json").write_text(compact_json(all_operations), encoding="utf-8")
    (out_dir / "rejected_operations.json").write_text(
        compact_json(all_rejected_operations),
        encoding="utf-8",
    )
    (out_dir / "summary.json").write_text(compact_json(summary), encoding="utf-8")

    return summary
