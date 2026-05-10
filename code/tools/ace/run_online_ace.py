from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ace.core.reflector import Reflector
from ace.core.curator import Curator
from ace.orkg.adapter import compact_json
from ace.orkg.online import run_online_ace, SUPPORTED_ONLINE_MODES
from ace.llm import AceLlmSessionCache, ace_client_to_inference_session
from src.utils.config_loader import load_json_config, get_model_entry


def resolve_model_entry(config_path: str, model_key: str) -> dict[str, Any]:
    full_config = load_json_config(config_path)
    return get_model_entry(full_config, model_key)


def get_provider(model_config: dict[str, Any]) -> str:
    return str(model_config.get("provider", "")).strip().lower()


def get_model_id(model_config: dict[str, Any], *, model_key: str) -> str:
    return str(model_config.get("model_id") or model_key)


def get_max_tokens(
    model_config: dict[str, Any],
    *,
    cli_max_tokens: int | None,
    default: int = 1024,
) -> int:
    if cli_max_tokens is not None:
        return cli_max_tokens

    generation = model_config.get("generation", {})
    value = (
        generation.get("max_output_tokens")
        or generation.get("max_new_tokens")
        or model_config.get("max_tokens")
        or default
    )
    return int(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ORKG Online ACE.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--generator-model-key", required=True)
    parser.add_argument("--prompt-mode", required=True)
    parser.add_argument("--prediction-format", required=True, choices=["pgmr_lite", "sparql"])
    parser.add_argument(
        "--online-mode",
        required=True,
        choices=sorted(SUPPORTED_ONLINE_MODES),
        help=(
            "playbook_refinement uses supervised ace_playbook feedback and may persist helpful rules; "
            "test_time_repair uses non-gold diagnostics and does not carry rules across benchmark items."
        ),
    )
    parser.add_argument("--initial-playbook-dir", default="code/data/ace_playbooks")
    parser.add_argument("--out-dir", required=True)

    parser.add_argument("--planner-model-key", default="gpt_4o_mini")
    parser.add_argument("--reflector-model-key", default="gpt_4o_mini")
    parser.add_argument("--curator-model-key", default="gpt_4o_mini")
    parser.add_argument("--model-config", default="code/config/model_config.json")

    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--top-k-rules", type=int, default=8)
    parser.add_argument("--ace-max-bullets", type=int, default=-1)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--sparql-endpoint", default="https://www.orkg.org/triplestore")
    parser.add_argument("--pgmr-memory-dir", default="code/data/orkg_memory/templates")
    parser.add_argument("--pgmr-similarity-mapping", action="store_true", default=True)
    parser.add_argument("--no-pgmr-similarity-mapping", dest="pgmr_similarity_mapping", action="store_false")
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--publish-final-playbooks", action="store_true")

    # Cost guard.
    parser.add_argument("--allow-api-calls", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    planner_config = resolve_model_entry(args.model_config, args.planner_model_key)
    reflector_config = resolve_model_entry(args.model_config, args.reflector_model_key)
    curator_config = resolve_model_entry(args.model_config, args.curator_model_key)

    planner_provider = get_provider(planner_config)
    reflector_provider = get_provider(reflector_config)
    curator_provider = get_provider(curator_config)

    planner_model_id = get_model_id(planner_config, model_key=args.planner_model_key)
    reflector_model_id = get_model_id(reflector_config, model_key=args.reflector_model_key)
    curator_model_id = get_model_id(curator_config, model_key=args.curator_model_key)

    planner_max_tokens = get_max_tokens(planner_config, cli_max_tokens=args.max_tokens)
    reflector_max_tokens = get_max_tokens(reflector_config, cli_max_tokens=args.max_tokens)
    curator_max_tokens = get_max_tokens(curator_config, cli_max_tokens=args.max_tokens)

    planned = {
        "dataset": args.dataset,
        "generator_model_key": args.generator_model_key,
        "prompt_mode": args.prompt_mode,
        "prediction_format": args.prediction_format,
        "online_mode": args.online_mode,
        "limit": args.limit,
        "planner_model_key": args.planner_model_key,
        "planner_model_id": planner_model_id,
        "planner_provider": planner_provider,
        "reflector_model_key": args.reflector_model_key,
        "reflector_model_id": reflector_model_id,
        "reflector_provider": reflector_provider,
        "curator_model_key": args.curator_model_key,
        "curator_model_id": curator_model_id,
        "curator_provider": curator_provider,
        "top_k_rules": args.top_k_rules,
        "max_attempts": args.max_attempts,
        "out_dir": args.out_dir,
        "initial_playbook_dir": args.initial_playbook_dir,
        "ace_max_bullets": args.ace_max_bullets,
        "publish_final_playbooks": args.publish_final_playbooks,
    }

    print("Planned online ACE run:")
    print(compact_json(planned))

    if not args.allow_api_calls:
        print()
        print("DRY RUN ONLY: no API calls and no evaluations were run.")
        print("Add --allow-api-calls to run Online ACE.")
        return 0

    llm_cache = AceLlmSessionCache(model_config_path=args.model_config)
    planner_client = llm_cache.get(args.planner_model_key)
    reflector_client = llm_cache.get(args.reflector_model_key)
    curator_client = llm_cache.get(args.curator_model_key)
    generator_client = llm_cache.get(args.generator_model_key)
    generator_inference_session = ace_client_to_inference_session(
        generator_client,
        model_key=args.generator_model_key,
    )

    reflector = Reflector(
        reflector_client,
        reflector_provider,
        reflector_model_id,
        max_tokens=reflector_max_tokens,
    )
    curator = Curator(
        curator_client,
        curator_provider,
        curator_model_id,
        max_tokens=curator_max_tokens,
    )

    summary = run_online_ace(
        dataset_path=Path(args.dataset),
        generator_model_key=args.generator_model_key,
        prompt_mode=args.prompt_mode,
        prediction_format=args.prediction_format,
        planner_client=planner_client,
        planner_provider=planner_provider,
        planner_model=planner_model_id,
        planner_max_tokens=planner_max_tokens,
        reflector=reflector,
        curator=curator,
        initial_playbook_dir=Path(args.initial_playbook_dir),
        out_dir=Path(args.out_dir),
        online_mode=args.online_mode,
        limit=args.limit,
        top_k_rules=args.top_k_rules,
        ace_max_bullets=args.ace_max_bullets,
        max_attempts=args.max_attempts,
        sparql_endpoint=args.sparql_endpoint,
        pgmr_memory_dir=args.pgmr_memory_dir,
        pgmr_similarity_mapping=args.pgmr_similarity_mapping,
        publish_final_playbooks=args.publish_final_playbooks,
        generator_inference_session=generator_inference_session,
    )

    print()
    print("Online ACE summary:")
    print(compact_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
