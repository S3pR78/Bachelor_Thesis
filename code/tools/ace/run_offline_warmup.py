from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ace.core.reflector import Reflector
from ace.core.curator import Curator
from ace.orkg.offline import load_raw_items, select_items, run_offline_warmup
from ace.orkg.adapter import compact_json
from ace.llm import (
    get_max_tokens_from_model_config,
    get_model_id,
    normalize_provider,
    resolve_ace_llm_client,
)
from src.utils.config_loader import load_json_config, get_model_entry


def resolve_model_entry(config_path: str, model_key: str) -> dict[str, Any]:
    full_config = load_json_config(config_path)
    return get_model_entry(full_config, model_key)


def get_provider(model_config: dict[str, Any]) -> str:
    return normalize_provider(model_config.get("provider"))


def get_max_tokens(
    model_config: dict[str, Any],
    *,
    cli_max_tokens: int | None,
    default: int = 900,
) -> int:
    if cli_max_tokens is not None:
        return cli_max_tokens

    return get_max_tokens_from_model_config(model_config, default=default)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ORKG ACE offline warmup from an evaluated benchmark_raw.json file."
    )

    parser.add_argument("--raw-path", required=True, help="Path to benchmark_raw.json.")
    parser.add_argument("--generator-model-key", required=True)
    parser.add_argument("--reflector-model-key", required=True)
    parser.add_argument("--curator-model-key", required=True)
    parser.add_argument("--model-config", default="code/config/model_config.json")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--playbook-dir", default="code/data/ace_playbooks")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-correct", action="store_true")
    parser.add_argument("--token-budget", type=int, default=4000)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--no-publish-playbooks", action="store_true")

    # Cost guard: by default, only print planned work. API calls require opt-in.
    parser.add_argument(
        "--allow-api-calls",
        action="store_true",
        help="Actually call Reflector/Curator APIs. Without this, only a dry-run summary is printed.",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    raw_path = Path(args.raw_path)
    out_dir = Path(args.out_dir)
    playbook_dir = Path(args.playbook_dir)

    reflector_config = resolve_model_entry(args.model_config, args.reflector_model_key)
    curator_config = resolve_model_entry(args.model_config, args.curator_model_key)

    reflector_provider = get_provider(reflector_config)
    curator_provider = get_provider(curator_config)

    reflector_model_id = get_model_id(reflector_config, model_key=args.reflector_model_key)
    curator_model_id = get_model_id(curator_config, model_key=args.curator_model_key)

    reflector_max_tokens = get_max_tokens(
        reflector_config,
        cli_max_tokens=args.max_tokens,
    )
    curator_max_tokens = get_max_tokens(
        curator_config,
        cli_max_tokens=args.max_tokens,
    )
    max_tokens = min(reflector_max_tokens, curator_max_tokens)

    raw_items = load_raw_items(raw_path)
    selected = select_items(
        raw_items,
        limit=args.limit,
        include_correct=args.include_correct,
    )

    planned = {
        "raw_path": str(raw_path),
        "generator_model_key": args.generator_model_key,
        "reflector_model_key": args.reflector_model_key,
        "reflector_model_id": reflector_model_id,
        "reflector_provider": reflector_provider,
        "curator_model_key": args.curator_model_key,
        "curator_model_id": curator_model_id,
        "curator_provider": curator_provider,
        "selected_items": len(selected),
        "estimated_llm_calls": len(selected) * 2,
        "limit": args.limit,
        "include_correct": args.include_correct,
        "out_dir": str(out_dir),
        "playbook_dir": str(playbook_dir),
        "publish_playbooks": not args.no_publish_playbooks,
        "max_tokens": max_tokens,
    }

    print("Planned offline ACE warmup:")
    print(compact_json(planned))

    if not args.allow_api_calls:
        print()
        print("DRY RUN ONLY: no LLM calls were made.")
        print("Add --allow-api-calls to run Reflector/Curator.")
        return 0

    llm_cache = {}
    reflector_client = resolve_ace_llm_client(
        args.model_config,
        args.reflector_model_key,
        cache=llm_cache,
    )
    curator_client = resolve_ace_llm_client(
        args.model_config,
        args.curator_model_key,
        cache=llm_cache,
    )

    reflector = Reflector(
        reflector_client,
        reflector_client.provider,
        reflector_client.model_id,
        max_tokens=max_tokens,
    )
    curator = Curator(
        curator_client,
        curator_client.provider,
        curator_client.model_id,
        max_tokens=max_tokens,
    )

    summary = run_offline_warmup(
        raw_path=raw_path,
        generator_model_key=args.generator_model_key,
        reflector=reflector,
        curator=curator,
        out_dir=out_dir,
        playbook_dir=playbook_dir,
        limit=args.limit,
        include_correct=args.include_correct,
        token_budget=args.token_budget,
        publish_playbooks=not args.no_publish_playbooks,
    )

    print()
    print("Offline ACE warmup summary:")
    print(compact_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
