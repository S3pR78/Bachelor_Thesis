from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def detect_sparql_query_type(query: str) -> str:
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
    if not isinstance(endpoint_url, str) or not endpoint_url.strip():
        raise ValueError("endpoint_url must be a non-empty string.")

    encoded_body = urlencode({"query": query}).encode("utf-8")

    request = Request(
        url=endpoint_url,
        data=encoded_body,
        method="POST",
        headers={
            "Accept": "application/sparql-results+json, application/json",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        },
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"SPARQL endpoint returned HTTP {exc.code}: {error_body}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach SPARQL endpoint: {exc}") from exc

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "SPARQL endpoint did not return valid JSON."
        ) from exc