"""Run the post-hoc LLM judge for multiple benchmark output folders."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = CODE_ROOT.parent
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from tools.evaluate.run_llm_judge import EXPLICIT_PREDICTION_FIELDS, run_llm_judge  # noqa: E402


# Top-level folders below code/outputs/evaluation_runs that should be skipped.
EXCLUDED_FOLDERS = {
    "t5_base",
}


def _is_excluded(raw_path: Path, runs_root: Path) -> bool:
    try:
        relative = raw_path.relative_to(runs_root)
    except ValueError:
        return False

    if not relative.parts:
        return False

    return relative.parts[0] in EXCLUDED_FOLDERS


def find_benchmark_raw_files(runs_root: Path) -> list[Path]:
    """Find benchmark_raw.json files, excluding configured top-level folders."""
    return [
        path
        for path in sorted(runs_root.glob("**/benchmark_raw.json"))
        if not _is_excluded(path, runs_root)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run code/tools/evaluate/run_llm_judge.py over all benchmark_raw.json "
            "files below an evaluation-runs directory."
        )
    )
    parser.add_argument(
        "--runs-root",
        default=str(REPO_ROOT / "code" / "outputs" / "evaluation_runs"),
        help="Root directory containing model/run subfolders.",
    )
    parser.add_argument(
        "--judge-model",
        default="gpt_4o_mini",
        help="OpenAI model config key or model id for judging.",
    )
    parser.add_argument(
        "--prediction-field",
        default="auto",
        choices=EXPLICIT_PREDICTION_FIELDS,
        help="Prediction query field to judge. Auto prefers restored queries.",
    )
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--only-failures", action="store_true")
    parser.add_argument("--only-executable", action="store_true")
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use run_llm_judge dry-run mode without calling the OpenAI API.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only print the benchmark_raw.json files that would be processed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runs_root = Path(args.runs_root).resolve()

    raw_files = find_benchmark_raw_files(runs_root)
    print(f"Runs root: {runs_root}")
    print(f"Excluded top-level folders: {', '.join(sorted(EXCLUDED_FOLDERS))}")
    print(f"Found benchmark_raw.json files to process: {len(raw_files)}")

    for raw_path in raw_files:
        print(f"- {raw_path}")

    if args.list_only:
        return 0

    for index, raw_path in enumerate(raw_files, start=1):
        output_dir = raw_path.parent
        print("=" * 80)
        print(f"[{index}/{len(raw_files)}] Running LLM judge")
        print(f"Input:      {raw_path}")
        print(f"Output dir: {output_dir}")
        print("Output files:")
        print(f"- {output_dir / 'llm_judge_raw.json'}")
        print(f"- {output_dir / 'llm_judge_summary.json'}")
        print(f"- {output_dir / 'benchmark_summary_with_llm_judge.json'}")

        _records, summary = run_llm_judge(
            input_path=raw_path,
            output_dir=output_dir,
            judge_model=args.judge_model,
            prediction_field_mode=args.prediction_field,
            max_items=args.max_items,
            only_failures=args.only_failures,
            only_executable=args.only_executable,
            sample_seed=args.sample_seed,
            dry_run=args.dry_run,
        )

        print(
            "Done: "
            f"judged={summary['num_judged_items']} "
            f"skipped={summary['num_skipped_items']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
