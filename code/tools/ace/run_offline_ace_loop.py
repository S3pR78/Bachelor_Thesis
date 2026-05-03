from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from src.ace.offline_loop import (
    ensure_no_test_adaptation,
    find_latest_benchmark_raw,
    run_trace_reflect_curate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run offline ACE adaptation loop on train/validation benchmark runs."
    )

    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--prompt-mode", required=True)
    parser.add_argument("--playbook", required=True)
    parser.add_argument("--ace-mode", required=True, choices=["pgmr_lite", "direct_sparql", "any"])
    parser.add_argument("--family", default=None)
    parser.add_argument("--split", default=None)

    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)

    parser.add_argument("--prediction-format", default=None)
    parser.add_argument("--pgmr-memory-dir", default=None)
    parser.add_argument("--sparql-endpoint", default=None)

    parser.add_argument("--ace-max-bullets", type=int, default=5)
    parser.add_argument("--min-support", type=int, default=1)
    parser.add_argument("--min-priority", type=int, default=0)
    parser.add_argument("--max-deltas", type=int, default=None)
    parser.add_argument("--max-evidence-items", type=int, default=5)

    parser.add_argument(
        "--outputs-root",
        default="code/outputs/evaluation_runs",
        help="Root folder where evaluate writes benchmark_raw.json files.",
    )
    parser.add_argument(
        "--dry-run-curation",
        action="store_true",
        help="Run evaluation/reflection but do not write playbook updates.",
    )
    parser.add_argument(
        "--allow-test-adaptation",
        action="store_true",
        help="Allow adapting on test data. Do not use this for thesis results.",
    )

    return parser.parse_args()


def build_evaluate_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "code/src/main.py",
        "evaluate",
        "--model",
        args.model,
        "--dataset",
        args.dataset,
        "--prompt-mode",
        args.prompt_mode,
        "--ace-playbook",
        args.playbook,
        "--ace-mode",
        args.ace_mode,
        "--ace-max-bullets",
        str(args.ace_max_bullets),
    ]

    if args.limit is not None:
        command += ["--limit", str(args.limit)]

    if args.prediction_format:
        command += ["--prediction-format", args.prediction_format]

    if args.pgmr_memory_dir:
        command += ["--pgmr-memory-dir", args.pgmr_memory_dir]

    if args.sparql_endpoint:
        command += ["--sparql-endpoint", args.sparql_endpoint]

    return command


def run_command(command: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = "code"

    print("Running evaluation command:")
    print(" ".join(command))
    print("=" * 80)

    subprocess.run(command, check=True, env=env)


def print_iteration_summary(summary: dict) -> None:
    print()
    print("ACE iteration summary")
    print("=" * 80)
    print(f"raw:             {summary['raw_path']}")
    print(f"traces:          {summary['trace_path']}")
    print(f"deltas:          {summary['delta_path']}")
    print(f"playbook:        {summary['playbook_path']}")
    print(f"trace count:     {summary['trace_count']}")
    print(f"error traces:    {summary['error_trace_count']}")
    print(f"deltas:          {summary['delta_count']}")
    print()

    print("Category counts")
    print("-" * 80)
    for category, count in summary["category_counts"].items():
        print(f"{category:35s} {count}")

    print()
    print("Curation")
    print("-" * 80)
    curation = summary["curation"]
    print(f"before bullets:   {curation['before_bullet_count']}")
    print(f"after bullets:    {curation['after_bullet_count']}")
    print(f"applied deltas:   {curation['applied_delta_count']}")
    print(f"skipped deltas:   {curation['skipped_delta_count']}")


def main() -> None:
    args = parse_args()

    ensure_no_test_adaptation(
        dataset_path=args.dataset,
        allow_test_adaptation=args.allow_test_adaptation,
    )

    for iteration in range(1, args.iterations + 1):
        print()
        print(f"Offline ACE iteration {iteration}/{args.iterations}")
        print("=" * 80)

        started_at = time.time()
        command = build_evaluate_command(args)
        run_command(command)

        raw_path = find_latest_benchmark_raw(
            outputs_root=args.outputs_root,
            started_after_epoch=started_at,
        )

        summary = run_trace_reflect_curate(
            raw_path=raw_path,
            playbook_path=args.playbook,
            mode=args.ace_mode,
            family=args.family,
            split=args.split,
            min_support=args.min_support,
            max_evidence_items=args.max_evidence_items,
            min_priority=args.min_priority,
            max_deltas=args.max_deltas,
            dry_run=args.dry_run_curation,
        )

        print_iteration_summary(summary)


if __name__ == "__main__":
    main()
