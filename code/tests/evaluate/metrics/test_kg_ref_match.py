from __future__ import annotations

import pytest

from src.evaluate.metrics.kg_ref_match import compute_kg_ref_match


def test_kg_ref_match_for_exact_match() -> None:
    prediction = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    gold = """
    SELECT ?paper WHERE {
      ?contribution orkgp:P181003 ?task .
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
    }
    """

    metric = compute_kg_ref_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["metric"] == "kg_ref_match"
    assert metric["type"] == "query_based"
    assert metric["comparable"] is True
    assert metric["ref_kind"] == "all"
    assert metric["precision"] == 1.0
    assert metric["recall"] == 1.0
    assert metric["f1"] == 1.0
    assert metric["value"] == 1.0
    assert metric["matched_ref_count"] == 3
    assert metric["prediction_ref_count"] == 3
    assert metric["gold_ref_count"] == 3
    assert metric["missing_gold_refs"] == []
    assert metric["extra_predicted_refs"] == []


def test_kg_ref_match_for_partial_overlap() -> None:
    prediction = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181004 ?taskType .
    }
    """

    gold = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    metric = compute_kg_ref_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert metric["matched_ref_count"] == 2
    assert metric["prediction_ref_count"] == 3
    assert metric["gold_ref_count"] == 3
    assert metric["precision"] == 0.6667
    assert metric["recall"] == 0.6667
    assert metric["f1"] == 0.6667
    assert metric["missing_gold_refs"] == ["orkgp:P181003"]
    assert metric["extra_predicted_refs"] == ["orkgp:P181004"]
    assert metric["matched_refs"] == ["orkgc:C121001", "orkgp:P31"]


def test_kg_ref_match_can_compare_only_predicates() -> None:
    prediction = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C999999 .
      ?contribution orkgp:P181004 ?taskType .
    }
    """

    gold = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    metric = compute_kg_ref_match(
        prediction_query=prediction,
        gold_query=gold,
        ref_kind="predicate",
    )

    assert metric["ref_kind"] == "predicate"
    assert metric["matched_refs"] == ["orkgp:P31"]
    assert metric["missing_gold_refs"] == ["orkgp:P181003"]
    assert metric["extra_predicted_refs"] == ["orkgp:P181004"]
    assert metric["precision"] == 0.5
    assert metric["recall"] == 0.5
    assert metric["f1"] == 0.5


def test_kg_ref_match_can_compare_only_classes() -> None:
    prediction = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C999999 .
    }
    """

    gold = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
    }
    """

    metric = compute_kg_ref_match(
        prediction_query=prediction,
        gold_query=gold,
        ref_kind="class",
    )

    assert metric["ref_kind"] == "class"
    assert metric["matched_refs"] == []
    assert metric["missing_gold_refs"] == ["orkgc:C121001"]
    assert metric["extra_predicted_refs"] == ["orkgc:C999999"]
    assert metric["precision"] == 0.0
    assert metric["recall"] == 0.0
    assert metric["f1"] == 0.0


def test_kg_ref_match_can_compare_only_resources() -> None:
    prediction = """
    SELECT ?paper WHERE {
      BIND(orkgr:R1 AS ?x)
      BIND(orkgr:R2 AS ?y)
    }
    """

    gold = """
    SELECT ?paper WHERE {
      BIND(orkgr:R1 AS ?x)
      BIND(orkgr:R3 AS ?z)
    }
    """

    metric = compute_kg_ref_match(
        prediction_query=prediction,
        gold_query=gold,
        ref_kind="resource",
    )

    assert metric["ref_kind"] == "resource"
    assert metric["matched_refs"] == ["orkgr:R1"]
    assert metric["missing_gold_refs"] == ["orkgr:R3"]
    assert metric["extra_predicted_refs"] == ["orkgr:R2"]
    assert metric["precision"] == 0.5
    assert metric["recall"] == 0.5
    assert metric["f1"] == 0.5


def test_kg_ref_match_with_no_refs_on_both_sides_is_perfect() -> None:
    prediction = """
    SELECT ?s WHERE {
      ?s ?p ?o .
    }
    """

    gold = """
    SELECT ?s WHERE {
      ?s ?p ?o .
    }
    """

    metric = compute_kg_ref_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert metric["prediction_ref_count"] == 0
    assert metric["gold_ref_count"] == 0
    assert metric["precision"] == 1.0
    assert metric["recall"] == 1.0
    assert metric["f1"] == 1.0


def test_kg_ref_match_with_missing_prediction_query_is_not_comparable() -> None:
    metric = compute_kg_ref_match(
        prediction_query=None,
        gold_query="SELECT ?paper WHERE { ?paper orkgp:P31 ?contribution . }",
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "prediction_query_missing"


def test_kg_ref_match_with_missing_gold_query_is_not_comparable() -> None:
    metric = compute_kg_ref_match(
        prediction_query="SELECT ?paper WHERE { ?paper orkgp:P31 ?contribution . }",
        gold_query=None,
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "gold_query_missing"


def test_kg_ref_match_rejects_invalid_ref_kind() -> None:
    with pytest.raises(ValueError):
        compute_kg_ref_match(
            prediction_query="SELECT ?s WHERE { ?s ?p ?o . }",
            gold_query="SELECT ?s WHERE { ?s ?p ?o . }",
            ref_kind="unknown",
        )
