"""Aggregate per-example evaluation results into benchmark summaries."""

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
    """Collect comparable numeric metric values and comparable counts."""
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
    """Summarize one numeric metric across all result entries."""
    values, comparable_count, non_comparable_count = _numeric_metric_values(
        results=results,
        metric_name=metric_name,
        value_field=value_field,
    )

    summary: dict[str, Any] = {
        "metric_name": metric_name,
        "value_field": value_field,
        "comparable_count": comparable_count,
        "valid_count": comparable_count,
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

def _build_pgmr_unmapped_placeholders_summary(results: list[dict]) -> dict:
    """Summarize unresolved PGMR placeholder diagnostics."""
    metrics = [
        _get_validation_metric(result, "pgmr_unmapped_placeholders")
        for result in results
    ]
    metrics = [metric for metric in metrics if metric is not None]

    comparable_metrics = [
        metric for metric in metrics if metric.get("comparable") is True
    ]
    non_comparable_metrics = [
        metric for metric in metrics if metric.get("comparable") is not True
    ]

    not_pgmr_mode_count = sum(
        1 for metric in non_comparable_metrics
        if metric.get("reason") == "not_pgmr_mode"
    )

    unmapped_item_count = sum(
        1 for metric in comparable_metrics
        if metric.get("has_unmapped_placeholders") is True
    )
    clean_item_count = sum(
        1 for metric in comparable_metrics
        if metric.get("has_unmapped_placeholders") is False
    )

    placeholder_counts = [
        metric.get("unmapped_placeholder_count")
        for metric in comparable_metrics
        if isinstance(metric.get("unmapped_placeholder_count"), (int, float))
    ]

    comparable_count = len(comparable_metrics)
    non_comparable_count = len(non_comparable_metrics)

    total_unmapped_placeholder_count = int(sum(placeholder_counts))
    mean_unmapped_placeholder_count = (
        None
        if not placeholder_counts
        else round(sum(placeholder_counts) / len(placeholder_counts), 4)
    )

    unmapped_item_rate = (
        None
        if comparable_count == 0
        else round(unmapped_item_count / comparable_count, 4)
    )

    return {
        "metric_name": "pgmr_unmapped_placeholders",
        "type": "pgmr_based",
        "comparable_count": comparable_count,
        "non_comparable_count": non_comparable_count,
        "not_pgmr_mode_count": not_pgmr_mode_count,
        "unmapped_item_count": unmapped_item_count,
        "clean_item_count": clean_item_count,
        "unmapped_item_rate": unmapped_item_rate,
        "total_unmapped_placeholder_count": total_unmapped_placeholder_count,
        "mean_unmapped_placeholder_count": mean_unmapped_placeholder_count,
    }


def _count_pgmr_resolution_events(results: list[dict[str, Any]]) -> dict[str, int]:
    """Count PGMR alias, similarity, suggestion, and unmapped diagnostics."""
    alias_items = 0
    auto_items = 0
    suggested_items = 0
    still_unmapped_items = 0

    alias_placeholders = 0
    auto_placeholders = 0
    suggested_placeholders = 0
    still_unmapped_placeholders = 0

    for result in results:
        alias_mappings = result.get("pgmr_alias_mappings") or []
        auto_mappings = result.get("pgmr_auto_mappings") or []
        suggestions = result.get("pgmr_mapping_suggestions") or []
        unmapped = (
            result.get("pgmr_unmapped_placeholders")
            or result.get("pgmr_missing_mapping_tokens")
            or []
        )

        if alias_mappings:
            alias_items += 1
            alias_placeholders += len(alias_mappings)

        if auto_mappings:
            auto_items += 1
            auto_placeholders += len(auto_mappings)

        if suggestions:
            suggested_items += 1
            suggested_placeholders += len(suggestions)

        if unmapped:
            still_unmapped_items += 1
            still_unmapped_placeholders += len(unmapped)

    return {
        "pgmr_alias_mapped_item_count": alias_items,
        "pgmr_alias_mapped_placeholder_count": alias_placeholders,
        "pgmr_auto_mapped_item_count": auto_items,
        "pgmr_auto_mapped_placeholder_count": auto_placeholders,
        "pgmr_suggested_item_count": suggested_items,
        "pgmr_suggested_placeholder_count": suggested_placeholders,
        "pgmr_still_unmapped_item_count": still_unmapped_items,
        "pgmr_still_unmapped_placeholder_count": still_unmapped_placeholders,
    }

def _build_uri_hallucination_summary(results: list[dict]) -> dict:
    """Summarize predicted ORKG references that are outside local memory."""
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
    """Build the main metric block for benchmark_summary.json."""
    return {
        "query_extracted": _build_metric_summary(results, "query_extracted"),
        "supported_query_form": _build_metric_summary(results, "supported_query_form"),
        "query_form_match": _build_metric_summary(results, "query_form_match"),
        "prediction_execution_success": _build_metric_summary(
            results,
            "prediction_execution_success",
        ),
        "query_normalized_exact_match": _build_metric_summary(
            results,
            "query_normalized_exact_match",
        ),
        "query_bleu": _build_metric_summary(
            results,
            "query_bleu",
            value_field="bleu",
        ),
        "query_rouge1_f1": _build_metric_summary(
            results,
            "query_rouge1_f1",
            value_field="f1",
        ),
        "query_rouge2_f1": _build_metric_summary(
            results,
            "query_rouge2_f1",
            value_field="f1",
        ),
        "query_rougeL_f1": _build_metric_summary(
            results,
            "query_rougeL_f1",
            value_field="f1",
        ),
        "pgmr_rouge1_f1": _build_metric_summary(
            results,
            "pgmr_rouge1_f1",
            value_field="f1",
        ),
        "pgmr_rouge2_f1": _build_metric_summary(
            results,
            "pgmr_rouge2_f1",
            value_field="f1",
        ),
        "pgmr_rougeL_f1": _build_metric_summary(
            results,
            "pgmr_rougeL_f1",
            value_field="f1",
        ),
        "sparql_structure_precision": _build_metric_summary(
            results,
            "sparql_structure_match",
            value_field="precision",
        ),
        "sparql_structure_recall": _build_metric_summary(
            results,
            "sparql_structure_match",
            value_field="recall",
        ),
        "sparql_structure_f1": _build_metric_summary(
            results,
            "sparql_structure_match",
            value_field="f1",
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
        "answer_cell_value_precision": _build_metric_summary(
            results,
            "answer_cell_value_precision_recall_f1",
            value_field="precision",
        ),
        "answer_cell_value_recall": _build_metric_summary(
            results,
            "answer_cell_value_precision_recall_f1",
            value_field="recall",
        ),
        "answer_cell_value_f1": _build_metric_summary(
            results,
            "answer_cell_value_precision_recall_f1",
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
        "pgmr_unmapped_placeholders": _build_pgmr_unmapped_placeholders_summary(results),
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
    summary = {
        "total_items": len(results),
        "metrics": _build_core_metrics_summary(results),
        "error_categories": _build_error_category_counts(results),
        "response_time_seconds": _build_response_time_summary(results),
        "slices": build_slice_summaries(results),
    }
    summary.update(_count_pgmr_resolution_events(results))
    return summary
