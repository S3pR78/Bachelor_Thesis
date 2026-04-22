from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from src.core.openai_provider import create_openai_client
from src.utils.config_loader import (
    get_configured_path,
    get_model_entry,
    load_json_config,
)


SYSTEM_PROMPT = """You generate exactly one high-quality English paraphrase for a benchmark question.

Rules:
1. Preserve meaning exactly.
2. Preserve answer scope exactly.
3. Do not add or remove constraints.
4. Do not change negation, temporal scope, quantity, ranking intent, comparison intent, or missing-information intent.
5. Do not make the wording vague.
6. Keep the paraphrase natural and academically plausible.
7. Use noticeably different wording from the original question.
8. Return JSON only in the form: {"paraphrase": "..."}
"""

USER_PROMPT_TEMPLATE = """Original question:
{question}

Generate exactly one English paraphrase that preserves the original meaning exactly.
"""

RETRY_USER_PROMPT_TEMPLATE = """Original question:
{question}

Your previous attempt was not acceptable because:
{reason}

Generate exactly one English paraphrase that:
- preserves the meaning exactly
- uses clearly different wording
- keeps the same answer scope
- keeps negation, temporal constraints, comparison meaning, ranking meaning, and missing-information meaning unchanged

Return JSON only in the form: {{"paraphrase": "..."}}.
"""


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


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def normalize_question_punctuation(text: str, original: str) -> str:
    cleaned = text.strip()
    original_has_qmark = original.strip().endswith("?")
    cleaned_has_qmark = cleaned.endswith("?")

    if original_has_qmark and not cleaned_has_qmark:
        cleaned = cleaned.rstrip(".! ") + "?"
    elif not original_has_qmark and cleaned_has_qmark:
        cleaned = cleaned.rstrip("?").rstrip()

    return cleaned


def is_bad_paraphrase(original: str, paraphrase: str) -> str | None:
    original_norm = normalize_text(original)
    paraphrase_norm = normalize_text(paraphrase)

    if not paraphrase_norm:
        return "empty paraphrase"

    if paraphrase_norm == original_norm:
        return "paraphrase is identical to original"

    return None


def get_usage_counts(response: Any) -> tuple[int, int]:
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


def build_request_kwargs(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
    reasoning_effort: str,
    temperature: float,
) -> dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["paraphrase"],
        "properties": {
            "paraphrase": {
                "type": "string",
                "minLength": 1,
            }
        },
    }

    request_kwargs: dict[str, Any] = {
        "model": model_name,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": reasoning_effort},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "question_paraphrase",
                "strict": True,
                "schema": schema,
            }
        },
    }

    models_without_temperature = {
        "gpt-5.4",
        "gpt-5.4-mini",
    }

    if model_name not in models_without_temperature:
        request_kwargs["temperature"] = temperature

    return request_kwargs


def generate_paraphrase_once(
    client: Any,
    model_name: str,
    user_prompt: str,
    max_output_tokens: int,
    reasoning_effort: str,
    temperature: float,
) -> tuple[str, int, int]:
    request_kwargs = build_request_kwargs(
        model_name=model_name,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
    )

    response = client.responses.create(**request_kwargs)

    incomplete_details = getattr(response, "incomplete_details", None)
    if incomplete_details is not None:
        reason = getattr(incomplete_details, "reason", None)
        if reason is None and isinstance(incomplete_details, dict):
            reason = incomplete_details.get("reason")
        if reason is not None:
            raise ValueError(f"Response was incomplete. Reason: {reason}")

    raw_text = response.output_text

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON output: {raw_text}") from exc

    paraphrase = parsed.get("paraphrase")
    if not isinstance(paraphrase, str):
        raise ValueError("Model output did not contain a valid 'paraphrase' string.")

    input_tokens, output_tokens = get_usage_counts(response)
    return paraphrase.strip(), input_tokens, output_tokens


def generate_paraphrase_with_retries(
    client: Any,
    model_name: str,
    question: str,
    max_output_tokens: int,
    reasoning_effort: str,
    temperature: float,
    max_attempts: int,
) -> tuple[str, int, int]:
    total_input_tokens = 0
    total_output_tokens = 0
    last_reason = "initial attempt"

    for attempt in range(1, max_attempts + 1):
        if attempt == 1:
            user_prompt = USER_PROMPT_TEMPLATE.format(question=question)
        else:
            user_prompt = RETRY_USER_PROMPT_TEMPLATE.format(
                question=question,
                reason=last_reason,
            )

        paraphrase, input_tokens, output_tokens = generate_paraphrase_once(
            client=client,
            model_name=model_name,
            user_prompt=user_prompt,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
        )

        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        paraphrase = normalize_question_punctuation(paraphrase, question)
        bad_reason = is_bad_paraphrase(question, paraphrase)
        if bad_reason is None:
            return paraphrase, total_input_tokens, total_output_tokens

        last_reason = bad_reason

    raise ValueError(last_reason)


def add_paraphrases(
    items: list[dict[str, Any]],
    client: Any,
    model_name: str,
    max_output_tokens: int,
    reasoning_effort: str,
    temperature: float,
    overwrite_existing: bool,
    sleep_seconds: float,
    max_attempts: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    updated_items: list[dict[str, Any]] = []

    generated_count = 0
    skipped_existing_count = 0
    failed_count = 0

    total_input_tokens = 0
    total_output_tokens = 0

    failures: list[dict[str, str]] = []

    for index, item in enumerate(items, start=1):
        new_item = dict(item)
        item_id = str(item.get("id", f"item_{index}"))

        question = item.get("question")
        if not isinstance(question, str) or not question.strip():
            failed_count += 1
            failures.append(
                {"id": item_id, "reason": "missing or invalid question"}
            )
            updated_items.append(new_item)
            continue

        existing = item.get("paraphrased_questions")
        has_existing = isinstance(existing, list) and len(existing) > 0

        if has_existing and not overwrite_existing:
            skipped_existing_count += 1
            updated_items.append(new_item)
            continue

        try:
            paraphrase, input_tokens, output_tokens = generate_paraphrase_with_retries(
                client=client,
                model_name=model_name,
                question=question,
                max_output_tokens=max_output_tokens,
                reasoning_effort=reasoning_effort,
                temperature=temperature,
                max_attempts=max_attempts,
            )

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            new_item["paraphrased_questions"] = [paraphrase]
            generated_count += 1

        except Exception as exc:  # noqa: BLE001
            failed_count += 1
            failures.append({"id": item_id, "reason": str(exc)})

        updated_items.append(new_item)

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    estimated_cost_usd = estimate_cost_usd(
        model_name=model_name,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
    )

    summary = {
        "total_items": len(items),
        "generated_count": generated_count,
        "skipped_existing_count": skipped_existing_count,
        "failed_count": failed_count,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "failures": failures,
    }

    return updated_items, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add one paraphrased question per dataset entry using OpenAI."
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to the input dataset JSON file.",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Path to the output dataset JSON file.",
    )
    parser.add_argument(
        "--summary-output-file",
        required=True,
        help="Path to save the paraphrase generation summary JSON.",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.4-mini",
        help="OpenAI model name to use.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature for supported models.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=300,
        help="Maximum output tokens per paraphrase generation.",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["minimal", "low", "medium", "high"],
        default="medium",
        help="Reasoning effort for supported reasoning models.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Overwrite existing paraphrased_questions entries.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional pause between requests.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum number of attempts per entry.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing output files.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    model_config_path = get_configured_path("config.model_config")
    model_config_data = load_json_config(model_config_path)
    model_config = get_model_entry(model_config_data, args.model)

    env_var_name = model_config.get("api", {}).get("env_var_name", "OPENAI_API_KEY")

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)
    summary_output_path = Path(args.summary_output_file)

    data = load_json_file(input_path)
    items = ensure_dataset_list(data, input_path)

    client = create_openai_client(env_var_name=env_var_name)

    updated_items, summary = add_paraphrases(
        items=items,
        client=client,
        model_name=args.model,
        max_output_tokens=args.max_output_tokens,
        reasoning_effort=args.reasoning_effort,
        temperature=args.temperature,
        overwrite_existing=args.overwrite_existing,
        sleep_seconds=args.sleep_seconds,
        max_attempts=args.max_attempts,
    )

    save_json_file(output_path, updated_items, overwrite=args.overwrite)
    save_json_file(summary_output_path, summary, overwrite=args.overwrite)

    print(f"Saved paraphrased dataset to: {output_path}")
    print(f"Saved paraphrase summary to: {summary_output_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if summary["estimated_cost_usd"] is not None:
        print(f"Estimated total API cost: ${summary['estimated_cost_usd']:.6f}")
    else:
        print(f"Estimated total API cost: unavailable for model '{args.model}'")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise