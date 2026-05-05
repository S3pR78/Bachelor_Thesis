"""Lightweight ROUGE query-similarity metrics for SPARQL/PGMR text."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from src.evaluate.query_text_normalization import (
    strip_markdown_code_fences,
    strip_sparql_comments,
)


PREFIX_OR_BASE_LINE_RE = re.compile(r"^\s*(?:PREFIX|BASE)\b", flags=re.IGNORECASE)
TOKEN_RE = re.compile(
    r"""
    https?://[^\s<>"{}|\\^`]+
    |[A-Za-z_][A-Za-z0-9_-]*:[A-Za-z_][A-Za-z0-9_-]*
    |\?[A-Za-z_][A-Za-z0-9_]*
    |[A-Za-z_][A-Za-z0-9_-]*
    |\d+(?:\.\d+)?
    |[{}()[\].;,]
    |[<>=!*/+\-]
    """,
    flags=re.VERBOSE,
)


def normalize_query_for_rouge(query: str | None) -> str:
    """Normalize query text conservatively before ROUGE tokenization."""
    if query is None:
        return ""

    if not isinstance(query, str):
        raise ValueError("query must be a string or None.")

    text = strip_markdown_code_fences(query)
    text = strip_sparql_comments(text)

    body_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not PREFIX_OR_BASE_LINE_RE.match(line)
    ]

    text = " ".join(body_lines)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_query_for_rouge(query: str | None) -> list[str]:
    """Tokenize normalized query text without reordering query structure."""
    normalized = normalize_query_for_rouge(query)
    if not normalized:
        return []
    return [match.group(0).lower() for match in TOKEN_RE.finditer(normalized)]


def _ngram_counts(tokens: list[str], order: int) -> Counter[tuple[str, ...]]:
    return Counter(
        tuple(tokens[index : index + order])
        for index in range(0, len(tokens) - order + 1)
    )


def _overlap_precision_recall_f1(
    prediction_units: Counter,
    gold_units: Counter,
) -> tuple[float, float, float, int]:
    if not prediction_units and not gold_units:
        return 1.0, 1.0, 1.0, 0

    if not prediction_units or not gold_units:
        return 0.0, 0.0, 0.0, 0

    overlap = sum(
        min(count, gold_units.get(unit, 0))
        for unit, count in prediction_units.items()
    )
    prediction_total = sum(prediction_units.values())
    gold_total = sum(gold_units.values())

    precision = overlap / prediction_total if prediction_total else 0.0
    recall = overlap / gold_total if gold_total else 0.0
    f1 = (
        0.0
        if precision + recall == 0
        else (2 * precision * recall) / (precision + recall)
    )
    return precision, recall, f1, overlap


def _lcs_length(left: list[str], right: list[str]) -> int:
    if not left or not right:
        return 0

    previous = [0] * (len(right) + 1)
    for left_token in left:
        current = [0]
        for index, right_token in enumerate(right, start=1):
            if left_token == right_token:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current

    return previous[-1]


def _build_non_comparable_metric(metric_name: str, reason: str) -> dict[str, Any]:
    return {
        "metric": metric_name,
        "type": "query_based",
        "comparable": False,
        "value": None,
        "precision": None,
        "recall": None,
        "f1": None,
        "reason": reason,
        "comparison_mode": "rouge_normalized_query_tokens",
        "prediction_token_count": None,
        "gold_token_count": None,
        "overlap_count": None,
    }


def compute_query_rouge_scores(
    *,
    prediction_query: str | None,
    gold_query: str | None,
    metric_prefix: str = "query",
) -> dict[str, dict[str, Any]]:
    """Compute ROUGE-1, ROUGE-2, and ROUGE-L F1 over normalized query tokens."""
    metric_names = {
        "rouge1": f"{metric_prefix}_rouge1_f1",
        "rouge2": f"{metric_prefix}_rouge2_f1",
        "rougeL": f"{metric_prefix}_rougeL_f1",
    }

    if prediction_query is None or not str(prediction_query).strip():
        return {
            name: _build_non_comparable_metric(name, "prediction_query_missing")
            for name in metric_names.values()
        }

    if gold_query is None or not str(gold_query).strip():
        return {
            name: _build_non_comparable_metric(name, "gold_query_missing")
            for name in metric_names.values()
        }

    prediction_tokens = tokenize_query_for_rouge(prediction_query)
    gold_tokens = tokenize_query_for_rouge(gold_query)

    if not prediction_tokens:
        return {
            name: _build_non_comparable_metric(
                name,
                "prediction_query_empty_after_normalization",
            )
            for name in metric_names.values()
        }

    if not gold_tokens:
        return {
            name: _build_non_comparable_metric(
                name,
                "gold_query_empty_after_normalization",
            )
            for name in metric_names.values()
        }

    prediction_unigrams = Counter((token,) for token in prediction_tokens)
    gold_unigrams = Counter((token,) for token in gold_tokens)
    rouge1_precision, rouge1_recall, rouge1_f1, rouge1_overlap = (
        _overlap_precision_recall_f1(prediction_unigrams, gold_unigrams)
    )

    prediction_bigrams = _ngram_counts(prediction_tokens, 2)
    gold_bigrams = _ngram_counts(gold_tokens, 2)
    if not prediction_bigrams and not gold_bigrams:
        rouge2_f1 = 1.0 if prediction_tokens == gold_tokens else 0.0
        rouge2_precision = rouge2_f1
        rouge2_recall = rouge2_f1
        rouge2_overlap = 0
    else:
        rouge2_precision, rouge2_recall, rouge2_f1, rouge2_overlap = (
            _overlap_precision_recall_f1(prediction_bigrams, gold_bigrams)
        )

    lcs_length = _lcs_length(prediction_tokens, gold_tokens)
    rouge_l_precision = lcs_length / len(prediction_tokens)
    rouge_l_recall = lcs_length / len(gold_tokens)
    rouge_l_f1 = (
        0.0
        if rouge_l_precision + rouge_l_recall == 0
        else (2 * rouge_l_precision * rouge_l_recall)
        / (rouge_l_precision + rouge_l_recall)
    )

    def payload(
        metric_name: str,
        precision: float,
        recall: float,
        f1: float,
        overlap_count: int,
        rouge_variant: str,
    ) -> dict[str, Any]:
        rounded_f1 = round(float(f1), 4)
        return {
            "metric": metric_name,
            "type": "query_based",
            "comparable": True,
            "value": rounded_f1,
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": rounded_f1,
            "comparison_mode": "rouge_normalized_query_tokens",
            "rouge_variant": rouge_variant,
            "prediction_token_count": len(prediction_tokens),
            "gold_token_count": len(gold_tokens),
            "overlap_count": overlap_count,
        }

    return {
        metric_names["rouge1"]: payload(
            metric_names["rouge1"],
            rouge1_precision,
            rouge1_recall,
            rouge1_f1,
            rouge1_overlap,
            "rouge1",
        ),
        metric_names["rouge2"]: payload(
            metric_names["rouge2"],
            rouge2_precision,
            rouge2_recall,
            rouge2_f1,
            rouge2_overlap,
            "rouge2",
        ),
        metric_names["rougeL"]: payload(
            metric_names["rougeL"],
            rouge_l_precision,
            rouge_l_recall,
            rouge_l_f1,
            lcs_length,
            "rougeL",
        ),
    }
