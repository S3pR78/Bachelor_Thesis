from __future__ import annotations

from src.evaluate.metric_runner import build_validation_metrics


ENDPOINT_URL = "https://www.orkg.org/triplestore"

ALLOWED_KG_REFS = frozenset(
    {
        "orkgp:P31",
        "orkgp:P181003",
        "orkgp:P181004",
        "orkgc:C121001",
    }
)


def uri(value: str) -> dict:
    return {
        "type": "uri",
        "value": value,
    }


def ok_select(bindings: list[dict]) -> dict:
    return {
        "status": "ok",
        "result_type": "select",
        "response_json": {
            "head": {"vars": []},
            "results": {"bindings": bindings},
        },
    }


def error_execution(reason: str = "endpoint_bad_request") -> dict:
    return {
        "status": "error",
        "error": reason,
    }


def test_metric_runner_builds_successful_validation_block() -> None:
    prediction_execution = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
        ]
    )
    gold_execution = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
        ]
    )

    prediction_query = """
    SELECT ?paper WHERE {
        ?paper orkgp:P31 ?contribution .
        ?contribution a orkgc:C121001 .
        ?contribution orkgp:P181003 ?task .
    }
    """

    gold_query = """
    SELECT ?paper WHERE {
        ?paper orkgp:P31 ?contribution .
        ?contribution a orkgc:C121001 .
        ?contribution orkgp:P181003 ?task .
    }
    """

    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
        endpoint_url=ENDPOINT_URL,
        prediction_query=prediction_query,
        gold_query=gold_query,
        allowed_kg_refs=ALLOWED_KG_REFS,
    )

    assert validation["query_extracted"]["value"] == 1.0
    assert validation["supported_query_form"]["value"] == 1.0
    assert validation["query_form_match"]["value"] == 1.0
    assert validation["prediction_execution_success"]["value"] == 1.0
    assert validation["gold_execution_success"]["value"] == 1.0

    assert validation["answer_exact_match"]["comparable"] is True
    assert validation["answer_exact_match"]["value"] == 1.0

    assert validation["answer_precision_recall_f1"]["comparable"] is True
    assert validation["answer_precision_recall_f1"]["precision"] == 1.0
    assert validation["answer_precision_recall_f1"]["recall"] == 1.0
    assert validation["answer_precision_recall_f1"]["f1"] == 1.0

    assert validation["answer_value_exact_match"]["comparable"] is True
    assert validation["answer_value_exact_match"]["value"] == 1.0
    assert validation["answer_value_exact_match"]["comparison_mode"] == "value_only"

    assert validation["answer_value_precision_recall_f1"]["comparable"] is True
    assert validation["answer_value_precision_recall_f1"]["precision"] == 1.0
    assert validation["answer_value_precision_recall_f1"]["recall"] == 1.0
    assert validation["answer_value_precision_recall_f1"]["f1"] == 1.0
    assert (
        validation["answer_value_precision_recall_f1"]["comparison_mode"]
        == "value_only"
    )

    assert validation["uri_hallucination"]["comparable"] is True
    assert validation["uri_hallucination"]["value"] == 0.0
    assert validation["uri_hallucination"]["has_hallucination"] is False
    assert validation["uri_hallucination"]["hallucinated_refs"] == []

    assert validation["pgmr_unmapped_placeholders"]["comparable"] is False
    assert validation["pgmr_unmapped_placeholders"]["value"] is None
    assert validation["pgmr_unmapped_placeholders"]["reason"] == "not_pgmr_mode"
    assert (
        validation["pgmr_unmapped_placeholders"]["has_unmapped_placeholders"]
        is None
    )
    assert (
        validation["pgmr_unmapped_placeholders"]["unmapped_placeholder_count"]
        is None
    )
    assert validation["pgmr_unmapped_placeholders"]["unmapped_placeholders"] == []
    assert validation["pgmr_unmapped_placeholders"]["unmapped_placeholders"] == []

    assert validation["primary_error_category"] == "success"


def test_metric_runner_marks_prediction_execution_error() -> None:
    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=error_execution(),
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
    )

    assert validation["query_extracted"]["value"] == 1.0
    assert validation["supported_query_form"]["value"] == 1.0
    assert validation["query_form_match"]["value"] == 1.0

    assert validation["prediction_execution_success"]["comparable"] is True
    assert validation["prediction_execution_success"]["value"] == 0.0

    assert validation["gold_execution_success"]["comparable"] is True
    assert validation["gold_execution_success"]["value"] == 1.0

    assert validation["answer_exact_match"]["comparable"] is False
    assert validation["answer_exact_match"]["value"] is None
    assert validation["answer_exact_match"]["reason"] == "prediction_error"

    assert validation["answer_precision_recall_f1"]["comparable"] is False
    assert validation["answer_precision_recall_f1"]["value"] is None
    assert validation["answer_precision_recall_f1"]["reason"] == "prediction_error"

    assert validation["primary_error_category"] == "prediction_execution_error"

    assert validation["answer_value_exact_match"]["comparable"] is False

    assert validation["answer_value_exact_match"]["value"] is None
    assert validation["answer_value_exact_match"]["reason"] == "prediction_error"

    assert validation["answer_value_precision_recall_f1"]["comparable"] is False
    assert validation["answer_value_precision_recall_f1"]["value"] is None
    assert validation["answer_value_precision_recall_f1"]["reason"] == "prediction_error"


def test_metric_runner_marks_answer_mismatch_for_executable_wrong_answer() -> None:
    prediction_execution = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
        ]
    )
    gold_execution = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R2")},
        ]
    )

    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
        endpoint_url=ENDPOINT_URL,
    )

    assert validation["prediction_execution_success"]["value"] == 1.0
    assert validation["gold_execution_success"]["value"] == 1.0

    assert validation["answer_exact_match"]["comparable"] is True
    assert validation["answer_exact_match"]["value"] == 0.0

    assert validation["answer_precision_recall_f1"]["comparable"] is True
    assert validation["answer_precision_recall_f1"]["precision"] == 0.0
    assert validation["answer_precision_recall_f1"]["recall"] == 0.0
    assert validation["answer_precision_recall_f1"]["f1"] == 0.0

    assert validation["primary_error_category"] == "answer_mismatch"


def test_metric_runner_marks_extraction_failure() -> None:
    validation = build_validation_metrics(
        has_extracted_query=False,
        prediction_query_form=None,
        gold_query_form="select",
        prediction_execution=None,
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
    )

    assert validation["query_extracted"]["value"] == 0.0

    assert validation["supported_query_form"]["comparable"] is False
    assert validation["supported_query_form"]["reason"] == "no_extracted_query"

    assert validation["prediction_execution_success"]["comparable"] is False
    assert (
        validation["prediction_execution_success"]["reason"]
        == "unsupported_or_missing_prediction_query"
    )

    assert validation["answer_exact_match"]["comparable"] is False
    assert validation["answer_exact_match"]["reason"] == "prediction_missing"

    assert validation["primary_error_category"] == "extraction_failure"


def test_metric_runner_marks_no_endpoint_as_not_comparable() -> None:
    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=None,
        gold_execution=None,
        endpoint_url=None,
    )

    assert validation["prediction_execution_success"]["comparable"] is False
    assert validation["prediction_execution_success"]["reason"] == "no_endpoint_configured"

    assert validation["gold_execution_success"]["comparable"] is False
    assert validation["gold_execution_success"]["reason"] == "no_endpoint_configured"

    assert validation["primary_error_category"] == "not_evaluated_no_endpoint"


def test_metric_runner_computes_value_only_metrics_for_different_variable_names() -> None:
    prediction_execution = ok_select(
        [
            {"name": uri("http://orkg.org/orkg/resource/R1")},
        ]
    )
    gold_execution = ok_select(
        [
            {"paper": uri("http://orkg.org/orkg/resource/R1")},
        ]
    )

    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=prediction_execution,
        gold_execution=gold_execution,
        endpoint_url=ENDPOINT_URL,
    )

    assert validation["answer_exact_match"]["comparable"] is True
    assert validation["answer_exact_match"]["value"] == 0.0

    assert validation["answer_precision_recall_f1"]["comparable"] is True
    assert validation["answer_precision_recall_f1"]["f1"] == 0.0

    assert validation["answer_value_exact_match"]["comparable"] is True
    assert validation["answer_value_exact_match"]["value"] == 1.0
    assert validation["answer_value_exact_match"]["comparison_mode"] == "value_only"

    assert validation["answer_value_precision_recall_f1"]["comparable"] is True
    assert validation["answer_value_precision_recall_f1"]["precision"] == 1.0
    assert validation["answer_value_precision_recall_f1"]["recall"] == 1.0
    assert validation["answer_value_precision_recall_f1"]["f1"] == 1.0
    assert (
        validation["answer_value_precision_recall_f1"]["comparison_mode"]
        == "value_only"
    )


def test_metric_runner_computes_kg_reference_metrics() -> None:
    prediction_query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181004 ?taskType .
    }
    """

    gold_query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
        prediction_query=prediction_query,
        gold_query=gold_query,
    )

    assert validation["kg_ref_match"]["comparable"] is True
    assert validation["kg_ref_match"]["ref_kind"] == "all"
    assert validation["kg_ref_match"]["matched_refs"] == [
        "orkgc:C121001",
        "orkgp:P31",
    ]
    assert validation["kg_ref_match"]["missing_gold_refs"] == ["orkgp:P181003"]
    assert validation["kg_ref_match"]["extra_predicted_refs"] == ["orkgp:P181004"]
    assert validation["kg_ref_match"]["f1"] == 0.6667

    assert validation["predicate_ref_match"]["comparable"] is True
    assert validation["predicate_ref_match"]["ref_kind"] == "predicate"
    assert validation["predicate_ref_match"]["matched_refs"] == ["orkgp:P31"]
    assert validation["predicate_ref_match"]["missing_gold_refs"] == ["orkgp:P181003"]
    assert validation["predicate_ref_match"]["extra_predicted_refs"] == [
        "orkgp:P181004"
    ]
    assert validation["predicate_ref_match"]["f1"] == 0.5

    assert validation["class_ref_match"]["comparable"] is True
    assert validation["class_ref_match"]["ref_kind"] == "class"
    assert validation["class_ref_match"]["matched_refs"] == ["orkgc:C121001"]
    assert validation["class_ref_match"]["f1"] == 1.0

    assert validation["resource_ref_match"]["comparable"] is True
    assert validation["resource_ref_match"]["ref_kind"] == "resource"
    assert validation["resource_ref_match"]["prediction_ref_count"] == 0
    assert validation["resource_ref_match"]["gold_ref_count"] == 0
    assert validation["resource_ref_match"]["f1"] == 1.0


def test_metric_runner_marks_kg_reference_metrics_not_comparable_without_prediction_query() -> None:
    validation = build_validation_metrics(
        has_extracted_query=False,
        prediction_query_form=None,
        gold_query_form="select",
        prediction_execution=None,
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
        prediction_query=None,
        gold_query="""
        SELECT ?paper WHERE {
          ?paper orkgp:P31 ?contribution .
          ?contribution a orkgc:C121001 .
        }
        """,
    )

    assert validation["kg_ref_match"]["comparable"] is False
    assert validation["kg_ref_match"]["reason"] == "prediction_query_missing"

    assert validation["predicate_ref_match"]["comparable"] is False
    assert validation["predicate_ref_match"]["reason"] == "prediction_query_missing"

    assert validation["class_ref_match"]["comparable"] is False
    assert validation["class_ref_match"]["reason"] == "prediction_query_missing"

    assert validation["resource_ref_match"]["comparable"] is False
    assert validation["resource_ref_match"]["reason"] == "prediction_query_missing"


def test_metric_runner_computes_uri_hallucination() -> None:
    prediction_query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P999999999 ?x .
    }
    """

    gold_query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
        prediction_query=prediction_query,
        gold_query=gold_query,
        allowed_kg_refs=ALLOWED_KG_REFS,
    )

    assert validation["uri_hallucination"]["comparable"] is True
    assert validation["uri_hallucination"]["value"] == 1.0
    assert validation["uri_hallucination"]["has_hallucination"] is True
    assert validation["uri_hallucination"]["hallucinated_ref_count"] == 1
    assert validation["uri_hallucination"]["hallucinated_refs"] == [
        "orkgp:P999999999"
    ]


def test_metric_runner_marks_uri_hallucination_not_comparable_without_memory() -> None:
    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
        prediction_query="""
        SELECT ?paper WHERE {
          ?paper orkgp:P31 ?contribution .
        }
        """,
        gold_query="""
        SELECT ?paper WHERE {
          ?paper orkgp:P31 ?contribution .
        }
        """,
        allowed_kg_refs=None,
    )

    assert validation["uri_hallucination"]["comparable"] is False
    assert validation["uri_hallucination"]["reason"] == "allowed_refs_missing"


def test_metric_runner_computes_pgmr_unmapped_placeholders() -> None:
    prediction_query = """
    SELECT ?paper WHERE {
      ?contribution {{NLP_TASK_PROPERTY}} ?task .
      ?contribution <UNKNOWN_CLASS> ?x .
    }
    """

    gold_query = """
    SELECT ?paper WHERE {
      ?paper orkgp:P31 ?contribution .
      ?contribution a orkgc:C121001 .
      ?contribution orkgp:P181003 ?task .
    }
    """

    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
        prediction_query=prediction_query,
        gold_query=gold_query,
        allowed_kg_refs=ALLOWED_KG_REFS,
        enable_pgmr_metrics=True,
    )

    metric = validation["pgmr_unmapped_placeholders"]

    assert metric["comparable"] is True
    assert metric["value"] == 1.0
    assert metric["has_unmapped_placeholders"] is True
    assert metric["unmapped_placeholder_count"] == 2
    assert metric["unmapped_placeholders"] == [
        "<UNKNOWN_CLASS>",
        "{{NLP_TASK_PROPERTY}}",
    ]


def test_metric_runner_marks_pgmr_unmapped_placeholders_not_comparable_without_prediction_query() -> None:
    validation = build_validation_metrics(
        has_extracted_query=False,
        prediction_query_form=None,
        gold_query_form="select",
        prediction_execution=None,
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
        prediction_query=None,
        gold_query="""
        SELECT ?paper WHERE {
          ?paper orkgp:P31 ?contribution .
        }
        """,
        allowed_kg_refs=ALLOWED_KG_REFS,
        enable_pgmr_metrics=True,
    )

    assert validation["pgmr_unmapped_placeholders"]["comparable"] is False
    assert (
        validation["pgmr_unmapped_placeholders"]["reason"]
        == "prediction_query_missing"
    )

def test_metric_runner_marks_pgmr_metric_not_applicable_for_non_pgmr_mode() -> None:
    validation = build_validation_metrics(
        has_extracted_query=True,
        prediction_query_form="select",
        gold_query_form="select",
        prediction_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        gold_execution=ok_select(
            [
                {"paper": uri("http://orkg.org/orkg/resource/R1")},
            ]
        ),
        endpoint_url=ENDPOINT_URL,
        prediction_query="""
        SELECT ?paper WHERE {
          ?contribution {{NLP_TASK_PROPERTY}} ?task .
        }
        """,
        gold_query="""
        SELECT ?paper WHERE {
          ?paper orkgp:P31 ?contribution .
        }
        """,
        allowed_kg_refs=ALLOWED_KG_REFS,
        enable_pgmr_metrics=False,
    )

    metric = validation["pgmr_unmapped_placeholders"]

    assert metric["comparable"] is False
    assert metric["value"] is None
    assert metric["has_unmapped_placeholders"] is None
    assert metric["unmapped_placeholder_count"] is None
    assert metric["unmapped_placeholders"] == []
    assert metric["reason"] == "not_pgmr_mode"