from __future__ import annotations

from typing import Any

from src.evaluate.query_text_normalization import normalize_sparql_query_text


def _build_non_comparable_metric(reason: str) -> dict[str, Any]:
    return {
        "metric": "query_normalized_exact_match",
        "type": "query_based",
        "comparable": False,
        "value": None,
        "reason": reason,
        "comparison_mode": "normalized_text",
        "prediction_normalized_length": None,
        "gold_normalized_length": None,
    }


def compute_query_normalized_exact_match(
    *,
    prediction_query: str | None,
    gold_query: str | None,
) -> dict[str, Any]:
    """Compare predicted and gold SPARQL after lightweight text normalization.

    This metric is query-based, not answer-based. It is not a full semantic
    SPARQL equivalence check. It only checks whether the normalized query text
    is identical.
    """

    if prediction_query is None or not str(prediction_query).strip():
        return _build_non_comparable_metric("prediction_query_missing")

    if gold_query is None or not str(gold_query).strip():
        return _build_non_comparable_metric("gold_query_missing")

    normalized_prediction = normalize_sparql_query_text(prediction_query)
    normalized_gold = normalize_sparql_query_text(gold_query)

    is_match = normalized_prediction == normalized_gold

    return {
        "metric": "query_normalized_exact_match",
        "type": "query_based",
        "comparable": True,
        "value": 1.0 if is_match else 0.0,
        "comparison_mode": "normalized_text",
        "prediction_normalized_length": len(normalized_prediction),
        "gold_normalized_length": len(normalized_gold),
    }
