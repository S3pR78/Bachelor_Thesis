from __future__ import annotations

from typing import Any


# Prices are USD per 1M tokens.
# Keep aliases because model names in config/runs may use either hyphens,
# underscores, or local config aliases.
OPENAI_MODEL_PRICES_USD_PER_1M = {
    # GPT-5.4 family
    "gpt-5.4": {
        "input": 2.50,
        "cached_input": 0.25,
        "output": 15.00,
    },
    "gpt_5_4": {
        "input": 2.50,
        "cached_input": 0.25,
        "output": 15.00,
    },
    "gpt-5.4-mini": {
        "input": 0.75,
        "cached_input": 0.075,
        "output": 4.50,
    },
    "gpt_5_4_mini": {
        "input": 0.75,
        "cached_input": 0.075,
        "output": 4.50,
    },

    # Older/OpenAI baseline models used in experiments.
    # Adjust these if your provider pricing changes.
    "gpt-4o-mini": {
        "input": 0.15,
        "cached_input": 0.075,
        "output": 0.60,
    },
    "gpt_4o_mini": {
        "input": 0.15,
        "cached_input": 0.075,
        "output": 0.60,
    },
    "gpt-4o": {
        "input": 2.50,
        "cached_input": 1.25,
        "output": 10.00,
    },
    "gpt_4o": {
        "input": 2.50,
        "cached_input": 1.25,
        "output": 10.00,
    },
}


def normalize_model_name_for_pricing(model_name: str | None) -> str:
    if not model_name:
        return ""

    return str(model_name).strip().lower().replace("_", "-")


def get_openai_model_prices(model_name: str | None) -> dict[str, float] | None:
    if not model_name:
        return None

    raw_name = str(model_name).strip().lower()
    normalized_name = normalize_model_name_for_pricing(model_name)
    underscore_name = normalized_name.replace("-", "_")

    return (
        OPENAI_MODEL_PRICES_USD_PER_1M.get(raw_name)
        or OPENAI_MODEL_PRICES_USD_PER_1M.get(normalized_name)
        or OPENAI_MODEL_PRICES_USD_PER_1M.get(underscore_name)
    )


def normalize_usage_payload(usage: dict[str, Any] | None) -> dict[str, int]:
    usage = usage or {}

    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(
        usage.get("total_tokens", prompt_tokens + completion_tokens)
        or (prompt_tokens + completion_tokens)
    )

    prompt_tokens_details = usage.get("prompt_tokens_details") or {}
    if not isinstance(prompt_tokens_details, dict):
        prompt_tokens_details = {}

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
    prices = get_openai_model_prices(model_name)
    if prices is None:
        return None

    normalized = normalize_usage_payload(usage)

    prompt_tokens = normalized["prompt_tokens"]
    cached_tokens = normalized["cached_tokens"]
    completion_tokens = normalized["completion_tokens"]

    cached_tokens = min(cached_tokens, prompt_tokens)
    non_cached_prompt_tokens = max(prompt_tokens - cached_tokens, 0)

    cost_usd = (
        (non_cached_prompt_tokens / 1_000_000) * prices["input"]
        + (cached_tokens / 1_000_000) * prices["cached_input"]
        + (completion_tokens / 1_000_000) * prices["output"]
    )

    return round(cost_usd, 8)


def build_cost_payload(
    *,
    provider: str,
    model_name: str,
    usage: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_usage = normalize_usage_payload(usage)

    estimated_cost_usd = None
    pricing_available = False

    if provider == "openai":
        estimated_cost_usd = estimate_openai_cost_usd(
            model_name=model_name,
            usage=normalized_usage,
        )
        pricing_available = estimated_cost_usd is not None

    return {
        "provider": provider,
        "model_name": model_name,
        "usage": normalized_usage,
        "estimated_cost_usd": estimated_cost_usd,
        "pricing_available": pricing_available,
    }


def summarize_cost_payloads(results: list[dict[str, Any]]) -> dict[str, Any]:
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    total_cached_tokens = 0
    total_estimated_cost_usd = 0.0
    priced_items = 0
    unpriced_items = 0

    for result in results:
        cost = result.get("cost") or result.get("costs") or {}
        if not isinstance(cost, dict):
            continue

        usage = cost.get("usage") or {}
        if not isinstance(usage, dict):
            usage = {}

        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        item_total_tokens = int(usage.get("total_tokens") or 0)
        cached_tokens = int(usage.get("cached_tokens") or 0)

        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_tokens += item_total_tokens
        total_cached_tokens += cached_tokens

        estimated_cost_usd = cost.get("estimated_cost_usd")
        if estimated_cost_usd is None:
            if prompt_tokens > 0 or completion_tokens > 0 or item_total_tokens > 0:
                unpriced_items += 1
            continue

        priced_items += 1
        total_estimated_cost_usd += float(estimated_cost_usd)

    mean_cost_per_priced_item_usd = (
        None
        if priced_items == 0
        else round(total_estimated_cost_usd / priced_items, 8)
    )

    return {
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "total_cached_tokens": total_cached_tokens,
        "total_estimated_cost_usd": round(total_estimated_cost_usd, 8),
        "priced_items": priced_items,
        "unpriced_items": unpriced_items,
        "mean_cost_per_priced_item_usd": mean_cost_per_priced_item_usd,
    }


# Backward-compatible alias if other code imports summarize_costs.
def summarize_costs(results: list[dict[str, Any]]) -> dict[str, Any]:
    return summarize_cost_payloads(results)
