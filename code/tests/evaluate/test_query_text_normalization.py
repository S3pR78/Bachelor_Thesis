from __future__ import annotations

import pytest

from src.evaluate.query_text_normalization import (
    normalize_sparql_query_text,
    strip_sparql_comments,
    tokenize_normalized_sparql,
)


def test_normalize_removes_comments_and_whitespace() -> None:
    query = """
    # leading comment
    SELECT   ?paper   WHERE   {
      ?paper    orkgp:P31    ?contribution . # inline comment
      ?contribution a orkgc:C121001 .
    }
    """

    normalized = normalize_sparql_query_text(query)

    assert normalized == (
        "SELECT ?paper WHERE { ?paper orkgp:P31 ?contribution . "
        "?contribution a orkgc:C121001 . }"
    )


def test_strip_comments_keeps_hash_inside_string_literal() -> None:
    query = '''
    SELECT ?paper WHERE {
      ?paper rdfs:label "A label with # inside" .
      # real comment
      ?paper orkgp:P31 ?contribution .
    }
    '''

    stripped = strip_sparql_comments(query)

    assert '"A label with # inside"' in stripped
    assert "real comment" not in stripped
    assert "orkgp:P31" in stripped


def test_normalize_sorts_prefix_declarations() -> None:
    first = """
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>
    PREFIX orkgc: <http://orkg.org/orkg/class/>
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
    }
    """

    second = """
    PREFIX orkgc: <http://orkg.org/orkg/class/>
    PREFIX orkgp: <http://orkg.org/orkg/predicate/>

    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
    }
    """

    assert normalize_sparql_query_text(first) == normalize_sparql_query_text(second)


def test_normalize_removes_markdown_code_fences() -> None:
    query = """```sparql
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
    }
    ```"""

    normalized = normalize_sparql_query_text(query)

    assert normalized == "SELECT ?paper WHERE { ?paper orkgp:P31 ?contribution . }"


def test_tokenize_normalized_sparql() -> None:
    query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
    }
    """

    tokens = tokenize_normalized_sparql(query)

    assert tokens == [
        "SELECT",
        "?paper",
        "WHERE",
        "{",
        "?paper",
        "orkgp:P31",
        "?contribution",
        ".",
        "}",
    ]


def test_none_query_normalizes_to_empty_string() -> None:
    assert normalize_sparql_query_text(None) == ""
    assert tokenize_normalized_sparql(None) == []


def test_invalid_query_type_raises_value_error() -> None:
    with pytest.raises(ValueError):
        normalize_sparql_query_text(123)  # type: ignore[arg-type]
