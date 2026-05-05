"""SPARQL query-form detection and endpoint execution helpers."""

from __future__ import annotations

import re
import requests


def detect_sparql_query_type(query: str) -> str:
    """Detect the outer SPARQL query form after removing PREFIX lines."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    without_prefixes = re.sub(
        r"(?im)^\s*PREFIX\s+.+?$",
        "",
        query,
    ).lstrip()

    upper = without_prefixes.upper()

    if upper.startswith("SELECT"):
        return "select"
    if upper.startswith("ASK"):
        return "ask"
    if upper.startswith("CONSTRUCT"):
        return "construct"
    if upper.startswith("DESCRIBE"):
        return "describe"

    return "unknown"


def execute_sparql_query(
    query: str,
    endpoint_url: str,
    timeout_seconds: int = 60,
) -> dict:
    """Execute a SPARQL query and return the endpoint JSON response."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    if not isinstance(endpoint_url, str) or not endpoint_url.strip():
        raise ValueError("endpoint_url must be a non-empty string.")

    headers = {
        "Accept": "application/sparql-results+json",
    }

    try:
        response = requests.get(
            endpoint_url,
            headers=headers,
            params={"query": query},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"SPARQL request failed: {exc}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("SPARQL endpoint did not return valid JSON.") from exc
