from __future__ import annotations

from typing import Any

from src.evaluate.query_elements import extract_orkg_query_elements


REF_KIND_TO_RESULT_KEY = {
    "predicate": "predicate_refs",
    "class": "class_refs",
    "resource": "resource_refs",
}


def _build_non_comparable_metric(
    *,
    reason: str,
    checked_ref_kinds: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "metric": "uri_hallucination",
        "type": "query_based",
        "comparable": False,
        "value": None,
        "has_hallucination": None,
        "hallucinated_ref_rate": None,
        "reason": reason,
        "checked_ref_kinds": list(checked_ref_kinds),
        "prediction_ref_count": None,
        "allowed_ref_count": None,
        "hallucinated_ref_count": None,
        "hallucinated_refs": [],
        "checked_prediction_refs": [],
    }


def _collect_refs_by_kinds(
    grouped_refs: dict[str, frozenset[str]],
    checked_ref_kinds: tuple[str, ...],
) -> frozenset[str]:
    refs: set[str] = set()

    for ref_kind in checked_ref_kinds:
        result_key = REF_KIND_TO_RESULT_KEY[ref_kind]
        refs.update(grouped_refs[result_key])

    return frozenset(refs)


def compute_uri_hallucination(
    *,
    prediction_query: str | None,
    allowed_refs: set[str] | frozenset[str] | None,
    checked_ref_kinds: tuple[str, ...] = ("predicate", "class"),
) -> dict[str, Any]:
    """Detect predicted ORKG refs that are unknown to the local memory.

    This is a local-memory hallucination metric. It does not prove that an ORKG
    ref does not exist globally. It only checks whether the predicted ref is
    absent from the provided allowed_refs memory.

    By default, only predicate and class refs are checked because template
    memories often contain a controlled vocabulary of orkgp:* and orkgc:* refs,
    while concrete orkgr:* resources may be open-ended.
    """

    invalid_kinds = [
        ref_kind
        for ref_kind in checked_ref_kinds
        if ref_kind not in REF_KIND_TO_RESULT_KEY
    ]
    if invalid_kinds:
        raise ValueError(
            "checked_ref_kinds contains unsupported values: "
            f"{', '.join(invalid_kinds)}"
        )

    if prediction_query is None or not str(prediction_query).strip():
        return _build_non_comparable_metric(
            reason="prediction_query_missing",
            checked_ref_kinds=checked_ref_kinds,
        )

    if allowed_refs is None:
        return _build_non_comparable_metric(
            reason="allowed_refs_missing",
            checked_ref_kinds=checked_ref_kinds,
        )

    allowed_ref_set = frozenset(allowed_refs)

    prediction_elements = extract_orkg_query_elements(prediction_query)
    checked_prediction_refs = _collect_refs_by_kinds(
        prediction_elements,
        checked_ref_kinds,
    )

    hallucinated_refs = checked_prediction_refs - allowed_ref_set

    prediction_ref_count = len(checked_prediction_refs)
    hallucinated_ref_count = len(hallucinated_refs)
    has_hallucination = hallucinated_ref_count > 0

    hallucinated_ref_rate = (
        0.0
        if prediction_ref_count == 0
        else hallucinated_ref_count / prediction_ref_count
    )

    return {
        "metric": "uri_hallucination",
        "type": "query_based",
        "comparable": True,
        "value": 1.0 if has_hallucination else 0.0,
        "has_hallucination": has_hallucination,
        "hallucinated_ref_rate": round(hallucinated_ref_rate, 4),
        "checked_ref_kinds": list(checked_ref_kinds),
        "prediction_ref_count": prediction_ref_count,
        "allowed_ref_count": len(allowed_ref_set),
        "hallucinated_ref_count": hallucinated_ref_count,
        "hallucinated_refs": sorted(hallucinated_refs),
        "checked_prediction_refs": sorted(checked_prediction_refs),
    }
