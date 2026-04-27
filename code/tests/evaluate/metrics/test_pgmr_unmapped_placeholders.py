from __future__ import annotations

import pytest

from src.evaluate.metrics.pgmr_unmapped_placeholders import (
    compute_pgmr_unmapped_placeholders,
    extract_pgmr_unmapped_placeholders,
)


def test_extracts_curly_placeholders() -> None:
    query = """
    SELECT ?paper WHERE {
      ?contribution {{NLP_TASK_PROPERTY}} ?task .
    }
    """

    assert extract_pgmr_unmapped_placeholders(query) == [
        "{{NLP_TASK_PROPERTY}}"
    ]


def test_extracts_angle_placeholders_without_matching_real_iris() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper <http://orkg.org/orkg/predicate/P31> ?contribution .
      ?contribution <NLP_TASK_PROPERTY> ?task .
    }
    """

    assert extract_pgmr_unmapped_placeholders(query) == [
        "<NLP_TASK_PROPERTY>"
    ]


def test_extracts_square_and_token_placeholders() -> None:
    query = """
    SELECT ?paper WHERE {
      ?contribution [UNMAPPED] ?task .
      ?contribution PGMR_UNKNOWN_PROPERTY ?value .
      ?contribution UNMAPPED_PREDICATE ?other .
    }
    """

    assert extract_pgmr_unmapped_placeholders(query) == [
        "PGMR_UNKNOWN_PROPERTY",
        "UNMAPPED_PREDICATE",
        "[UNMAPPED]",
    ]


def test_clean_sparql_has_no_unmapped_placeholders() -> None:
    query = """
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>
    PREFIX orkgc: <http://orkg.org/orkg/class/>

    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
      OPTIONAL { ?task rdfs:label ?taskLabel . }
    }
    """

    assert extract_pgmr_unmapped_placeholders(query) == []


def test_metric_marks_query_with_unmapped_placeholders() -> None:
    metric = compute_pgmr_unmapped_placeholders(
        prediction_query="""
        SELECT ?paper WHERE {
          ?contribution {{NLP_TASK_PROPERTY}} ?task .
          ?contribution <UNKNOWN_CLASS> ?x .
        }
        """
    )

    assert metric["metric"] == "pgmr_unmapped_placeholders"
    assert metric["type"] == "pgmr_based"
    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["has_unmapped_placeholders"] is True
    assert metric["unmapped_placeholder_count"] == 2
    assert metric["unmapped_placeholders"] == [
        "<UNKNOWN_CLASS>",
        "{{NLP_TASK_PROPERTY}}",
    ]


def test_metric_marks_clean_query() -> None:
    metric = compute_pgmr_unmapped_placeholders(
        prediction_query="""
        SELECT ?paper WHERE {
          ?paper orkgp:P31 ?contribution .
          ?contribution a orkgc:C121001 .
        }
        """
    )

    assert metric["comparable"] is True
    assert metric["value"] == 0.0
    assert metric["has_unmapped_placeholders"] is False
    assert metric["unmapped_placeholder_count"] == 0
    assert metric["unmapped_placeholders"] == []


def test_metric_is_not_comparable_without_prediction_query() -> None:
    metric = compute_pgmr_unmapped_placeholders(prediction_query=None)

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["reason"] == "prediction_query_missing"


def test_invalid_query_type_raises_value_error() -> None:
    with pytest.raises(ValueError):
        extract_pgmr_unmapped_placeholders(123)  # type: ignore[arg-type]
