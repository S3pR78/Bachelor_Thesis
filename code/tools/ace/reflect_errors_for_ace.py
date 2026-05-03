from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from src.ace.reflector import (
    load_trace_report,
    reflect_trace_report,
    save_delta_report,
)


def print_delta_report(report: dict) -> None:
    print("ACE reflector delta report")
    print("=" * 80)
    print(f"traces:       {report['source_trace_path']}")
    print(f"min_support:  {report['min_support']}")
    print(f"deltas:       {report['delta_count']}")
    print()

    category_counts = Counter(
        delta["bullet"]["category"] for delta in report.get("deltas", [])
    )

    print("Delta categories")
    print("-" * 80)
    if not category_counts:
        print("No deltas generated.")
    else:
        for category, count in category_counts.most_common():
            print(f"{category:35s} {count}")

    print()
    print("Generated delta rules")
    print("-" * 80)
    for delta in report.get("deltas", []):
        bullet = delta["bullet"]
        print(f"ID:       {bullet['id']}")
        print(f"Family:   {bullet['family']}")
        print(f"Mode:     {bullet['mode']}")
        print(f"Category: {bullet['category']}")
        print(f"Title:    {bullet['title']}")
        print(f"Rule:     {bullet['content']}")
        if bullet.get("positive_pattern"):
            print(f"Pattern:  {bullet['positive_pattern']}")
        if bullet.get("avoid"):
            print(f"Avoid:    {bullet['avoid']}")
        print(f"Evidence: {', '.join(bullet.get('evidence_item_ids', [])) or '—'}")
        print("-" * 80)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reflect ACE error traces into candidate playbook deltas."
    )
    parser.add_argument(
        "--traces",
        required=True,
        help="Path to ace_error_traces.json.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. Defaults to ace_deltas.json next to the trace file.",
    )
    parser.add_argument(
        "--min-support",
        type=int,
        default=1,
        help="Minimum number of traces required before generating a rule.",
    )
    parser.add_argument(
        "--max-evidence-items",
        type=int,
        default=5,
        help="Maximum number of trace IDs stored as evidence per delta.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trace_path = Path(args.traces)
    output_path = (
        Path(args.output)
        if args.output
        else trace_path.parent / "ace_deltas.json"
    )

    trace_report = load_trace_report(trace_path)

    delta_report = reflect_trace_report(
        trace_report=trace_report,
        trace_path=str(trace_path),
        min_support=args.min_support,
        max_evidence_items=args.max_evidence_items,
    )

    save_delta_report(delta_report, output_path)
    print_delta_report(delta_report)
    print()
    print(f"Saved ACE deltas to: {output_path}")


if __name__ == "__main__":
    main()
