from __future__ import annotations

import argparse
from pathlib import Path

from src.ace.curator import apply_delta_report_to_playbook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Curate ACE deltas and update an ACE playbook."
    )
    parser.add_argument(
        "--playbook",
        required=True,
        help="Path to the target ACE playbook JSON. Created if missing.",
    )
    parser.add_argument(
        "--deltas",
        required=True,
        help="Path to ace_deltas.json.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output playbook path. Defaults to overwriting --playbook.",
    )
    parser.add_argument(
        "--family",
        default=None,
        help="Optional family filter, e.g. nlp4re.",
    )
    parser.add_argument(
        "--mode",
        default=None,
        choices=["pgmr_lite", "direct_sparql", "any"],
        help="Optional ACE mode filter.",
    )
    parser.add_argument(
        "--min-priority",
        type=int,
        default=0,
        help="Only apply deltas with at least this priority.",
    )
    parser.add_argument(
        "--max-deltas",
        type=int,
        default=None,
        help="Apply at most this many highest-priority deltas.",
    )
    parser.add_argument(
        "--allowed-category",
        action="append",
        default=None,
        help="Optional allowlist category. Can be passed multiple times.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be applied without writing the playbook.",
    )
    return parser.parse_args()


def print_summary(summary: dict) -> None:
    print("ACE curator summary")
    print("=" * 80)
    print(f"playbook:            {summary['playbook_path']}")
    print(f"deltas:              {summary['source_delta_path']}")
    print(f"output:              {summary['output_path']}")
    print(f"before bullets:      {summary['before_bullet_count']}")
    print(f"after bullets:       {summary['after_bullet_count']}")
    print(f"candidate deltas:    {summary['candidate_delta_count']}")
    print(f"applied deltas:      {summary['applied_delta_count']}")
    print(f"skipped deltas:      {summary['skipped_delta_count']}")

    if summary["skipped_reasons"]:
        print()
        print("Skipped reasons")
        print("-" * 80)
        for reason, count in summary["skipped_reasons"].items():
            print(f"{reason:30s} {count}")

    if summary["applied_delta_ids"]:
        print()
        print("Applied delta IDs")
        print("-" * 80)
        for delta_id in summary["applied_delta_ids"]:
            print(delta_id)


def main() -> None:
    args = parse_args()

    output_path = Path(args.output) if args.output else Path(args.playbook)
    allowed_categories = (
        set(args.allowed_category) if args.allowed_category else None
    )

    _, summary = apply_delta_report_to_playbook(
        playbook_path=args.playbook,
        delta_path=args.deltas,
        output_path=output_path,
        family=args.family,
        mode=args.mode,
        min_priority=args.min_priority,
        max_deltas=args.max_deltas,
        allowed_categories=allowed_categories,
        dry_run=args.dry_run,
    )

    summary_dict = summary.to_dict()
    print_summary(summary_dict)

    if args.dry_run:
        print()
        print("Dry run only. Playbook was not written.")
    else:
        print()
        print(f"Saved ACE playbook to: {output_path}")


if __name__ == "__main__":
    main()
