from __future__ import annotations

import math
from collections import Counter
from typing import Any

from src.evaluate.query_text_normalization import tokenize_normalized_sparql


def _build_non_comparable_metric(reason: str) -> dict[str, Any]:
    return {
        "metric": "query_bleu",
        "type": "query_based",
        "comparable": False,
        "value": None,
        "bleu": None,
        "reason": reason,
        "comparison_mode": "normalized_token_bleu",
        "max_order": None,
        "smoothing": None,
        "prediction_token_count": None,
        "gold_token_count": None,
    }


def _ngram_counts(tokens: list[str], order: int) -> Counter[tuple[str, ...]]:
    return Counter(
        tuple(tokens[index : index + order])
        for index in range(0, len(tokens) - order + 1)
    )


def _modified_precision(
    prediction_tokens: list[str],
    gold_tokens: list[str],
    order: int,
    *,
    smoothing: float,
) -> float:
    prediction_counts = _ngram_counts(prediction_tokens, order)
    gold_counts = _ngram_counts(gold_tokens, order)

    if not prediction_counts:
        return 0.0

    clipped_count = 0
    total_count = 0

    for ngram, count in prediction_counts.items():
        clipped_count += min(count, gold_counts.get(ngram, 0))
        total_count += count

    return (clipped_count + smoothing) / (total_count + smoothing)


def compute_query_bleu(
    *,
    prediction_query: str | None,
    gold_query: str | None,
    max_order: int = 4,
    smoothing: float = 1.0,
) -> dict[str, Any]:
    """Compute a lightweight BLEU score over normalized SPARQL tokens.

    This is a query-text-similarity metric. It is not a semantic correctness
    metric. It should be interpreted as a supporting metric only.
    """

    if prediction_query is None or not str(prediction_query).strip():
        return _build_non_comparable_metric("prediction_query_missing")

    if gold_query is None or not str(gold_query).strip():
        return _build_non_comparable_metric("gold_query_missing")

    if max_order <= 0:
        raise ValueError("max_order must be greater than 0.")

    if smoothing <= 0:
        raise ValueError("smoothing must be greater than 0.")

    prediction_tokens = tokenize_normalized_sparql(prediction_query)
    gold_tokens = tokenize_normalized_sparql(gold_query)

    if not prediction_tokens:
        return _build_non_comparable_metric("prediction_query_empty_after_normalization")

    if not gold_tokens:
        return _build_non_comparable_metric("gold_query_empty_after_normalization")

    precisions = [
        _modified_precision(
            prediction_tokens,
            gold_tokens,
            order,
            smoothing=smoothing,
        )
        for order in range(1, max_order + 1)
    ]

    log_precision_sum = sum(math.log(precision) for precision in precisions)
    geometric_mean = math.exp(log_precision_sum / max_order)

    prediction_length = len(prediction_tokens)
    gold_length = len(gold_tokens)

    if prediction_length > gold_length:
        brevity_penalty = 1.0
    else:
        brevity_penalty = math.exp(1.0 - (gold_length / prediction_length))

    bleu = brevity_penalty * geometric_mean

    return {
        "metric": "query_bleu",
        "type": "query_based",
        "comparable": True,
        "value": round(bleu, 4),
        "bleu": round(bleu, 4),
        "comparison_mode": "normalized_token_bleu",
        "max_order": max_order,
        "smoothing": smoothing,
        "prediction_token_count": prediction_length,
        "gold_token_count": gold_length,
        "modified_precisions": [round(value, 4) for value in precisions],
        "brevity_penalty": round(brevity_penalty, 4),
    }
