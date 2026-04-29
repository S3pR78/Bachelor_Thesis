from __future__ import annotations

import argparse
import json
from pathlib import Path
from string import Formatter
from typing import Any

from src.train.config import get_train_run_config, load_train_config


def load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected dataset list in {path}")

    return data


def format_prompt_value(value: Any) -> str:
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


def read_prompt_template_reference(template_ref: Any) -> str:
    """Return inline prompt text or read prompt text from a file path."""
    if template_ref is None:
        raise ValueError("Prompt template reference is missing.")

    text = str(template_ref)

    # Path-style prompt reference.
    if "\n" not in text and len(text) < 500:
        candidate = Path(text)
        if candidate.exists() and candidate.is_file():
            return candidate.read_text(encoding="utf-8")

    # Inline prompt template.
    return text


def resolve_prompt_template(entry: dict[str, Any], prompt_config: str | dict[str, Any]) -> str:
    """Resolve prompt template for one dataset entry.

    Supported config formats:

    Old:
      "prompt": {
        "template": "..."
      }

    New:
      "prompt": {
        "template_by_family": {
          "nlp4re": "code/prompts/.../nlp4re_prompt.txt",
          "empirical_research_practice": "code/prompts/.../empirical_research_prompt.txt"
        }
      }
    """
    if isinstance(prompt_config, str):
        return read_prompt_template_reference(prompt_config)

    if not isinstance(prompt_config, dict):
        raise ValueError("prompt_config must be a string or dictionary.")

    if "template_by_family" in prompt_config:
        family = str(entry.get("family", "")).strip()
        templates = prompt_config["template_by_family"]

        if not isinstance(templates, dict):
            raise ValueError("prompt.template_by_family must be a dictionary.")

        if family not in templates:
            available = ", ".join(sorted(str(key) for key in templates.keys()))
            raise KeyError(
                f"No prompt template configured for family={family!r}. "
                f"Available families: {available}"
            )

        return read_prompt_template_reference(templates[family])

    if "template" in prompt_config:
        return read_prompt_template_reference(prompt_config["template"])

    raise ValueError("Prompt config must contain either 'template' or 'template_by_family'.")


def entry_matches_filters(entry: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True

    for key, expected in filters.items():
        actual = entry.get(key)
        if str(actual).strip() != str(expected).strip():
            return False

    return True


def build_training_input(entry: dict[str, Any], prompt_template: str) -> str:
    if not isinstance(prompt_template, str) or not prompt_template.strip():
        raise ValueError("prompt_template must be a non-empty string.")

    format_values: dict[str, str] = {}

    for _, field_name, _, _ in Formatter().parse(prompt_template):
        if not field_name:
            continue

        value = entry.get(field_name)

        if field_name in {"family", "question"} and (
            value is None or not str(value).strip()
        ):
            raise ValueError(
                f"Missing required prompt field '{field_name}' "
                f"for entry id={entry.get('id')}"
            )

        format_values[field_name] = format_prompt_value(value)

    return prompt_template.format(**format_values)


def build_training_examples(
    entries: list[dict[str, Any]],
    prompt_config: str | dict[str, Any] | None = None,
    target_field: str = "",
    required_status: str | None = None,
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
    prompt_template: str | None = None,
) -> list[dict[str, str]]:
    """Build seq2seq training examples.

    Backward compatible:
    - old caller can pass prompt_template
    - new caller can pass prompt_config
    - old config can use required_status for pgmr_status
    - new config can use filters={"pgmr_status": "ok"}
    """
    if prompt_config is None:
        prompt_config = prompt_template

    if prompt_config is None:
        raise ValueError("Either prompt_config or prompt_template must be provided.")

    if not target_field:
        raise ValueError("target_field must be provided.")

    effective_filters = dict(filters or {})
    if required_status is not None:
        effective_filters.setdefault("pgmr_status", required_status)

    examples: list[dict[str, str]] = []

    for entry in entries:
        if limit is not None and len(examples) >= limit:
            break

        if not entry_matches_filters(entry, effective_filters):
            continue

        target = str(entry.get(target_field, "")).strip()
        if not target:
            continue

        prompt_template_for_entry = resolve_prompt_template(entry, prompt_config)

        examples.append(
            {
                "id": str(entry.get("id", "")),
                "family": str(entry.get("family", "")),
                "input_text": build_training_input(entry, prompt_template_for_entry),
                "target_text": target,
            }
        )

    return examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview training examples.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("code/config/train_config.json"),
        help="Path to train_config.json.",
    )
    parser.add_argument("--run", required=True, help="Training run name.")
    parser.add_argument(
        "--split",
        choices=["train", "validation"],
        default="train",
        help="Dataset split to preview.",
    )
    parser.add_argument("--limit", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = load_train_config(args.config)
    run_config = get_train_run_config(config, args.run)

    dataset_config = run_config["dataset"]
    prompt_config = run_config["prompt"]

    dataset_path = Path(
        dataset_config["train_path"]
        if args.split == "train"
        else dataset_config["validation_path"]
    )

    entries = load_dataset(dataset_path)

    examples = build_training_examples(
        entries=entries,
        prompt_config=prompt_config,
        target_field=dataset_config["target_field"],
        required_status=dataset_config.get("required_status"),
        filters=dataset_config.get("filters"),
        limit=args.limit,
    )

    print(f"Loaded entries: {len(entries)}")
    print(f"Preview examples: {len(examples)}")
    print(f"Dataset path: {dataset_path}")
    print(f"Target field: {dataset_config['target_field']}")
    print(f"Required status: {dataset_config.get('required_status')}")
    print(f"Filters: {dataset_config.get('filters')}")

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
