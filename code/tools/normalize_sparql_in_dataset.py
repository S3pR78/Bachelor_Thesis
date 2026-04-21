from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.sparql.normalization import normalize_sparql_for_storage


def load_json(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {path}. Use --overwrite to replace it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    changed = 0
    normalized_items: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("All dataset entries must be JSON objects.")

        new_item = dict(item)

        gold_sparql = new_item.get("gold_sparql")
        if isinstance(gold_sparql, str):
            normalized = normalize_sparql_for_storage(gold_sparql)
            if normalized != gold_sparql:
                changed += 1
            new_item["gold_sparql"] = normalized

        normalized_items.append(new_item)

    return normalized_items, changed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize gold_sparql fields in a dataset JSON file."
    )
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    data = load_json(input_path)
    if not isinstance(data, list):
        raise ValueError("Expected a top-level JSON array.")

    normalized_items, changed = normalize_items(data)
    save_json(output_path, normalized_items, overwrite=args.overwrite)

    print(f"Saved normalized dataset to: {output_path}")
    print(f"Entries changed: {changed}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise