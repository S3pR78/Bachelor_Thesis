from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ace.orkg.adapter import compact_json
from ace.orkg.planner import plan_question_with_llm
from ace.orkg.rule_retrieval import (
    load_playbook_rules,
    select_top_k_rules,
    render_selected_rules_block,
)
from ace.orkg.offline import playbook_output_path
from ace.llm import prepare_ace_llm_client
from src.utils.config_loader import load_json_config, get_model_entry


def get_model_config(config_path: str, model_key: str) -> dict[str, Any]:
    config = load_json_config(config_path)
    return get_model_entry(config, model_key)


def get_max_tokens(model_config: dict[str, Any], cli_max_tokens: int | None, default: int = 1024) -> int:
    if cli_max_tokens is not None:
        return cli_max_tokens
    generation = model_config.get("generation", {})
    return int(
        generation.get("max_output_tokens")
        or generation.get("max_new_tokens")
        or model_config.get("max_tokens")
        or default
    )


def prepare_client_compat(*, model_key: str, model_config_path: str):
    """Call prepare_ace_llm_client with a tolerant signature.

    This keeps the smoke tool compatible with the current ACE LLM refactor while
    avoiding assumptions about the exact helper signature.
    """
    try:
        return prepare_ace_llm_client(
            model_key=model_key,
            model_config_path=model_config_path,
        )
    except TypeError:
        try:
            return prepare_ace_llm_client(model_key, model_config_path)
        except TypeError:
            model_config = get_model_config(model_config_path, model_key)
            return prepare_ace_llm_client(model_config)


def infer_family_from_dataset_item(item: dict[str, Any]) -> str:
    return (
        item.get("family")
        or item.get("entry_metadata", {}).get("family")
        or item.get("metadata", {}).get("family")
        or "unknown_family"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke test ORKG ACE planning and top-k rule retrieval.")
    parser.add_argument("--question", default=None)
    parser.add_argument("--family", default=None, choices=["nlp4re", "empirical_research_practice", None])
    parser.add_argument("--prediction-format", required=True, choices=["pgmr_lite", "sparql"])
    parser.add_argument("--dataset", default=None, help="Optional dataset JSON list; uses first item if question/family omitted.")
    parser.add_argument("--item-index", type=int, default=0)
    parser.add_argument("--generator-model-key", required=True)
    parser.add_argument("--planner-model-key", default="gpt_4o_mini")
    parser.add_argument("--model-config", default="code/config/model_config.json")
    parser.add_argument("--playbook-dir", default="code/data/ace_playbooks")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--out-dir", default="code/outputs/ace_smoke/plan_and_retrieve")
    parser.add_argument("--allow-api-calls", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    question = args.question
    family = args.family

    if args.dataset:
        data = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
        item = data[args.item_index]
        question = question or item.get("question")
        family = family or infer_family_from_dataset_item(item)

    if not question or not family:
        raise ValueError("Provide --question and --family, or provide --dataset with a valid item.")

    playbook_path = playbook_output_path(
        Path(args.playbook_dir),
        generator_model_key=args.generator_model_key,
        family=family,
        prediction_format=args.prediction_format,
    )

    rules = load_playbook_rules(playbook_path)

    planned = {
        "question": question,
        "family": family,
        "prediction_format": args.prediction_format,
        "playbook_path": str(playbook_path),
        "rule_count": len(rules),
        "planner_model_key": args.planner_model_key,
        "top_k": args.top_k,
    }

    print("Planned planner/retrieval smoke:")
    print(compact_json(planned))

    if not args.allow_api_calls:
        print()
        print("DRY RUN ONLY: no planner LLM call was made.")
        print("Add --allow-api-calls to generate a plan and retrieve rules.")
        return 0

    model_config = get_model_config(args.model_config, args.planner_model_key)
    max_tokens = get_max_tokens(model_config, args.max_tokens)

    client = prepare_client_compat(
        model_key=args.planner_model_key,
        model_config_path=args.model_config,
    )
    provider = str(model_config.get("provider") or "").strip().lower()
    model_id = str(model_config.get("model_id") or args.planner_model_key)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plan, call_info = plan_question_with_llm(
        question=question,
        family=family,
        prediction_format=args.prediction_format,
        api_client=client,
        api_provider=provider,
        model=model_id,
        max_tokens=max_tokens,
        call_id="smoke_plan",
        log_dir=str(out_dir / "llm_logs"),
    )

    selected_rules = select_top_k_rules(
        question=question,
        plan=plan,
        rules=rules,
        top_k=args.top_k,
    )

    output = {
        "question": question,
        "family": family,
        "prediction_format": args.prediction_format,
        "plan": plan,
        "selected_rules": selected_rules,
        "call_info": call_info,
    }

    (out_dir / "plan_and_rules.json").write_text(compact_json(output), encoding="utf-8")

    print()
    print("Plan:")
    print(compact_json(plan))
    print()
    print(render_selected_rules_block(selected_rules))
    print()
    print("Wrote:", out_dir / "plan_and_rules.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
