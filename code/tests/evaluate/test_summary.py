from __future__ import annotations

from src.evaluate.summary import build_benchmark_summary


def metric(
    name: str,
    value: float | None,
    comparable: bool = True,
    metric_type: str = "test",
    **extra,
) -> dict:
    payload = {
        "metric": name,
        "type": metric_type,
        "comparable": comparable,
        "value": value,
    }
    payload.update(extra)
    return payload


def result_item(
    *,
    family: str,
    source_dataset: str,
    query_type: str,
    answer_type: str,
    query_shape: str,
    complexity_level: str,
    validation: dict,
    response_time_seconds: float = 1.0,
) -> dict:
    return {
        "entry_metadata": {
            "family": family,
            "source_dataset": source_dataset,
            "query_type": query_type,
            "answer_type": answer_type,
            "query_shape": query_shape,
            "complexity_level": complexity_level,
        },
        "validation": validation,
        "response_time_seconds": response_time_seconds,
    }


def validation_block(
    *,
    exact_match: float,
    precision: float,
    recall: float,
    f1: float,
    prediction_execution_success: float,
    category: str,
) -> dict:
    return {
        "query_extracted": metric("query_extracted", 1.0),
        "supported_query_form": metric("supported_query_form", 1.0),
        "query_form_match": metric("query_form_match", 1.0),
        "prediction_execution_success": metric(
            "prediction_execution_success",
            prediction_execution_success,
        ),
        "gold_execution_success": metric("gold_execution_success", 1.0),
        "answer_exact_match": metric(
            "answer_exact_match",
            exact_match,
            metric_type="answer_based",
        ),
        "answer_precision_recall_f1": {
            "metric": "answer_precision_recall_f1",
            "type": "answer_based",
            "comparable": True,
            "value": f1,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "answer_value_exact_match": metric(
            "answer_value_exact_match",
            exact_match,
            metric_type="answer_based",
            comparison_mode="value_only",
        ),
        "answer_value_precision_recall_f1": {
            "metric": "answer_value_precision_recall_f1",
            "type": "answer_based",
            "comparable": True,
            "value": f1,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "comparison_mode": "value_only",
        },
        "primary_error_category": category,
    }


def test_summary_maps_answer_precision_recall_f1_fields() -> None:
    results = [
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=validation_block(
                exact_match=1.0,
                precision=1.0,
                recall=1.0,
                f1=1.0,
                prediction_execution_success=1.0,
                category="success",
            ),
            response_time_seconds=2.0,
        ),
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=validation_block(
                exact_match=0.0,
                precision=0.5,
                recall=0.25,
                f1=0.3333,
                prediction_execution_success=1.0,
                category="answer_mismatch",
            ),
            response_time_seconds=4.0,
        ),
    ]

    summary = build_benchmark_summary(results)

    assert summary["total_items"] == 2

    metrics = summary["metrics"]

    assert metrics["answer_exact_match"]["mean"] == 0.5
    assert metrics["answer_exact_match"]["success_count"] == 1
    assert metrics["answer_exact_match"]["failure_count"] == 1
    assert metrics["answer_exact_match"]["success_rate"] == 0.5

    assert metrics["answer_precision"]["mean"] == 0.75
    assert metrics["answer_recall"]["mean"] == 0.625
    assert metrics["answer_f1"]["mean"] == 0.6666

    assert metrics["answer_precision"]["value_field"] == "precision"
    assert metrics["answer_recall"]["value_field"] == "recall"
    assert metrics["answer_f1"]["value_field"] == "f1"

    assert metrics["answer_value_exact_match"]["mean"] == 0.5
    assert metrics["answer_value_exact_match"]["success_count"] == 1
    assert metrics["answer_value_exact_match"]["failure_count"] == 1
    assert metrics["answer_value_exact_match"]["success_rate"] == 0.5

    assert metrics["answer_value_precision"]["mean"] == 0.75
    assert metrics["answer_value_recall"]["mean"] == 0.625
    assert metrics["answer_value_f1"]["mean"] == 0.6666

    assert metrics["answer_value_precision"]["value_field"] == "precision"
    assert metrics["answer_value_recall"]["value_field"] == "recall"
    assert metrics["answer_value_f1"]["value_field"] == "f1"


def test_summary_counts_non_comparable_answer_metrics() -> None:
    results = [
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation={
                "query_extracted": metric("query_extracted", 1.0),
                "supported_query_form": metric("supported_query_form", 1.0),
                "query_form_match": metric("query_form_match", 1.0),
                "prediction_execution_success": metric(
                    "prediction_execution_success",
                    0.0,
                ),
                "gold_execution_success": metric("gold_execution_success", 1.0),
                "answer_exact_match": metric(
                    "answer_exact_match",
                    None,
                    comparable=False,
                    metric_type="answer_based",
                    reason="prediction_error",
                ),
                "answer_precision_recall_f1": {
                    "metric": "answer_precision_recall_f1",
                    "type": "answer_based",
                    "comparable": False,
                    "value": None,
                    "reason": "prediction_error",
                },
                "answer_value_exact_match": {
                    "metric": "answer_value_exact_match",
                    "type": "answer_based",
                    "comparable": False,
                    "value": None,
                    "reason": "prediction_error",
                    "comparison_mode": "value_only",
                },
                "answer_value_precision_recall_f1": {
                    "metric": "answer_value_precision_recall_f1",
                    "type": "answer_based",
                    "comparable": False,
                    "value": None,
                    "precision": None,
                    "recall": None,
                    "f1": None,
                    "reason": "prediction_error",
                    "comparison_mode": "value_only",
                },
                "primary_error_category": "prediction_execution_error",
            },
        )
    ]

    summary = build_benchmark_summary(results)
    metrics = summary["metrics"]

    assert metrics["answer_exact_match"]["comparable_count"] == 0
    assert metrics["answer_exact_match"]["non_comparable_count"] == 1
    assert metrics["answer_exact_match"]["mean"] is None

    assert metrics["answer_precision"]["comparable_count"] == 0
    assert metrics["answer_precision"]["non_comparable_count"] == 1
    assert metrics["answer_precision"]["mean"] is None

    assert metrics["answer_recall"]["comparable_count"] == 0
    assert metrics["answer_recall"]["non_comparable_count"] == 1
    assert metrics["answer_recall"]["mean"] is None

    assert metrics["answer_f1"]["comparable_count"] == 0
    assert metrics["answer_f1"]["non_comparable_count"] == 1
    assert metrics["answer_f1"]["mean"] is None

    assert metrics["answer_value_exact_match"]["comparable_count"] == 0
    assert metrics["answer_value_exact_match"]["non_comparable_count"] == 1
    assert metrics["answer_value_exact_match"]["mean"] is None

    assert metrics["answer_value_precision"]["comparable_count"] == 0
    assert metrics["answer_value_precision"]["non_comparable_count"] == 1
    assert metrics["answer_value_precision"]["mean"] is None

    assert metrics["answer_value_recall"]["comparable_count"] == 0
    assert metrics["answer_value_recall"]["non_comparable_count"] == 1
    assert metrics["answer_value_recall"]["mean"] is None

    assert metrics["answer_value_f1"]["comparable_count"] == 0
    assert metrics["answer_value_f1"]["non_comparable_count"] == 1
    assert metrics["answer_value_f1"]["mean"] is None


def test_summary_builds_slice_metrics() -> None:
    results = [
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=validation_block(
                exact_match=1.0,
                precision=1.0,
                recall=1.0,
                f1=1.0,
                prediction_execution_success=1.0,
                category="success",
            ),
        ),
        result_item(
            family="empirical_research_practice",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="multi_hop",
            complexity_level="medium",
            validation=validation_block(
                exact_match=0.0,
                precision=0.0,
                recall=0.0,
                f1=0.0,
                prediction_execution_success=1.0,
                category="answer_mismatch",
            ),
        ),
    ]

    summary = build_benchmark_summary(results)

    family_slices = summary["slices"]["family"]

    assert family_slices["nlp4re"]["item_count"] == 1
    assert family_slices["nlp4re"]["metrics"]["answer_f1"]["mean"] == 1.0

    assert family_slices["empirical_research_practice"]["item_count"] == 1
    assert (
        family_slices["empirical_research_practice"]["metrics"]["answer_f1"]["mean"]
        == 0.0
    )


def test_summary_counts_error_categories() -> None:
    results = [
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=validation_block(
                exact_match=1.0,
                precision=1.0,
                recall=1.0,
                f1=1.0,
                prediction_execution_success=1.0,
                category="success",
            ),
        ),
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=validation_block(
                exact_match=0.0,
                precision=0.0,
                recall=0.0,
                f1=0.0,
                prediction_execution_success=1.0,
                category="answer_mismatch",
            ),
        ),
    ]

    summary = build_benchmark_summary(results)

    assert summary["error_categories"] == {
        "answer_mismatch": 1,
        "success": 1,
    }


def test_summary_response_time_statistics() -> None:
    results = [
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=validation_block(
                exact_match=1.0,
                precision=1.0,
                recall=1.0,
                f1=1.0,
                prediction_execution_success=1.0,
                category="success",
            ),
            response_time_seconds=2.0,
        ),
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=validation_block(
                exact_match=0.0,
                precision=0.5,
                recall=0.5,
                f1=0.5,
                prediction_execution_success=1.0,
                category="answer_mismatch",
            ),
            response_time_seconds=4.0,
        ),
    ]

    summary = build_benchmark_summary(results)

    assert summary["response_time_seconds"] == {
        "count": 2,
        "mean_seconds": 3.0,
        "min_seconds": 2.0,
        "max_seconds": 4.0,
        "total_seconds": 6.0,
    }


def kg_ref_metric(
    metric_key: str,
    *,
    ref_kind: str,
    precision: float,
    recall: float,
    f1: float,
) -> dict:
    return {
        "metric": "kg_ref_match",
        "type": "query_based",
        "comparable": True,
        "value": f1,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "ref_kind": ref_kind,
        "matched_ref_count": 1,
        "prediction_ref_count": 1,
        "gold_ref_count": 1,
        "missing_gold_refs": [],
        "extra_predicted_refs": [],
        "matched_refs": [],
    }


def test_summary_maps_kg_reference_metric_fields() -> None:
    first_validation = validation_block(
        exact_match=1.0,
        precision=1.0,
        recall=1.0,
        f1=1.0,
        prediction_execution_success=1.0,
        category="success",
    )
    first_validation.update(
        {
            "kg_ref_match": kg_ref_metric(
                "kg_ref_match",
                ref_kind="all",
                precision=1.0,
                recall=1.0,
                f1=1.0,
            ),
            "predicate_ref_match": kg_ref_metric(
                "predicate_ref_match",
                ref_kind="predicate",
                precision=0.5,
                recall=0.5,
                f1=0.5,
            ),
            "class_ref_match": kg_ref_metric(
                "class_ref_match",
                ref_kind="class",
                precision=1.0,
                recall=1.0,
                f1=1.0,
            ),
            "resource_ref_match": kg_ref_metric(
                "resource_ref_match",
                ref_kind="resource",
                precision=1.0,
                recall=1.0,
                f1=1.0,
            ),
        }
    )

    second_validation = validation_block(
        exact_match=0.0,
        precision=0.0,
        recall=0.0,
        f1=0.0,
        prediction_execution_success=1.0,
        category="answer_mismatch",
    )
    second_validation.update(
        {
            "kg_ref_match": kg_ref_metric(
                "kg_ref_match",
                ref_kind="all",
                precision=0.0,
                recall=0.0,
                f1=0.0,
            ),
            "predicate_ref_match": kg_ref_metric(
                "predicate_ref_match",
                ref_kind="predicate",
                precision=1.0,
                recall=1.0,
                f1=1.0,
            ),
            "class_ref_match": kg_ref_metric(
                "class_ref_match",
                ref_kind="class",
                precision=0.0,
                recall=0.0,
                f1=0.0,
            ),
            "resource_ref_match": kg_ref_metric(
                "resource_ref_match",
                ref_kind="resource",
                precision=0.5,
                recall=0.5,
                f1=0.5,
            ),
        }
    )

    results = [
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=first_validation,
        ),
        result_item(
            family="empirical_research_practice",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="multi_hop",
            complexity_level="medium",
            validation=second_validation,
        ),
    ]

    summary = build_benchmark_summary(results)
    metrics = summary["metrics"]

    assert metrics["kg_ref_precision"]["mean"] == 0.5
    assert metrics["kg_ref_recall"]["mean"] == 0.5
    assert metrics["kg_ref_f1"]["mean"] == 0.5

    assert metrics["predicate_ref_precision"]["mean"] == 0.75
    assert metrics["predicate_ref_recall"]["mean"] == 0.75
    assert metrics["predicate_ref_f1"]["mean"] == 0.75

    assert metrics["class_ref_precision"]["mean"] == 0.5
    assert metrics["class_ref_recall"]["mean"] == 0.5
    assert metrics["class_ref_f1"]["mean"] == 0.5

    assert metrics["resource_ref_precision"]["mean"] == 0.75
    assert metrics["resource_ref_recall"]["mean"] == 0.75
    assert metrics["resource_ref_f1"]["mean"] == 0.75

    assert metrics["kg_ref_precision"]["value_field"] == "precision"
    assert metrics["kg_ref_recall"]["value_field"] == "recall"
    assert metrics["kg_ref_f1"]["value_field"] == "f1"


def test_summary_aggregates_uri_hallucination() -> None:
    first_validation = validation_block(
        exact_match=1.0,
        precision=1.0,
        recall=1.0,
        f1=1.0,
        prediction_execution_success=1.0,
        category="success",
    )
    first_validation["uri_hallucination"] = {
        "metric": "uri_hallucination",
        "type": "query_based",
        "comparable": True,
        "value": 0.0,
        "has_hallucination": False,
        "hallucinated_ref_rate": 0.0,
        "checked_ref_kinds": ["predicate", "class"],
        "prediction_ref_count": 3,
        "allowed_ref_count": 161,
        "hallucinated_ref_count": 0,
        "hallucinated_refs": [],
        "checked_prediction_refs": ["orkgc:C121001", "orkgp:P31", "orkgp:P181003"],
    }

    second_validation = validation_block(
        exact_match=0.0,
        precision=0.0,
        recall=0.0,
        f1=0.0,
        prediction_execution_success=1.0,
        category="answer_mismatch",
    )
    second_validation["uri_hallucination"] = {
        "metric": "uri_hallucination",
        "type": "query_based",
        "comparable": True,
        "value": 1.0,
        "has_hallucination": True,
        "hallucinated_ref_rate": 0.25,
        "checked_ref_kinds": ["predicate", "class"],
        "prediction_ref_count": 4,
        "allowed_ref_count": 161,
        "hallucinated_ref_count": 1,
        "hallucinated_refs": ["orkgp:P999999999"],
        "checked_prediction_refs": [
            "orkgc:C121001",
            "orkgp:P31",
            "orkgp:P181003",
            "orkgp:P999999999",
        ],
    }

    third_validation = validation_block(
        exact_match=0.0,
        precision=0.0,
        recall=0.0,
        f1=0.0,
        prediction_execution_success=0.0,
        category="prediction_execution_error",
    )
    third_validation["uri_hallucination"] = {
        "metric": "uri_hallucination",
        "type": "query_based",
        "comparable": False,
        "value": None,
        "has_hallucination": None,
        "hallucinated_ref_rate": None,
        "reason": "prediction_query_missing",
        "checked_ref_kinds": ["predicate", "class"],
        "prediction_ref_count": None,
        "allowed_ref_count": 161,
        "hallucinated_ref_count": None,
        "hallucinated_refs": [],
        "checked_prediction_refs": [],
    }

    results = [
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=first_validation,
        ),
        result_item(
            family="nlp4re",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="single_hop",
            complexity_level="easy",
            validation=second_validation,
        ),
        result_item(
            family="empirical_research_practice",
            source_dataset="final_test",
            query_type="SELECT",
            answer_type="resources",
            query_shape="multi_hop",
            complexity_level="medium",
            validation=third_validation,
        ),
    ]

    summary = build_benchmark_summary(results)

    metric = summary["metrics"]["uri_hallucination"]

    assert metric["metric_name"] == "uri_hallucination"
    assert metric["type"] == "query_based"
    assert metric["comparable_count"] == 2
    assert metric["non_comparable_count"] == 1
    assert metric["hallucinated_item_count"] == 1
    assert metric["clean_item_count"] == 1
    assert metric["hallucinated_item_rate"] == 0.5
    assert metric["total_hallucinated_ref_count"] == 1
    assert metric["mean_hallucinated_ref_count"] == 0.5
    assert metric["mean_hallucinated_ref_rate"] == 0.125
