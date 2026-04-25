from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.train.config import get_train_run_config, load_train_config
from string import Formatter


def load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected dataset list in {path}")

    return data


def format_prompt_value(value) -> str:
    if value is None:
        return "none"

    if isinstance(value, list):
        values = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(values) if values else "none"

    if isinstance(value, dict):
        values = [
            f"{key}={val}"
            for key, val in value.items()
            if str(key).strip() and str(val).strip()
        ]
        return ", ".join(values) if values else "none"

    text = str(value).strip()
    return text if text else "none"


def build_training_input(entry: dict[str, Any], prompt_template: str) -> str:
    if not isinstance(prompt_template, str) or not prompt_template.strip():
        raise ValueError("prompt_template must be a non-empty string.")

    format_values: dict[str, str] = {}

    for _, field_name, _, _ in Formatter().parse(prompt_template):
        if not field_name:
            continue

        value = entry.get(field_name)

        if field_name in {"family", "question"} and (value is None or not str(value).strip()):
            raise ValueError(f"Missing required prompt field '{field_name}' for entry id={entry.get('id')}")

        format_values[field_name] = format_prompt_value(value)

    return prompt_template.format(**format_values)

def build_training_examples(
    entries: list[dict[str, Any]],
    prompt_template: str,
    target_field: str,
    required_status: str | None = None,
    limit: int | None = None,
) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []

    for entry in entries:
        if limit is not None and len(examples) >= limit:
            break

        if required_status is not None:
            status = str(entry.get("pgmr_status", "")).strip()
            if status != required_status:
                continue

        target = str(entry.get(target_field, "")).strip()
        if not target:
            continue

        examples.append(
            {
                "id": str(entry.get("id", "")),
                "family": str(entry.get("family", "")),
                "input_text": build_training_input(entry, prompt_template),
                "target_text": target,
            }
        )

    return examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview training examples for PGMR fine-tuning."
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("code/config/train_config.json"),
        help="Path to train_config.json.",
    )
    parser.add_argument(
        "--run",
        required=True,
        help="Training run name from train_config.json.",
    )
    parser.add_argument(
        "--split",
        choices=["train", "validation"],
        default="train",
        help="Dataset split to preview.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Number of examples to print.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = load_train_config(args.config)
    run_config = get_train_run_config(config, args.run)

    dataset_config = run_config["dataset"]
    prompt_template = run_config["prompt"]["template"]
    target_field = dataset_config["target_field"]
    required_status = dataset_config.get("required_status")

    dataset_path = Path(
        dataset_config["train_path"]
        if args.split == "train"
        else dataset_config["validation_path"]
    )

    entries = load_dataset(dataset_path)

    examples = build_training_examples(
        entries=entries,
        prompt_template=prompt_template,
        target_field=target_field,
        required_status=required_status,
        limit=args.limit,
    )

    print(f"Loaded entries: {len(entries)}")
    print(f"Preview examples: {len(examples)}")
    print(f"Dataset path: {dataset_path}")
    print(f"Target field: {target_field}")
    print(f"Required PGMR status: {required_status}")

    for example in examples:
        print("\n" + "=" * 80)
        print("id:", example["id"])
        print("family:", example["family"])
        print("\nINPUT:")
        print(example["input_text"])
        print("\nTARGET:")
        print(example["target_text"])


if __name__ == "__main__":
    main()
