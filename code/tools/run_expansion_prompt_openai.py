from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.core.openai_provider import create_openai_client
from src.utils.config_loader import (
    get_configured_path,
    get_model_entry,
    load_json_config,
)


def read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def extract_json_array(raw_text: str) -> list[dict[str, Any]]:
    text = raw_text.strip()

    try:
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("Model output is valid JSON, but not a JSON array.")
        return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not find a JSON array in model output.")

    candidate = text[start : end + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, list):
        raise ValueError("Extracted JSON content is not a JSON array.")
    return parsed


def validate_candidate_items(
    items: list[dict[str, Any]],
    expected_count: int | None = None,
) -> None:
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
            raise ValueError(
                f"Entry {index} field 'query_components' must be a list."
            )
        if not isinstance(item["special_types"], list):
            raise ValueError(
                f"Entry {index} field 'special_types' must be a list."
            )


def get_usage_counts(response) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0

    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    return input_tokens, output_tokens


def estimate_cost_usd(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    pricing_per_million = {
        "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
        "gpt-5.4": {"input": 2.50, "output": 15.00},
        "gpt-5-mini": {"input": 0.25, "output": 2.00},
        "gpt-5": {"input": 1.25, "output": 10.00},
    }

    pricing = pricing_per_million.get(model_name)
    if pricing is None:
        return None

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost



def build_candidate_items_schema(expected_count: int) -> dict:
    required_fields = [
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
    ]

    item_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": required_fields,
        "properties": {
            "id": {"type": "string"},
            "source_id": {"type": "string"},
            "question": {"type": "string"},
            "gold_sparql": {"type": "string"},
            "family": {"type": "string"},
            "source_dataset": {"type": "string"},
            "language": {"type": "string"},
            "query_type": {"type": "string"},
            "query_shape": {"type": "string"},
            "answer_type": {"type": "string"},
            "complexity_level": {"type": "string"},
            "ambiguity_risk": {"type": "string"},
            "lexical_gap_risk": {"type": "string"},
            "hallucination_risk": {"type": "string"},
            "query_components": {
                "type": "array",
                "items": {"type": "string"},
            },
            "special_types": {
                "type": "array",
                "items": {"type": "string"},
            },
            "number_of_patterns": {"type": "integer"},
            "human_or_generated": {"type": "string"},
            "gold_status": {"type": "string"},
            "review_status": {"type": "string"},
            "split": {"type": "string"},
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": expected_count,
                "maxItems": expected_count,
                "items": item_schema,
            }
        },
    }


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

    model_config_path = get_configured_path("config.model_config")
    model_config_data = load_json_config(model_config_path)
    model_config = get_model_entry(model_config_data, args.model)

    env_var_name = model_config.get("api", {}).get("env_var_name", "OPENAI_API_KEY")

    prompt_path = Path(args.prompt_file)
    output_path = Path(args.output_file)

    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. Use --overwrite to replace it."
        )

    prompt_text = read_text(prompt_path)

    client = create_openai_client(env_var_name=env_var_name)

    schema = build_candidate_items_schema(args.expected_count)

    request_kwargs = {
        "model": args.model,
        "input": prompt_text,
        "max_output_tokens": args.max_output_tokens,
        "reasoning": {"effort": args.reasoning_effort},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "dataset_expansion_candidates",
                "strict": True,
                "schema": schema,
            }
        },
    }

    models_without_temperature = {
        "gpt-5.4",
        "gpt-5.4-mini",
    }

    if args.model not in models_without_temperature:
        request_kwargs["temperature"] = args.temperature

    response = client.responses.create(**request_kwargs)

    raw_text = response.output_text

    try:
        parsed_output = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Model returned non-JSON output. Raw output was:\n{raw_text}"
        ) from exc

    items = parsed_output.get("items")
    if not isinstance(items, list):
        raise ValueError(
            f"Model returned JSON, but no valid 'items' array was found. Raw output was:\n{raw_text}"
        )

    validate_candidate_items(items, expected_count=args.expected_count)

    input_tokens, output_tokens = get_usage_counts(response)
    estimated_cost_usd = estimate_cost_usd(args.model, input_tokens, output_tokens)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Saved {len(items)} candidate entries to: {output_path}")
    print(f"Usage: input_tokens={input_tokens}, output_tokens={output_tokens}")

    if estimated_cost_usd is not None:
        print(f"Estimated API cost: ${estimated_cost_usd:.6f}")
    else:
        print(f"Estimated API cost: unavailable for model '{args.model}'")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise