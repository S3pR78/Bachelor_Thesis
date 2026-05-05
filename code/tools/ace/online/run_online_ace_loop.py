"""Thin CLI wrapper for the online ACE loop."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.ace.online.loop import OnlineAceConfig, run_online_ace_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the true per-question online ACE loop."
    )
    parser.add_argument("--model", required=True, help="Model key to generate queries.")
    parser.add_argument("--dataset", required=True, type=Path, help="Dataset JSON path.")
    parser.add_argument("--prompt-mode", required=True, help="Prompt mode to use.")
    parser.add_argument(
        "--prediction-format",
        required=True,
        help="Prediction format, e.g. pgmr_lite or sparql.",
    )
    parser.add_argument(
        "--sparql-endpoint",
        required=True,
        help="SPARQL endpoint used by the later evaluation step.",
    )
    parser.add_argument(
        "--initial-playbook",
        required=True,
        type=Path,
        help="Initial online ACE playbook JSON path. This path is not overwritten.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where online ACE outputs will be written in later steps.",
    )
    parser.add_argument(
        "--family",
        default=None,
        help="Optional dataset family filter, e.g. nlp4re.",
    )
    parser.add_argument(
        "--pgmr-memory-dir",
        default=None,
        type=Path,
        help="Optional PGMR memory directory for later PGMR restoration.",
    )
    parser.add_argument(
        "--iterations",
        default=3,
        type=int,
        help="Maximum attempts per item.",
    )
    parser.add_argument(
        "--limit",
        default=None,
        type=int,
        help="Optional item limit after filtering and shuffling.",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle selected dataset items with --sample-seed.",
    )
    parser.add_argument(
        "--sample-seed",
        default=42,
        type=int,
        help="Deterministic shuffle seed.",
    )
    parser.add_argument(
        "--reflect-model",
        default="gpt_4o_mini",
        help="LLM model key for reflection.",
    )
    parser.add_argument(
        "--ace-max-bullets",
        default=3,
        type=int,
        help="Maximum enabled context rules to include in prompts.",
    )
    parser.add_argument(
        "--disable-harmful-rules",
        action="store_true",
        help="Disable rules once they reach --min-harmful-count.",
    )
    parser.add_argument(
        "--delete-harmful-rules",
        action="store_true",
        help="Delete harmful rules from active context in later steps.",
    )
    parser.add_argument(
        "--min-harmful-count",
        default=2,
        type=int,
        help="Harmful count threshold for disabling or deleting rules.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print parsed configuration and exit without running online ACE.",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> OnlineAceConfig:
    return OnlineAceConfig(
        model=args.model,
        dataset=args.dataset,
        prompt_mode=args.prompt_mode,
        prediction_format=args.prediction_format,
        sparql_endpoint=args.sparql_endpoint,
        initial_playbook=args.initial_playbook,
        output_dir=args.output_dir,
        family=args.family,
        pgmr_memory_dir=args.pgmr_memory_dir,
        iterations=args.iterations,
        limit=args.limit,
        shuffle=args.shuffle,
        sample_seed=args.sample_seed,
        reflect_model=args.reflect_model,
        ace_max_bullets=args.ace_max_bullets,
        disable_harmful_rules=args.disable_harmful_rules,
        delete_harmful_rules=args.delete_harmful_rules,
        min_harmful_count=args.min_harmful_count,
        dry_run=args.dry_run,
    )


def main() -> int:
    config = build_config(parse_args())
    try:
        return run_online_ace_loop(config)
    except NotImplementedError as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

