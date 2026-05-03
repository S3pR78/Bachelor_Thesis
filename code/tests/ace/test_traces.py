from __future__ import annotations

import json
from pathlib import Path

from src.ace.traces import build_trace_report


def test_build_trace_report_groups_failed_items(tmp_path: Path) -> None:
    raw_path = tmp_path / "benchmark_raw.json"
    raw_path.write_text(
        json.dumps(
            [
                {
                    "id": "1",
                    "family": "nlp4re",
                    "split": "validation",
                    "question": "Which metrics are used?",
                    "raw_model_output": "I cannot answer.",
                    "metrics": {
                        "query_extracted": {"value": False},
                        "prediction_execution_success": {"value": False},
                        "answer_f1": {"value": 0.0},
                    },
                },
                {
                    "id": "2",
                    "family": "nlp4re",
                    "split": "validation",
                    "question": "Which datasets are used?",
                    "raw_model_output": "SELECT ?dataset WHERE { ... }",
                    "metrics": {
                        "query_extracted": {"value": True},
                        "prediction_execution_success": {"value": True},
                        "answer_f1": {"value": 1.0},
                    },
                },
            ]
        ),
        encoding="utf-8",
    )

    report = build_trace_report(
        raw_path=raw_path,
        mode="pgmr_lite",
        family="nlp4re",
        split="validation",
    )

    assert report["total_records_in_raw"] == 2
    assert report["trace_count"] == 1
    assert report["error_trace_count"] == 1
    assert report["category_counts"]["no_extracted_query"] == 1
    assert report["category_counts"]["prediction_execution_error"] == 1
    assert report["category_counts"]["answer_mismatch"] == 1


def test_build_trace_report_detects_pgmr_restore_and_unmapped_errors(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "benchmark_raw.json"
    raw_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "id": "810",
                        "family": "nlp4re",
                        "split": "validation",
                        "question": "What are the granularities?",
                        "raw_model_output": "SELECT ?x WHERE { ?x pgmr:unknown_token ?y . }",
                        "pgmr_restore_status": "failed",
                        "missing_token_counts": {
                            "pgmr:unknown_token": 1,
                        },
                        "metrics": {
                            "query_extracted": True,
                            "prediction_execution_success": False,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_trace_report(
        raw_path=raw_path,
        mode="pgmr_lite",
        family="nlp4re",
        split="validation",
    )

    assert report["trace_count"] == 1
    assert report["category_counts"]["pgmr_restore_error"] == 1
    assert report["category_counts"]["pgmr_unmapped_placeholders"] == 1
