from __future__ import annotations

import pytest

from src.evaluate.metrics.sparql_structure_match import (
    compute_sparql_structure_match,
    extract_sparql_structure_patterns,
)


def test_extract_sparql_structure_patterns_from_where_body() -> None:
    query = """
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>
    PREFIX orkgc: <http://orkg.org/orkg/class/>

    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    patterns = extract_sparql_structure_patterns(query)

    assert patterns == [
        "?paper orkgp:P31 ?contribution",
        "?contribution a orkgc:C121001",
        "?contribution orkgp:P181003 ?task",
    ]


def test_sparql_structure_match_is_one_for_same_patterns_in_different_order() -> None:
    prediction = """
    SELECT ?paper WHERE {
      ?contribution orkgp:P181003 ?task .
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
    }
    """

    gold = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    metric = compute_sparql_structure_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["metric"] == "sparql_structure_match"
    assert metric["type"] == "query_based"
    assert metric["comparison_mode"] == "sqm_lite"
    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["precision"] == 1.0
    assert metric["recall"] == 1.0
    assert metric["f1"] == 1.0
    assert metric["matched_pattern_count"] == 3
    assert metric["prediction_pattern_count"] == 3
    assert metric["gold_pattern_count"] == 3
    assert metric["missing_gold_patterns"] == []
    assert metric["extra_predicted_patterns"] == []


def test_sparql_structure_match_detects_partial_overlap() -> None:
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

    metric = compute_sparql_structure_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert metric["matched_pattern_count"] == 2
    assert metric["prediction_pattern_count"] == 3
    assert metric["gold_pattern_count"] == 3
    assert metric["precision"] == 0.6667
    assert metric["recall"] == 0.6667
    assert metric["f1"] == 0.6667
    assert metric["missing_gold_patterns"] == [
        "?contribution orkgp:P181003 ?task"
    ]
    assert metric["extra_predicted_patterns"] == [
        "?contribution orkgp:P181004 ?taskType"
    ]


def test_sparql_structure_match_handles_optional_pattern_text() -> None:
    prediction = """
    SELECT ?paper ?label WHERE {
      ?paper orkgp:P31 ?contribution .
      OPTIONAL { ?paper rdfs:label ?label . }
    }
    """

    gold = """
    SELECT ?paper ?label WHERE {
      OPTIONAL { ?paper rdfs:label ?label . }
      ?paper orkgp:P31 ?contribution .
    }
    """

    metric = compute_sparql_structure_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert metric["f1"] == 1.0


def test_sparql_structure_match_is_not_comparable_without_prediction() -> None:
    metric = compute_sparql_structure_match(
        prediction_query=None,
        gold_query="SELECT ?s WHERE { ?s ?p ?o . }",
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "prediction_query_missing"


def test_sparql_structure_match_is_not_comparable_without_gold() -> None:
    metric = compute_sparql_structure_match(
        prediction_query="SELECT ?s WHERE { ?s ?p ?o . }",
        gold_query=None,
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "gold_query_missing"


def test_sparql_structure_match_with_no_patterns_on_both_sides_is_perfect() -> None:
    prediction = "ASK WHERE { }"
    gold = "ASK WHERE { }"

    metric = compute_sparql_structure_match(
        prediction_query=prediction,
        gold_query=gold,
    )

    assert metric["comparable"] is True
    assert metric["prediction_pattern_count"] == 0
    assert metric["gold_pattern_count"] == 0
    assert metric["f1"] == 1.0


def test_extract_sparql_structure_patterns_rejects_invalid_type() -> None:
    with pytest.raises(ValueError):
        extract_sparql_structure_patterns(123)  # type: ignore[arg-type]
