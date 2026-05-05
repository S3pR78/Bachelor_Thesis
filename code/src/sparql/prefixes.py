"""Shared ORKG prefix handling."""

from __future__ import annotations

ORKG_STANDARD_PREFIXES = """PREFIX orkgr: <http://orkg.org/orkg/resource/>
PREFIX orkgc: <http://orkg.org/orkg/class/>
PREFIX orkgp: <http://orkg.org/orkg/predicate/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"""


def prepend_orkg_prefixes(query: str) -> str:
    """Prepend the standard ORKG/RDF prefixes if a query has none."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    stripped = query.lstrip()
    if stripped.upper().startswith("PREFIX "):
        return query.strip()

    return f"{ORKG_STANDARD_PREFIXES}\n\n{query.strip()}"
