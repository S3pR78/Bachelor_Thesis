from __future__ import annotations

from typing import Any


# Aktuell bewusst klein gehalten: zuerst nur das Modell,
# das du gerade wirklich testest.
OPENAI_MODEL_PRICES_USD_PER_1M = {
    "gpt-5.4": {
        "input": 2.50,
        "cached_input": 0.25,
        "output": 15.00,
    }
}


def normalize_usage_payload(usage: dict[str, Any] | None) -> dict[str, int]:
    usage = usage or {}

    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(
        usage.get("total_tokens", prompt_tokens + completion_tokens)
        or (prompt_tokens + completion_tokens)
    )

    prompt_tokens_details = usage.get("prompt_tokens_details") or {}
    cached_tokens = int(
        prompt_tokens_details.get("cached_tokens", 0)
        or usage.get("cached_tokens", 0)
        or 0
    )

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
    }


def estimate_openai_cost_usd(
    model_name: str,
    usage: dict[str, Any] | None,
) -> float | None:
    prices = OPENAI_MODEL_PRICES_USD_PER_1M.get(model_name)
    if prices is None:
        return None

    normalized = normalize_usage_payload(usage)

    prompt_tokens = normalized["prompt_tokens"]
    cached_tokens = normalized["cached_tokens"]
    completion_tokens = normalized["completion_tokens"]

    non_cached_prompt_tokens = max(prompt_tokens - cached_tokens, 0)

    cost_usd = (
        (non_cached_prompt_tokens / 1_000_000) * prices["input"]
        + (cached_tokens / 1_000_000) * prices["cached_input"]
        + (completion_tokens / 1_000_000) * prices["output"]
    )

    return round(cost_usd, 6)


def build_cost_payload(
    *,
    provider: str,
    model_name: str,
    usage: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_usage = normalize_usage_payload(usage)

    if provider != "openai":
        return {
            "provider": provider,
            "model_name": model_name,
            "usage": normalized_usage,
            "estimated_cost_usd": None,
        }

    return {
        "provider": provider,
        "model_name": model_name,
        "usage": normalized_usage,
        "estimated_cost_usd": estimate_openai_cost_usd(
            model_name=model_name,
            usage=normalized_usage,
        ),
    }