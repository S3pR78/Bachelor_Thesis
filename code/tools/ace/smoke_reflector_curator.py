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
)
from ace.utils import initialize_clients


def normalize_scope(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def select_gold_target(trace: dict[str, Any]) -> tuple[str, str]:
    prediction_format = normalize_scope(trace.get("prediction_format"))

    if prediction_format == "pgmr_lite":
        return (
            trace.get("gold_pgmr_sparql")
            or trace.get("gold_target_query")
            or "",
            "gold_pgmr_sparql",
        )

    return (
        trace.get("gold_query")
        or trace.get("gold_sparql")
        or trace.get("gold_target_query")
        or "",
        "gold_query",
    )


def compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_reasoning_trace(trace: dict[str, Any]) -> str:
    fields = {
        "family": trace.get("family"),
        "prediction_format": trace.get("prediction_format"),
        "prompt_mode": trace.get("prompt_mode"),
        "raw_model_output": trace.get("raw_model_output"),
        "extracted_query": trace.get("extracted_query"),
        "postprocessed_query": trace.get("postprocessed_query"),
        "executed_query": trace.get("executed_query"),
        "query_extracted": trace.get("query_extracted"),
        "extraction_status": trace.get("extraction_status"),
        "postprocessing_status": trace.get("postprocessing_status"),
    }
    return compact_json({k: v for k, v in fields.items() if v not in (None, "", [])})


def build_predicted_answer(trace: dict[str, Any]) -> str:
    fields = {
        "extracted_query": trace.get("extracted_query"),
        "postprocessed_query": trace.get("postprocessed_query"),
        "executed_query": trace.get("executed_query"),
        "prediction_result": trace.get("prediction_result"),
    }
    return compact_json({k: v for k, v in fields.items() if v not in (None, "", [])})


def build_environment_feedback(trace: dict[str, Any]) -> str:
    fields = {
        "main_issue": trace.get("main_issue"),
        "diagnostic_hint": trace.get("diagnostic_hint"),
        "prediction_execution_success": trace.get("prediction_execution_success"),
        "answer_exact_match": trace.get("answer_exact_match"),
        "answer_cell_value_f1": trace.get("answer_cell_value_f1"),
        "kg_ref_f1": trace.get("kg_ref_f1"),
        "predicate_ref_f1": trace.get("predicate_ref_f1"),
        "class_ref_f1": trace.get("class_ref_f1"),
        "resource_ref_f1": trace.get("resource_ref_f1"),
        "execution_error": trace.get("execution_error"),
    }
    return compact_json({k: v for k, v in fields.items() if v not in (None, "", [])})


def build_question_context(trace: dict[str, Any], gold_field: str) -> str:
    fields = {
        "id": trace.get("id"),
        "family": trace.get("family"),
        "prediction_format": trace.get("prediction_format"),
        "prompt_mode": trace.get("prompt_mode"),
        "main_issue": trace.get("main_issue"),
        "gold_target_field_used_for_reflection": gold_field,
        "note": (
            "Final playbook rules must be inference-time usable and must not mention "
            "gold/reference queries. For PGMR-lite, rules must not use real ORKG IDs."
        ),
    }
    return compact_json({k: v for k, v in fields.items() if v not in (None, "", [])})


def main() -> None:
    trace_path = Path(os.environ.get("TRACE_PATH", "/tmp/ace_reflector_curator_smoke/mini_trace.json"))
    out_dir = Path(os.environ.get("OUT_DIR", "/tmp/ace_reflector_curator_smoke"))
    out_dir.mkdir(parents=True, exist_ok=True)

    if not trace_path.exists():
        raise FileNotFoundError(
            f"Trace file not found: {trace_path}\n"
            "Create /tmp/ace_reflector_curator_smoke/mini_trace.json first or set TRACE_PATH."
        )

    api_provider = os.environ.get("ACE_API_PROVIDER", "openai")
    reflector_model = os.environ.get("ACE_REFLECTOR_MODEL", "gpt-4o-mini")
    curator_model = os.environ.get("ACE_CURATOR_MODEL", "gpt-4o-mini")
    max_tokens = int(os.environ.get("ACE_MAX_TOKENS", "900"))

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    gold_target, gold_field = select_gold_target(trace)

    current_playbook = """## STRATEGIES & INSIGHTS

## COMMON MISTAKES TO AVOID

## OTHERS"""

    bullets_used = extract_playbook_bullets(current_playbook, [])

    question = trace.get("question") or ""
    reasoning_trace = build_reasoning_trace(trace)
    predicted_answer = build_predicted_answer(trace)
    environment_feedback = build_environment_feedback(trace)
    question_context = build_question_context(trace, gold_field)

    generator_client, reflector_client, curator_client = initialize_clients(api_provider)

    reflector = Reflector(
        reflector_client,
        api_provider,
        reflector_model,
        max_tokens=max_tokens,
    )
    curator = Curator(
        curator_client,
        api_provider,
        curator_model,
        max_tokens=max_tokens,
    )

    reflection, bullet_tags, _ = reflector.reflect(
        question=question,
        reasoning_trace=reasoning_trace,
        predicted_answer=predicted_answer,
        ground_truth=gold_target,
        environment_feedback=environment_feedback,
        bullets_used=bullets_used,
        use_ground_truth=True,
        use_json_mode=True,
        call_id="smoke_reflect",
        log_dir=str(out_dir),
    )

    (out_dir / "reflection.json").write_text(reflection, encoding="utf-8")
    (out_dir / "bullet_tags.json").write_text(
        compact_json(bullet_tags),
        encoding="utf-8",
    )

    updated_playbook, next_id, operations, _ = curator.curate(
        current_playbook=current_playbook,
        recent_reflection=reflection,
        question_context=question_context,
        current_step=1,
        total_samples=1,
        token_budget=4000,
        playbook_stats=get_playbook_stats(current_playbook),
        use_ground_truth=True,
        use_json_mode=True,
        call_id="smoke_curate",
        log_dir=str(out_dir),
        next_global_id=get_next_global_id(current_playbook),
    )

    (out_dir / "curator_operations.json").write_text(
        compact_json(operations),
        encoding="utf-8",
    )
    (out_dir / "updated_playbook.txt").write_text(
        updated_playbook,
        encoding="utf-8",
    )

    print("Wrote:")
    print(f"- {out_dir / 'reflection.json'}")
    print(f"- {out_dir / 'curator_operations.json'}")
    print(f"- {out_dir / 'updated_playbook.txt'}")
    print()
    print("Operations:")
    print(compact_json(operations))
    print()
    print("Updated playbook:")
    print(updated_playbook)


if __name__ == "__main__":
    main()
