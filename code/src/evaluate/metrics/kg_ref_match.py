from __future__ import annotations

from typing import Any

from src.evaluate.metrics.common import round_metric_payload
from src.evaluate.query_elements import extract_orkg_query_elements


REF_KIND_TO_RESULT_KEY = {
    "all": "all_refs",
    "predicate": "predicate_refs",
    "class": "class_refs",
    "resource": "resource_refs",
}


def _build_non_comparable_metric(
    *,
    ref_kind: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "metric": "kg_ref_match",
        "type": "query_based",
        "comparable": False,
        "value": None,
        "precision": None,
        "recall": None,
        "f1": None,
        "reason": reason,
        "ref_kind": ref_kind,
        "matched_ref_count": None,
        "prediction_ref_count": None,
        "gold_ref_count": None,
        "missing_gold_refs": [],
        "extra_predicted_refs": [],
        "matched_refs": [],
    }


def compute_kg_ref_match(
    *,
    prediction_query: str | None,
    gold_query: str | None,
    ref_kind: str = "all",
) -> dict[str, Any]:
    """Compare ORKG references in a predicted SPARQL query against gold.

    This is a query-based metric, not an answer-based metric.

    ref_kind controls which references are compared:
    - "all": predicate, class, and resource refs together
    - "predicate": only orkgp:* refs
    - "class": only orkgc:* refs
    - "resource": only orkgr:* refs
    """

    if ref_kind not in REF_KIND_TO_RESULT_KEY:
        raise ValueError(
            "ref_kind must be one of: "
            f"{', '.join(sorted(REF_KIND_TO_RESULT_KEY))}"
        )

    if prediction_query is None or not str(prediction_query).strip():
        return _build_non_comparable_metric(
            ref_kind=ref_kind,
            reason="prediction_query_missing",
        )

    if gold_query is None or not str(gold_query).strip():
        return _build_non_comparable_metric(
            ref_kind=ref_kind,
            reason="gold_query_missing",
        )

    result_key = REF_KIND_TO_RESULT_KEY[ref_kind]

    prediction_elements = extract_orkg_query_elements(prediction_query)
    gold_elements = extract_orkg_query_elements(gold_query)

    prediction_refs = prediction_elements[result_key]
    gold_refs = gold_elements[result_key]

    matched_refs = prediction_refs & gold_refs
    missing_gold_refs = gold_refs - prediction_refs
    extra_predicted_refs = prediction_refs - gold_refs

    prediction_ref_count = len(prediction_refs)
    gold_ref_count = len(gold_refs)
    matched_ref_count = len(matched_refs)

    if prediction_ref_count == 0 and gold_ref_count == 0:
        precision = 1.0
        recall = 1.0
        f1 = 1.0
    else:
        precision = (
            0.0
            if prediction_ref_count == 0
            else matched_ref_count / prediction_ref_count
        )
        recall = (
            0.0
            if gold_ref_count == 0
            else matched_ref_count / gold_ref_count
        )
        f1 = (
            0.0
            if (precision + recall) == 0.0
            else (2.0 * precision * recall) / (precision + recall)
        )

    return round_metric_payload(
        {
            "metric": "kg_ref_match",
            "type": "query_based",
            "comparable": True,
            "value": f1,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "ref_kind": ref_kind,
            "matched_ref_count": matched_ref_count,
            "prediction_ref_count": prediction_ref_count,
            "gold_ref_count": gold_ref_count,
            "missing_gold_refs": sorted(missing_gold_refs),
            "extra_predicted_refs": sorted(extra_predicted_refs),
            "matched_refs": sorted(matched_refs),
        }
    )
