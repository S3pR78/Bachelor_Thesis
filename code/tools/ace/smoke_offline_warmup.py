from __future__ import annotations

import json
import os
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
from ace.utils import initialize_clients
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


def load_items(raw_path: Path) -> list[dict[str, Any]]:
    data = json.loads(raw_path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    for key in ("results", "items", "examples", "raw_results"):
        if isinstance(data.get(key), list):
            return data[key]

    raise ValueError(f"Could not find item list in {raw_path}")


def empty_playbook() -> str:
    return """## STRATEGIES & INSIGHTS

## COMMON MISTAKES TO AVOID

## OTHERS"""


def main() -> None:
    raw_path = Path(os.environ["RAW_PATH"])
    out_dir = Path(os.environ.get("OUT_DIR", "code/outputs/ace_smoke/offline_warmup"))
    limit = int(os.environ.get("LIMIT", "3"))
    out_dir.mkdir(parents=True, exist_ok=True)

    api_provider = os.environ.get("ACE_API_PROVIDER", "openai")
    reflector_model = os.environ.get("ACE_REFLECTOR_MODEL", "gpt-4o-mini")
    curator_model = os.environ.get("ACE_CURATOR_MODEL", "gpt-4o-mini")
    max_tokens = int(os.environ.get("ACE_MAX_TOKENS", "900"))

    _, reflector_client, curator_client = initialize_clients(api_provider)
    reflector = Reflector(reflector_client, api_provider, reflector_model, max_tokens=max_tokens)
    curator = Curator(curator_client, api_provider, curator_model, max_tokens=max_tokens)

    items = load_items(raw_path)
    selected = [
        item for item in items
        if get_validation_metric(item, "answer_exact_match") is not True
    ][:limit]

    playbooks: dict[tuple[str, str], str] = {}
    next_ids: dict[tuple[str, str], int] = {}
    all_operations = []
    all_rejected_operations = []
    all_reflections = []

    for idx, item in enumerate(selected, start=1):
        family = get_family(item)
        prediction_format = get_prediction_format(item)
        key = (family, prediction_format)

        if key not in playbooks:
            playbooks[key] = empty_playbook()
            next_ids[key] = get_next_global_id(playbooks[key])

        gold, gold_field = select_gold_target(item)
        bullets_used = extract_playbook_bullets(playbooks[key], [])

        reflection, bullet_tags, _ = reflector.reflect(
            question=item.get("question") or "",
            reasoning_trace=build_reasoning_trace(item),
            predicted_answer=build_predicted_answer(item),
            ground_truth=gold,
            environment_feedback=build_environment_feedback(item),
            bullets_used=bullets_used,
            use_ground_truth=True,
            use_json_mode=True,
            call_id=f"smoke_reflect_{idx:03d}",
            log_dir=str(out_dir),
        )

        try:
            reflection_obj = json.loads(reflection)
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

        previous_playbook = playbooks[key]
        previous_next_id = next_ids[key]

        _updated_playbook, _next_id, operations, _ = curator.curate(
            current_playbook=previous_playbook,
            recent_reflection=reflection,
            question_context=build_question_context(item, gold_field),
            current_step=idx,
            total_samples=len(selected),
            token_budget=4000,
            playbook_stats=get_playbook_stats(previous_playbook),
            use_ground_truth=True,
            use_json_mode=True,
            call_id=f"smoke_curate_{idx:03d}",
            log_dir=str(out_dir),
            next_global_id=previous_next_id,
        )

        safe_operations, rejected_operations = filter_safe_operations(
            operations,
            family=family,
            prediction_format=prediction_format,
        )

        if rejected_operations:
            print(
                f"Safety rejected {len(rejected_operations)} curator operation(s) "
                f"for id={item.get('id')} family={family} format={prediction_format}"
            )
            for rejected in rejected_operations:
                print(
                    "  -",
                    rejected.get("safety_rejection_reason"),
                    "::",
                    rejected.get("content", rejected),
                )

        # Rebuild from the previous playbook using only safe operations. This keeps
        # the upstream-style Curator unchanged while ensuring final smoke outputs
        # do not contain unsafe playbook rules.
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

    (out_dir / "reflections.json").write_text(compact_json(all_reflections), encoding="utf-8")
    (out_dir / "operations.json").write_text(compact_json(all_operations), encoding="utf-8")
    (out_dir / "rejected_operations.json").write_text(
        compact_json(all_rejected_operations),
        encoding="utf-8",
    )

    playbook_dir = out_dir / "playbooks"
    playbook_dir.mkdir(exist_ok=True)

    for (family, prediction_format), text in playbooks.items():
        path = playbook_dir / f"{family}__{prediction_format}.txt"
        path.write_text(text, encoding="utf-8")

    print(f"Wrote smoke outputs to {out_dir}")
    print()
    print("Operations:")
    print(compact_json(all_operations))
    print()
    print("Rejected operations:")
    print(compact_json(all_rejected_operations))
    print()
    print("Playbooks:")

    for path in sorted(playbook_dir.glob("*.txt")):
        print(f"\n=== {path.name} ===")
        print(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
