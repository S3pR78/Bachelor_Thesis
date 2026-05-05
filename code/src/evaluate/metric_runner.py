"""Collect all per-example evaluation metrics into one validation payload."""

from __future__ import annotations

from typing import Any

from src.evaluate.metrics.answer_exact_match import compute_answer_exact_match
from src.evaluate.metrics.answer_cell_value_precision_recall_f1 import (
    compute_answer_cell_value_precision_recall_f1,
)
from src.evaluate.metrics.answer_precision_recall_f1 import (
    compute_answer_precision_recall_f1,
)
from src.evaluate.metrics.gold_execution_success import compute_gold_execution_success
from src.evaluate.metrics.prediction_execution_success import (
    compute_prediction_execution_success,
)
from src.evaluate.metrics.primary_error_category import compute_primary_error_category
from src.evaluate.metrics.query_extracted import compute_query_extracted
from src.evaluate.metrics.query_form_match import compute_query_form_match
from src.evaluate.metrics.supported_query_form import compute_supported_query_form
from src.evaluate.metrics.answer_value_exact_match import (
    compute_answer_value_exact_match,
)
from src.evaluate.metrics.answer_value_precision_recall_f1 import (
    compute_answer_value_precision_recall_f1,
)
from src.evaluate.metrics.kg_ref_match import compute_kg_ref_match
from src.evaluate.metrics.uri_hallucination import compute_uri_hallucination
from src.evaluate.metrics.pgmr_unmapped_placeholders import (
    build_pgmr_unmapped_placeholders_not_applicable,
    compute_pgmr_unmapped_placeholders,
)

from src.evaluate.metrics.query_normalized_exact_match import (
    compute_query_normalized_exact_match,
)
from src.evaluate.metrics.query_bleu import compute_query_bleu
from src.evaluate.metrics.query_rouge import compute_query_rouge_scores
from src.evaluate.metrics.sparql_structure_match import (
    compute_sparql_structure_match,
)


def build_validation_metrics(
    *,
    has_extracted_query: bool,
    prediction_query_form: str | None,
    gold_query_form: str | None,
    prediction_execution: dict[str, Any] | None,
    gold_execution: dict[str, Any] | None,
    endpoint_url: str | None,
    prediction_query: str | None = None,
    gold_query: str | None = None,
    prediction_pgmr_query: str | None = None,
    gold_pgmr_query: str | None = None,
    allowed_kg_refs: set[str] | frozenset[str] | None = None,
    enable_pgmr_metrics: bool = False,
) -> dict[str, Any]:
    """Compute the complete metric set for one prediction/gold query pair."""
    prediction_execution_for_status = prediction_execution or {}
    gold_execution_for_status = gold_execution or {}

    # Query-status metrics can be computed even when endpoint execution is off.
    query_extracted = compute_query_extracted(
        has_extracted_query=has_extracted_query,
    )

    supported_query_form = compute_supported_query_form(
        has_extracted_query=has_extracted_query,
        prediction_query_form=prediction_query_form,
    )

    query_form_match = compute_query_form_match(
        prediction_query_form=prediction_query_form,
        gold_query_form=gold_query_form,
    )

    prediction_execution_success = compute_prediction_execution_success(
        has_extracted_query=has_extracted_query,
        prediction_query_form=prediction_query_form,
        prediction_execution=prediction_execution_for_status,
        endpoint_url=endpoint_url,
    )

    gold_execution_success = compute_gold_execution_success(
        gold_query_form=gold_query_form,
        gold_execution=gold_execution_for_status,
        endpoint_url=endpoint_url,
    )

    answer_exact_match = compute_answer_exact_match(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    answer_precision_recall_f1 = compute_answer_precision_recall_f1(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    answer_value_exact_match = compute_answer_value_exact_match(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    answer_value_precision_recall_f1 = compute_answer_value_precision_recall_f1(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )

    answer_cell_value_precision_recall_f1 = compute_answer_cell_value_precision_recall_f1(
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
    )


    # KG-reference metrics check whether the model used the expected ORKG refs.
    kg_ref_match = compute_kg_ref_match(
        prediction_query=prediction_query,
        gold_query=gold_query,
        ref_kind="all",
    )



    predicate_ref_match = compute_kg_ref_match(
        prediction_query=prediction_query,
        gold_query=gold_query,
        ref_kind="predicate",
    )

    class_ref_match = compute_kg_ref_match(
        prediction_query=prediction_query,
        gold_query=gold_query,
        ref_kind="class",
    )

    resource_ref_match = compute_kg_ref_match(
        prediction_query=prediction_query,
        gold_query=gold_query,
        ref_kind="resource",
    )

    uri_hallucination = compute_uri_hallucination(
        prediction_query=prediction_query,
        allowed_refs=allowed_kg_refs,
        checked_ref_kinds=("predicate", "class"),
    )

    # PGMR placeholder diagnostics only make sense in PGMR-producing runs.
    if enable_pgmr_metrics:
        pgmr_unmapped_placeholders = compute_pgmr_unmapped_placeholders(
            prediction_query=prediction_query,
        )
    else:
        pgmr_unmapped_placeholders = build_pgmr_unmapped_placeholders_not_applicable(
            reason="not_pgmr_mode",
        )

    query_normalized_exact_match = compute_query_normalized_exact_match(
        prediction_query=prediction_query,
        gold_query=gold_query,
    )

    query_bleu = compute_query_bleu(
        prediction_query=prediction_query,
        gold_query=gold_query,
    )

    query_rouge_scores = compute_query_rouge_scores(
        prediction_query=prediction_query,
        gold_query=gold_query,
        metric_prefix="query",
    )

    if enable_pgmr_metrics and gold_pgmr_query:
        pgmr_rouge_scores = compute_query_rouge_scores(
            prediction_query=prediction_pgmr_query,
            gold_query=gold_pgmr_query,
            metric_prefix="pgmr",
        )
    else:
        pgmr_rouge_scores = compute_query_rouge_scores(
            prediction_query=None,
            gold_query=gold_pgmr_query,
            metric_prefix="pgmr",
        )

    sparql_structure_match = compute_sparql_structure_match(
        prediction_query=prediction_query,
        gold_query=gold_query,
    )

    # A single coarse category makes error inspection easier in summaries.
    primary_error_category = compute_primary_error_category(
        has_extracted_query=has_extracted_query,
        prediction_query_form=prediction_query_form,
        gold_query_form=gold_query_form,
        prediction_execution=prediction_execution_for_status,
        gold_execution=gold_execution_for_status,
        answer_exact_match=answer_exact_match,
        endpoint_url=endpoint_url,
    )

    return {
        "query_extracted": query_extracted,
        "supported_query_form": supported_query_form,
        "query_form_match": query_form_match,
        "prediction_execution_success": prediction_execution_success,
        "gold_execution_success": gold_execution_success,
        "answer_exact_match": answer_exact_match,
        "answer_precision_recall_f1": answer_precision_recall_f1,
        "answer_value_exact_match": answer_value_exact_match,
        "answer_value_precision_recall_f1": answer_value_precision_recall_f1,
        "answer_cell_value_precision_recall_f1": answer_cell_value_precision_recall_f1,
        "kg_ref_match": kg_ref_match,
        "predicate_ref_match": predicate_ref_match,
        "class_ref_match": class_ref_match,
        "resource_ref_match": resource_ref_match,
        "uri_hallucination": uri_hallucination,
        "pgmr_unmapped_placeholders": pgmr_unmapped_placeholders,
        "query_normalized_exact_match": query_normalized_exact_match,
        "query_bleu": query_bleu,
        **query_rouge_scores,
        **pgmr_rouge_scores,
        "sparql_structure_match": sparql_structure_match,
        "primary_error_category": primary_error_category,
    }
