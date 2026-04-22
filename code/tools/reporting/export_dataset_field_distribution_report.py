from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.evaluate.dataset_analysis import build_dataset_field_distribution_report


def build_default_output_path(dataset_path: str | Path) -> Path:
    dataset_path = Path(dataset_path)

    if dataset_path.suffix:
        return dataset_path.with_suffix(".field_distribution_report.json")

    return dataset_path.parent / f"{dataset_path.name}.field_distribution_report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and export a dataset field distribution report as JSON."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the dataset JSON file.",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Optional path to the schema JSON file.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output path for the field distribution report JSON.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for the number of dataset entries to analyze.",
    )
    parser.add_argument(
        "--coverage-scopes",
        nargs="+",
        default=["required", "schema"],
        help="Coverage scopes to include. Supported: required, schema, dataset",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataset_path = Path(args.dataset)
    schema_path = Path(args.schema) if args.schema is not None else None
    output_path = (
        Path(args.output)
        if args.output is not None
        else build_default_output_path(dataset_path)
    )

    report = build_dataset_field_distribution_report(
        dataset_path=dataset_path,
        schema_path=schema_path,
        limit=args.limit,
        coverage_scopes=args.coverage_scopes,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Field distribution report written to: {output_path}")


if __name__ == "__main__":
    main()