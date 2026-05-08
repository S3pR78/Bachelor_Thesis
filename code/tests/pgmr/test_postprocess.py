from __future__ import annotations

from src.pgmr.postprocess import postprocess_pgmr_query


def test_filter_not_exists_without_braces_wraps_connected_triple_chain() -> None:
    query = """
    SELECT ?paper WHERE {
      FILTER NOT EXISTS ?contribution orkgp:P15124 ?dataAnalysis .
      ?dataAnalysis orkgp:P56043 ?inferentialStatistics .
      ?inferentialStatistics orkgp:P35133 ?statisticalTechnique .
    }
    """

    assert postprocess_pgmr_query(query) == (
        "SELECT ?paper WHERE { FILTER NOT EXISTS { "
        "?contribution orkgp:P15124 ?dataAnalysis . "
        "?dataAnalysis orkgp:P56043 ?inferentialStatistics . "
        "?inferentialStatistics orkgp:P35133 ?statisticalTechnique . } }"
    )


def test_filter_not_exists_with_existing_braces_remains_unchanged() -> None:
    query = """
    SELECT ?paper WHERE {
      FILTER NOT EXISTS {
        ?contribution orkgp:P15124 ?dataAnalysis .
      }
    }
    """

    assert postprocess_pgmr_query(query) == (
        "SELECT ?paper WHERE { FILTER NOT EXISTS { "
        "?contribution orkgp:P15124 ?dataAnalysis . } }"
    )


def test_filter_not_exists_repair_stops_before_optional() -> None:
    query = """
    SELECT ?paper WHERE {
      FILTER NOT EXISTS ?contribution orkgp:P15124 ?dataAnalysis .
      ?dataAnalysis orkgp:P56043 ?inferentialStatistics .
      OPTIONAL { ?paper rdfs:label ?paperLabel . }
    }
    """

    assert postprocess_pgmr_query(query) == (
        "SELECT ?paper WHERE { FILTER NOT EXISTS { "
        "?contribution orkgp:P15124 ?dataAnalysis . "
        "?dataAnalysis orkgp:P56043 ?inferentialStatistics . } "
        "OPTIONAL { ?paper rdfs:label ?paperLabel . } }"
    )


def test_malformed_regex_equality_filter_becomes_plain_equality() -> None:
    query = """
    SELECT ?paper WHERE {
      FILTER(REGEX(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
    }
    """

    assert postprocess_pgmr_query(query) == (
        'SELECT ?paper WHERE { FILTER(LCASE(STR(?venueName)) = '
        'LCASE("IEEE International Requirements Engineering Conference")) }'
    )


def test_valid_regex_filter_remains_unchanged() -> None:
    query = 'SELECT ?paper WHERE { FILTER(REGEX(?label, "abc")) }'

    assert (
        postprocess_pgmr_query(query)
        == 'SELECT ?paper WHERE { FILTER(REGEX(?label, "abc")) }'
    )


def test_pure_output_label_triple_becomes_optional() -> None:
    query = """
    SELECT DISTINCT ?paper ?paperLabel WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C27001 .
      ?paper rdfs:label ?paperLabel .
    }
    ORDER BY ?paperLabel
    """

    assert postprocess_pgmr_query(query) == (
        "SELECT DISTINCT ?paper ?paperLabel WHERE { "
        "?paper orkgp:P31 ?contribution . "
        "?contribution a orkgc:C27001 . "
        "OPTIONAL { ?paper rdfs:label ?paperLabel . } } "
        "ORDER BY ?paperLabel"
    )


def test_label_used_in_filter_is_not_made_optional() -> None:
    query = """
    SELECT ?paper WHERE {
      ?venue rdfs:label ?venueName .
      FILTER(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
    }
    """

    assert postprocess_pgmr_query(query) == (
        "SELECT ?paper WHERE { ?venue rdfs:label ?venueName . "
        'FILTER(LCASE(STR(?venueName)) = '
        'LCASE("IEEE International Requirements Engineering Conference")) }'
    )


def test_already_optional_label_triple_remains_unchanged() -> None:
    query = """
    SELECT ?paper ?paperLabel WHERE {
      OPTIONAL { ?paper rdfs:label ?paperLabel . }
    }
    """

    assert postprocess_pgmr_query(query) == (
        "SELECT ?paper ?paperLabel WHERE { "
        "OPTIONAL { ?paper rdfs:label ?paperLabel . } }"
    )


def test_realistic_query_combines_limited_repairs() -> None:
    query = """
    SELECT DISTINCT ?paper ?paperLabel WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C27001 .
      ?venue rdfs:label ?venueName .
      FILTER(REGEX(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
      FILTER NOT EXISTS ?contribution orkgp:P15124 ?dataAnalysis .
      ?dataAnalysis orkgp:P56043 ?inferentialStatistics .
      ?inferentialStatistics orkgp:P35133 ?statisticalTechnique .
      OPTIONAL { ?paper rdfs:label ?alreadyOptionalLabel . }
      ?paper rdfs:label ?paperLabel .
    }
    ORDER BY ?paperLabel
    """

    assert postprocess_pgmr_query(query) == (
        "SELECT DISTINCT ?paper ?paperLabel WHERE { "
        "?paper orkgp:P31 ?contribution . "
        "?contribution a orkgc:C27001 . "
        "?venue rdfs:label ?venueName . "
        'FILTER(LCASE(STR(?venueName)) = '
        'LCASE("IEEE International Requirements Engineering Conference")) '
        "FILTER NOT EXISTS { ?contribution orkgp:P15124 ?dataAnalysis . "
        "?dataAnalysis orkgp:P56043 ?inferentialStatistics . "
        "?inferentialStatistics orkgp:P35133 ?statisticalTechnique . } "
        "OPTIONAL { ?paper rdfs:label ?alreadyOptionalLabel . } "
        "OPTIONAL { ?paper rdfs:label ?paperLabel . } } "
        "ORDER BY ?paperLabel"
    )
