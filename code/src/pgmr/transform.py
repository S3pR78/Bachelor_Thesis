from __future__ import annotations

import re
from dataclasses import dataclass


ORKG_COMPACT_URI_PATTERN = re.compile(
    r"\b(?:orkgp:[A-Za-z0-9_]+|orkgc:[A-Za-z0-9_]+|orkgr:[A-Za-z0-9_]+)\b"
)


@dataclass(frozen=True)
class PgmrTransformResult:
    pgmr_sparql: str
    status: str
    replaced_terms: list[str]
    unmapped_terms: list[str]


def extract_orkg_compact_uris(sparql: str) -> list[str]:
    return sorted(set(ORKG_COMPACT_URI_PATTERN.findall(sparql)))


def transform_sparql_to_pgmr(
    sparql: str,
    family: str,
    uri_to_placeholder_by_family: dict[str, dict[str, str]],
) -> PgmrTransformResult:
    if not sparql or not sparql.strip():
        return PgmrTransformResult(
            pgmr_sparql="",
            status="missing_gold_sparql",
            replaced_terms=[],
            unmapped_terms=[],
        )

    family_mapping = uri_to_placeholder_by_family.get(family)
    if family_mapping is None:
        return PgmrTransformResult(
            pgmr_sparql=sparql,
            status="unknown_family",
            replaced_terms=[],
            unmapped_terms=[],
        )

    found_terms = extract_orkg_compact_uris(sparql)
    replaced_terms: list[str] = []
    unmapped_terms: list[str] = []

    transformed = sparql

    # Replace longer identifiers first just to be safe.
    for uri in sorted(found_terms, key=len, reverse=True):
        placeholder = family_mapping.get(uri)

        if placeholder is None:
            unmapped_terms.append(uri)
            continue

        transformed = re.sub(rf"\b{re.escape(uri)}\b", placeholder, transformed)
        replaced_terms.append(uri)

    if unmapped_terms and replaced_terms:
        status = "partially_mapped"
    elif unmapped_terms:
        status = "unmapped_uri"
    else:
        status = "ok"

    return PgmrTransformResult(
        pgmr_sparql=transformed,
        status=status,
        replaced_terms=sorted(replaced_terms),
        unmapped_terms=sorted(unmapped_terms),
    )