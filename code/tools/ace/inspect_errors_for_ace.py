from __future__ import annotations

import argparse
from pathlib import Path

from src.ace.traces import build_trace_report, save_trace_report


def _shorten(value: str | None, limit: int = 700) -> str:
    if not value:
        return "—"
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + " ..."


def print_report(report: dict, *, max_examples: int) -> None:
    print("ACE error trace report")
    print("=" * 80)
    print(f"raw:          {report['source_raw_path']}")
    print(f"mode:         {report['mode']}")
    print(f"family:       {report.get('family_filter') or 'all'}")
    print(f"split:        {report.get('split_filter') or 'all'}")
    print(f"raw records:  {report['total_records_in_raw']}")
    print(f"traces:       {report['trace_count']}")
    print(f"errors:       {report['error_trace_count']}")
    print()

    print("Category counts")
    print("-" * 80)
    if not report["category_counts"]:
        print("No error categories found.")
    else:
        for category, count in report["category_counts"].items():
            print(f"{category:35s} {count}")

    print()
    print(f"Examples first {max_examples}")
    print("-" * 80)

    for trace in report["traces"][:max_examples]:
        print(f"ID:       {trace.get('item_id')}")
        print(f"Family:   {trace.get('family')}")
        print(f"Split:    {trace.get('split')}")
        print(f"Category: {', '.join(trace.get('categories', [])) or 'success'}")
        print(f"Question: {_shorten(trace.get('question'), 250)}")
        print()
        print("Raw model output:")
        print(_shorten(trace.get("raw_model_output")))
        print()
        print("Extracted query:")
        print(_shorten(trace.get("extracted_query")))
        print()
        print("Restored query:")
        print(_shorten(trace.get("restored_query")))
        print()
        print("Gold SPARQL:")
        print(_shorten(trace.get("gold_sparql")))
        print()
        if trace.get("error_text"):
            print("Error text:")
            print(_shorten(trace.get("error_text")))
            print()
        print("-" * 80)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect benchmark_raw.json and build ACE error traces."
    )
    parser.add_argument(
        "--raw",
        required=True,
        help="Path to benchmark_raw.json.",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["pgmr_lite", "direct_sparql", "any"],
        help="ACE mode for the trace report.",
    )
    parser.add_argument(
        "--family",
        default=None,
        help="Optional family filter, e.g. nlp4re or empirical_research_practice.",
    )
    parser.add_argument(
        "--split",
        default=None,
        help="Optional split filter. Use this to restrict to train/validation only.",
    )
    parser.add_argument(
        "--include-success",
        action="store_true",
        help="Include successful items too. By default only error traces are written.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. Defaults to ace_error_traces.json next to the raw file.",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=10,
        help="Number of examples to print to terminal.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_path = Path(args.raw)

    output_path = (
        Path(args.output)
        if args.output
        else raw_path.parent / "ace_error_traces.json"
    )

    report = build_trace_report(
        raw_path=raw_path,
        mode=args.mode,
        family=args.family,
        split=args.split,
        include_success=args.include_success,
    )

    save_trace_report(report, output_path)
    print_report(report, max_examples=args.max_examples)
    print()
    print(f"Saved ACE traces to: {output_path}")


if __name__ == "__main__":
    main()
