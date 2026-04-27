from __future__ import annotations

import pytest

from src.evaluate.metrics.uri_hallucination import compute_uri_hallucination


ALLOWED_REFS = frozenset(
    {
        "orkgp:P31",
        "orkgp:P181003",
        "orkgp:P181004",
        "orkgc:C121001",
        "orkgc:C27001",
    }
)


def test_uri_hallucination_detects_no_hallucination() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    metric = compute_uri_hallucination(
        prediction_query=query,
        allowed_refs=ALLOWED_REFS,
    )

    assert metric["metric"] == "uri_hallucination"
    assert metric["type"] == "query_based"
    assert metric["comparable"] is True
    assert metric["value"] == 0.0
    assert metric["has_hallucination"] is False
    assert metric["hallucinated_ref_count"] == 0
    assert metric["hallucinated_ref_rate"] == 0.0
    assert metric["hallucinated_refs"] == []
    assert metric["prediction_ref_count"] == 3


def test_uri_hallucination_detects_unknown_predicate() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P999999 ?x .
    }
    """

    metric = compute_uri_hallucination(
        prediction_query=query,
        allowed_refs=ALLOWED_REFS,
    )

    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["has_hallucination"] is True
    assert metric["hallucinated_ref_count"] == 1
    assert metric["hallucinated_ref_rate"] == 0.3333
    assert metric["hallucinated_refs"] == ["orkgp:P999999"]


def test_uri_hallucination_detects_unknown_class() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C999999 .
    }
    """

    metric = compute_uri_hallucination(
        prediction_query=query,
        allowed_refs=ALLOWED_REFS,
    )

    assert metric["has_hallucination"] is True
    assert metric["hallucinated_refs"] == ["orkgc:C999999"]


def test_uri_hallucination_ignores_resources_by_default() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      BIND(orkgr:R999999 AS ?resource)
    }
    """

    metric = compute_uri_hallucination(
        prediction_query=query,
        allowed_refs=ALLOWED_REFS,
    )

    assert metric["checked_ref_kinds"] == ["predicate", "class"]
    assert metric["has_hallucination"] is False
    assert metric["hallucinated_refs"] == []
    assert metric["checked_prediction_refs"] == ["orkgp:P31"]


def test_uri_hallucination_can_check_resources_when_requested() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      BIND(orkgr:R999999 AS ?resource)
    }
    """

    metric = compute_uri_hallucination(
        prediction_query=query,
        allowed_refs=ALLOWED_REFS,
        checked_ref_kinds=("predicate", "class", "resource"),
    )

    assert metric["checked_ref_kinds"] == ["predicate", "class", "resource"]
    assert metric["has_hallucination"] is True
    assert metric["hallucinated_refs"] == ["orkgr:R999999"]


def test_uri_hallucination_with_no_checked_refs_is_comparable_and_clean() -> None:
    query = """
    SELECT ?s WHERE {
      ?s ?p ?o .
    }
    """

    metric = compute_uri_hallucination(
        prediction_query=query,
        allowed_refs=ALLOWED_REFS,
    )

    assert metric["comparable"] is True
    assert metric["prediction_ref_count"] == 0
    assert metric["hallucinated_ref_count"] == 0
    assert metric["hallucinated_ref_rate"] == 0.0
    assert metric["value"] == 0.0


def test_uri_hallucination_missing_prediction_query_is_not_comparable() -> None:
    metric = compute_uri_hallucination(
        prediction_query=None,
        allowed_refs=ALLOWED_REFS,
    )

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "prediction_query_missing"


def test_uri_hallucination_rejects_invalid_ref_kind() -> None:
    with pytest.raises(ValueError):
        compute_uri_hallucination(
            prediction_query="SELECT ?s WHERE { ?s ?p ?o . }",
            allowed_refs=ALLOWED_REFS,
            checked_ref_kinds=("predicate", "unknown"),
        )
