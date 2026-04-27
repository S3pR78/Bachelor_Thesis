from __future__ import annotations

import pytest

from src.evaluate.query_elements import (
    extract_orkg_query_elements,
    get_orkg_ref_counts,
)


def test_extracts_prefixed_orkg_references() -> None:
    query = """
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>
    PREFIX orkgc: <http://orkg.org/orkg/class/>
    PREFIX orkgr: <http://orkg.org/orkg/resource/>

    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
      BIND(orkgr:R1544125 AS ?template)
    }
    """

    elements = extract_orkg_query_elements(query)

    assert elements["predicate_refs"] == frozenset(
        {
            "orkgp:P31",
            "orkgp:P181003",
        }
    )
    assert elements["class_refs"] == frozenset({"orkgc:C121001"})
    assert elements["resource_refs"] == frozenset({"orkgr:R1544125"})
    assert elements["all_refs"] == frozenset(
        {
            "orkgp:P31",
            "orkgp:P181003",
            "orkgc:C121001",
            "orkgr:R1544125",
        }
    )


def test_extracts_full_orkg_iris_as_canonical_prefixed_refs() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper <http://orkg.org/orkg/predicate/P31> ?contribution .
      ?contribution a <http://orkg.org/orkg/class/C27001> .
      BIND(<http://orkg.org/orkg/resource/R186491> AS ?template)
    }
    """

    elements = extract_orkg_query_elements(query)

    assert elements["predicate_refs"] == frozenset({"orkgp:P31"})
    assert elements["class_refs"] == frozenset({"orkgc:C27001"})
    assert elements["resource_refs"] == frozenset({"orkgr:R186491"})


def test_extracts_special_orkg_predicate_refs() -> None:
    query = """
    SELECT ?evaluation WHERE {
      ?contribution orkgp:HAS_EVALUATION ?evaluation .
      ?evaluation orkgp:P110 ?score .
    }
    """

    elements = extract_orkg_query_elements(query)

    assert elements["predicate_refs"] == frozenset(
        {
            "orkgp:HAS_EVALUATION",
            "orkgp:P110",
        }
    )


def test_deduplicates_references() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?paper orkgp:P31 ?otherContribution .
      ?contribution a orkgc:C121001 .
      ?otherContribution a orkgc:C121001 .
    }
    """

    elements = extract_orkg_query_elements(query)

    assert elements["predicate_refs"] == frozenset({"orkgp:P31"})
    assert elements["class_refs"] == frozenset({"orkgc:C121001"})
    assert len(elements["all_refs"]) == 2


def test_ignores_prefix_declarations_comments_and_string_literals() -> None:
    query = """
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>
    PREFIX orkgc: <http://orkg.org/orkg/class/>

    SELECT ?paper WHERE {
      # This comment mentions orkgp:P999999 and should be ignored.
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      FILTER(?label = "orkgp:P888888 should be ignored inside a string")
    }
    """

    elements = extract_orkg_query_elements(query)

    assert elements["predicate_refs"] == frozenset({"orkgp:P31"})
    assert elements["class_refs"] == frozenset({"orkgc:C121001"})
    assert "orkgp:P999999" not in elements["all_refs"]
    assert "orkgp:P888888" not in elements["all_refs"]


def test_ignores_markdown_code_fences() -> None:
    query = """```sparql
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
    }
    ```"""

    elements = extract_orkg_query_elements(query)

    assert elements["predicate_refs"] == frozenset({"orkgp:P31"})
    assert elements["class_refs"] == frozenset({"orkgc:C121001"})


def test_empty_or_none_query_returns_empty_sets() -> None:
    assert extract_orkg_query_elements(None) == {
        "predicate_refs": frozenset(),
        "class_refs": frozenset(),
        "resource_refs": frozenset(),
        "all_refs": frozenset(),
    }

    assert extract_orkg_query_elements("") == {
        "predicate_refs": frozenset(),
        "class_refs": frozenset(),
        "resource_refs": frozenset(),
        "all_refs": frozenset(),
    }


def test_invalid_query_type_raises_value_error() -> None:
    with pytest.raises(ValueError):
        extract_orkg_query_elements(123)  # type: ignore[arg-type]


def test_get_orkg_ref_counts() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
      BIND(orkgr:R1544125 AS ?template)
    }
    """

    counts = get_orkg_ref_counts(query)

    assert counts == {
        "predicate_ref_count": 2,
        "class_ref_count": 1,
        "resource_ref_count": 1,
        "all_ref_count": 4,
    }
