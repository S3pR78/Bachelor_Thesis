from __future__ import annotations

import pytest

from src.evaluate.metrics.query_bleu import compute_query_bleu


def test_query_bleu_is_one_for_identical_normalized_queries() -> None:
    prediction = """
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>

    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
    }
    """

    gold = """
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>
    SELECT   ?paper   WHERE {
      ?paper    orkgp:P31    ?contribution .
    }
    """

    metric = compute_query_bleu(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["metric"] == "query_bleu"
    assert metric["type"] == "query_based"
    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["bleu"] == 1.0
    assert metric["comparison_mode"] == "normalized_token_bleu"
    assert metric["max_order"] == 4


def test_query_bleu_decreases_for_different_predicate() -> None:
    prediction = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution orkgp:P181004 ?taskType .
    }
    """

    gold = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution orkgp:P181003 ?task .
    }
    """

    metric = compute_query_bleu(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert 0.0 < metric["value"] < 1.0
    assert metric["prediction_token_count"] > 0
    assert metric["gold_token_count"] > 0


def test_query_bleu_handles_short_queries_with_smoothing() -> None:
    prediction = "ASK { ?s ?p ?o . }"
    gold = "SELECT ?s WHERE { ?s ?p ?o . }"

    metric = compute_query_bleu(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert 0.0 <= metric["value"] <= 1.0
    assert len(metric["modified_precisions"]) == 4


def test_query_bleu_is_not_comparable_without_prediction() -> None:
    metric = compute_query_bleu(
        prediction_query=None,
        gold_query="SELECT ?s WHERE { ?s ?p ?o . }",
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "prediction_query_missing"


def test_query_bleu_is_not_comparable_without_gold() -> None:
    metric = compute_query_bleu(
        prediction_query="SELECT ?s WHERE { ?s ?p ?o . }",
        gold_query=None,
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "gold_query_missing"


def test_query_bleu_rejects_invalid_max_order() -> None:
    with pytest.raises(ValueError):
        compute_query_bleu(
            prediction_query="SELECT ?s WHERE { ?s ?p ?o . }",
            gold_query="SELECT ?s WHERE { ?s ?p ?o . }",
            max_order=0,
        )


def test_query_bleu_rejects_invalid_smoothing() -> None:
    with pytest.raises(ValueError):
        compute_query_bleu(
            prediction_query="SELECT ?s WHERE { ?s ?p ?o . }",
            gold_query="SELECT ?s WHERE { ?s ?p ?o . }",
            smoothing=0.0,
        )
