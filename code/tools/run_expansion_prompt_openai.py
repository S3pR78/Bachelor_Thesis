from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI


def read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def extract_json_array(raw_text: str) -> list[dict[str, Any]]:
    text = raw_text.strip()

    # Best case: pure JSON array
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("Model output is valid JSON, but not a JSON array.")
        return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: extract first JSON array block
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not find a JSON array in model output.")

    candidate = text[start : end + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, list):
        raise ValueError("Extracted JSON content is not a JSON array.")
    return parsed


def validate_candidate_items(items: list[dict[str, Any]], expected_count: int | None = None) -> None:
    required_fields = {
        "id",
        "source_id",
        "question",
        "gold_sparql",
        "family",
        "source_dataset",
        "language",
        "query_type",
        "query_shape",
        "answer_type",
        "complexity_level",
        "ambiguity_risk",
        "lexical_gap_risk",
        "hallucination_risk",
        "query_components",
        "special_types",
        "number_of_patterns",
        "human_or_generated",
        "gold_status",
        "review_status",
        "split",
    }

    if not items:
        raise ValueError("Generated JSON array is empty.")
    
    if expected_count is not None and len(items) != expected_count:
        raise ValueError(
            f"Expected {expected_count} entries, but got {len(items)}."
        )

    seen_ids: set[str] = set()
    seen_source_ids: set[str] = set()

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {index} is not a JSON object.")

        missing = sorted(required_fields - set(item.keys()))
        if missing:
            raise ValueError(f"Entry {index} is missing required fields: {missing}")

        item_id = str(item["id"])
        source_id = str(item["source_id"])

        if item_id in seen_ids:
            raise ValueError(f"Duplicate id detected: {item_id}")
        if source_id in seen_source_ids:
            raise ValueError(f"Duplicate source_id detected: {source_id}")

        seen_ids.add(item_id)
        seen_source_ids.add(source_id)

        if not isinstance(item["query_components"], list):
            raise ValueError(f"Entry {index} field 'query_components' must be a list.")
        if not isinstance(item["special_types"], list):
            raise ValueError(f"Entry {index} field 'special_types' must be a list.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a final dataset-expansion prompt via OpenAI and save JSON candidates."
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=10,
        help="Expected number of generated candidate entries.",
    )
    parser.add_argument(
        "--prompt-file",
        required=True,
        help="Path to the fully assembled prompt file.",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Path where the generated JSON array should be saved.",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.4-mini",
        help="OpenAI model name to use.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=14000,
        help="Maximum output tokens for the generation.",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["minimal", "low", "medium", "high"],
        default="medium",
        help="Reasoning effort for supported reasoning models.",
)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output file.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set in the environment.")

    prompt_path = Path(args.prompt_file)
    output_path = Path(args.output_file)

    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. Use --overwrite to replace it."
        )

    prompt_text = read_text(prompt_path)

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=args.model,
        input=prompt_text,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        reasoning={"effort": args.reasoning_effort},
        text={"format": {"type": "text"}},
    )

    raw_text = response.output_text
    items = extract_json_array(raw_text)
    validate_candidate_items(items, expected_count=args.expected_count)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved {len(items)} candidate entries to: {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise