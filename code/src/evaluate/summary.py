from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

SUMMARY_SLICE_FIELDS = (
    "family",
    "source_dataset",
    "query_type",
    "answer_type",
    "query_shape",
    "complexity_level",
)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _numeric_metric_values(
    results: list[dict[str, Any]],
    metric_name: str,
    value_field: str = "value",
) -> tuple[list[float], int, int]:
    comparable_values: list[float] = []
    comparable_count = 0
    non_comparable_count = 0

    for result in results:
        validation = result.get("validation") or {}
        metric = validation.get(metric_name)

        if not isinstance(metric, dict):
            non_comparable_count += 1
            continue

        if not metric.get("comparable"):
            non_comparable_count += 1
            continue

        value = metric.get(value_field)
        comparable_count += 1

        if isinstance(value, (int, float)):
            comparable_values.append(float(value))

    return comparable_values, comparable_count, non_comparable_count


def _build_metric_summary(
    results: list[dict[str, Any]],
    metric_name: str,
    value_field: str = "value",
) -> dict[str, Any]:
    values, comparable_count, non_comparable_count = _numeric_metric_values(
        results=results,
        metric_name=metric_name,
        value_field=value_field,
    )

    summary: dict[str, Any] = {
        "metric_name": metric_name,
        "value_field": value_field,
        "comparable_count": comparable_count,
        "non_comparable_count": non_comparable_count,
        "mean": _mean(values),
    }

    if values and all(value in {0.0, 1.0} for value in values):
        success_count = sum(1 for value in values if value == 1.0)
        failure_count = sum(1 for value in values if value == 0.0)
        summary["success_count"] = success_count
        summary["failure_count"] = failure_count
        summary["success_rate"] = _mean(values)

    return summary

def _get_validation_metric(result: dict, metric_name: str) -> dict | None:
    validation = result.get("validation", {})
    metric = validation.get(metric_name)
    return metric if isinstance(metric, dict) else None


def _build_uri_hallucination_summary(results: list[dict]) -> dict:
    metrics = [
        _get_validation_metric(result, "uri_hallucination")
        for result in results
    ]
    metrics = [metric for metric in metrics if metric is not None]

    comparable_metrics = [
        metric for metric in metrics if metric.get("comparable") is True
    ]
    non_comparable_count = len(metrics) - len(comparable_metrics)

    hallucinated_item_count = sum(
        1 for metric in comparable_metrics
        if metric.get("has_hallucination") is True
    )
    clean_item_count = sum(
        1 for metric in comparable_metrics
        if metric.get("has_hallucination") is False
    )

    hallucinated_ref_counts = [
        metric.get("hallucinated_ref_count")
        for metric in comparable_metrics
        if isinstance(metric.get("hallucinated_ref_count"), (int, float))
    ]
    hallucinated_ref_rates = [
        metric.get("hallucinated_ref_rate")
        for metric in comparable_metrics
        if isinstance(metric.get("hallucinated_ref_rate"), (int, float))
    ]

    comparable_count = len(comparable_metrics)

    total_hallucinated_ref_count = int(sum(hallucinated_ref_counts))
    mean_hallucinated_ref_count = (
        None
        if not hallucinated_ref_counts
        else round(sum(hallucinated_ref_counts) / len(hallucinated_ref_counts), 4)
    )
    mean_hallucinated_ref_rate = (
        None
        if not hallucinated_ref_rates
        else round(sum(hallucinated_ref_rates) / len(hallucinated_ref_rates), 4)
    )

    hallucinated_item_rate = (
        None
        if comparable_count == 0
        else round(hallucinated_item_count / comparable_count, 4)
    )

    return {
        "metric_name": "uri_hallucination",
        "type": "query_based",
        "comparable_count": comparable_count,
        "non_comparable_count": non_comparable_count,
        "hallucinated_item_count": hallucinated_item_count,
        "clean_item_count": clean_item_count,
        "hallucinated_item_rate": hallucinated_item_rate,
        "total_hallucinated_ref_count": total_hallucinated_ref_count,
        "mean_hallucinated_ref_count": mean_hallucinated_ref_count,
        "mean_hallucinated_ref_rate": mean_hallucinated_ref_rate,
    }


def _build_response_time_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        float(result["response_time_seconds"])
        for result in results
        if isinstance(result.get("response_time_seconds"), (int, float))
    ]

    if not values:
        return {
            "count": 0,
            "mean_seconds": None,
            "min_seconds": None,
            "max_seconds": None,
            "total_seconds": None,
        }

    return {
        "count": len(values),
        "mean_seconds": round(sum(values) / len(values), 4),
        "min_seconds": round(min(values), 4),
        "max_seconds": round(max(values), 4),
        "total_seconds": round(sum(values), 4),
    }


def _build_error_category_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()

    for result in results:
        validation = result.get("validation") or {}
        category = validation.get("primary_error_category")
        if category is None:
            category = "none"
        counter[str(category)] += 1

    return dict(sorted(counter.items()))


def _build_core_metrics_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "query_extracted": _build_metric_summary(results, "query_extracted"),
        "supported_query_form": _build_metric_summary(results, "supported_query_form"),
        "query_form_match": _build_metric_summary(results, "query_form_match"),
        "prediction_execution_success": _build_metric_summary(
            results,
            "prediction_execution_success",
        ),
        "gold_execution_success": _build_metric_summary(
            results,
            "gold_execution_success",
        ),
        "answer_exact_match": _build_metric_summary(results, "answer_exact_match"),
        "answer_precision": _build_metric_summary(
            results,
            "answer_precision_recall_f1",
            value_field="precision",
        ),
        "answer_recall": _build_metric_summary(
            results,
            "answer_precision_recall_f1",
            value_field="recall",
        ),
        "answer_f1": _build_metric_summary(
            results,
            "answer_precision_recall_f1",
            value_field="f1",
        ),
        "answer_value_exact_match": _build_metric_summary(
            results,
            "answer_value_exact_match",
        ),
        "answer_value_precision": _build_metric_summary(
            results,
            "answer_value_precision_recall_f1",
            value_field="precision",
        ),
        "answer_value_recall": _build_metric_summary(
            results,
            "answer_value_precision_recall_f1",
            value_field="recall",
        ),
        "answer_value_f1": _build_metric_summary(
            results,
            "answer_value_precision_recall_f1",
            value_field="f1",
        ),
        "kg_ref_precision": _build_metric_summary(
            results,
            "kg_ref_match",
            value_field="precision",
        ),
        "kg_ref_recall": _build_metric_summary(
            results,
            "kg_ref_match",
            value_field="recall",
        ),
        "kg_ref_f1": _build_metric_summary(
            results,
            "kg_ref_match",
            value_field="f1",
        ),
        "predicate_ref_precision": _build_metric_summary(
            results,
            "predicate_ref_match",
            value_field="precision",
        ),
        "predicate_ref_recall": _build_metric_summary(
            results,
            "predicate_ref_match",
            value_field="recall",
        ),
        "predicate_ref_f1": _build_metric_summary(
            results,
            "predicate_ref_match",
            value_field="f1",
        ),
        "class_ref_precision": _build_metric_summary(
            results,
            "class_ref_match",
            value_field="precision",
        ),
        "class_ref_recall": _build_metric_summary(
            results,
            "class_ref_match",
            value_field="recall",
        ),
        "class_ref_f1": _build_metric_summary(
            results,
            "class_ref_match",
            value_field="f1",
        ),
        "resource_ref_precision": _build_metric_summary(
            results,
            "resource_ref_match",
            value_field="precision",
        ),
        "resource_ref_recall": _build_metric_summary(
            results,
            "resource_ref_match",
            value_field="recall",
        ),
        "resource_ref_f1": _build_metric_summary(
            results,
            "resource_ref_match",
            value_field="f1",
        ),

        "uri_hallucination": _build_uri_hallucination_summary(results),
    }


def _subset_results_by_field(
    results: list[dict[str, Any]],
    field_name: str,
) -> dict[str, list[dict[str, Any]]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for result in results:
        entry_metadata = result.get("entry_metadata") or {}
        value = entry_metadata.get(field_name)
        group_key = str(value) if value is not None else "__missing__"
        grouped[group_key].append(result)

    return dict(sorted(grouped.items()))


def _build_slice_summary_for_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "item_count": len(results),
        "metrics": _build_core_metrics_summary(results),
        "error_categories": _build_error_category_counts(results),
        "response_time_seconds": _build_response_time_summary(results),
    }


def build_slice_summaries(
    results: list[dict[str, Any]],
    slice_fields: tuple[str, ...] = SUMMARY_SLICE_FIELDS,
) -> dict[str, Any]:
    slice_summaries: dict[str, Any] = {}

    for field_name in slice_fields:
        grouped_results = _subset_results_by_field(results, field_name)
        slice_summaries[field_name] = {
            field_value: _build_slice_summary_for_results(field_results)
            for field_value, field_results in grouped_results.items()
        }

    return slice_summaries


def build_benchmark_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_items": len(results),
        "metrics": _build_core_metrics_summary(results),
        "error_categories": _build_error_category_counts(results),
        "response_time_seconds": _build_response_time_summary(results),
        "slices": build_slice_summaries(results),
    }