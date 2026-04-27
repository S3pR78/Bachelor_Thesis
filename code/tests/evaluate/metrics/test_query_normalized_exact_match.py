from __future__ import annotations

from src.evaluate.metrics.query_normalized_exact_match import (
    compute_query_normalized_exact_match,
)


def test_query_normalized_exact_match_ignores_comments_whitespace_and_prefix_order() -> None:
    prediction = """
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>
    PREFIX orkgc: <http://orkg.org/orkg/class/>

    # model comment
    SELECT   ?paper WHERE {
      ?paper orkgp:P31 ?contribution . # inline comment
      ?contribution a orkgc:C121001 .
    }
    """

    gold = """
    PREFIX orkgc: <http://orkg.org/orkg/class/>
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>

    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
    }
    """

    metric = compute_query_normalized_exact_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["metric"] == "query_normalized_exact_match"
    assert metric["type"] == "query_based"
    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["comparison_mode"] == "normalized_text"


def test_query_normalized_exact_match_detects_different_predicate() -> None:
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

    metric = compute_query_normalized_exact_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 0.0


def test_query_normalized_exact_match_is_not_comparable_without_prediction() -> None:
    metric = compute_query_normalized_exact_match(
        prediction_query=None,
        gold_query="SELECT ?s WHERE { ?s ?p ?o . }",
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "prediction_query_missing"


def test_query_normalized_exact_match_is_not_comparable_without_gold() -> None:
    metric = compute_query_normalized_exact_match(
        prediction_query="SELECT ?s WHERE { ?s ?p ?o . }",
        gold_query=None,
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "gold_query_missing"


def test_query_normalized_exact_match_handles_markdown_fences() -> None:
    prediction = """```sparql
    SELECT ?s WHERE {
      ?s ?p ?o .
    }
    ```"""

    gold = """
    SELECT ?s WHERE {
      ?s ?p ?o .
    }
    """

    metric = compute_query_normalized_exact_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 1.0
