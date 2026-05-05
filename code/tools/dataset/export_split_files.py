"""Export split-specific dataset files from a split-annotated master file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_file(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {path}. Use --overwrite to replace it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_dataset_list(obj: Any, path: Path) -> list[dict[str, Any]]:
    if not isinstance(obj, list):
        raise ValueError(f"{path} must contain a top-level JSON array.")
    for index, item in enumerate(obj, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {index} in {path} is not a JSON object.")
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export train/validation/test files from a split dataset."
    )
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_dir = Path(args.output_dir)

    items = ensure_dataset_list(load_json_file(input_path), input_path)

    train_items = [item for item in items if item.get("split") == "train"]
    validation_items = [item for item in items if item.get("split") == "validation"]
    test_items = [item for item in items if item.get("split") == "test"]

    save_json_file(output_dir / "train.json", train_items, overwrite=args.overwrite)
    save_json_file(output_dir / "validation.json", validation_items, overwrite=args.overwrite)
    save_json_file(output_dir / "test.json", test_items, overwrite=args.overwrite)

    summary = {
        "total_items": len(items),
        "train_count": len(train_items),
        "validation_count": len(validation_items),
        "test_count": len(test_items),
    }
    save_json_file(output_dir / "split_export_summary.json", summary, overwrite=args.overwrite)

    print(f"Exported split files to: {output_dir}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
