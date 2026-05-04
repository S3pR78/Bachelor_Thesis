from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ace.offline_loop import (
    create_family_filtered_dataset,
    ensure_no_test_adaptation,
    find_latest_benchmark_raw,
    run_trace_reflect_curate,
)
from src.ace.playbook import load_playbook


def test_ensure_no_test_adaptation_blocks_test_json() -> None:
    with pytest.raises(ValueError):
        ensure_no_test_adaptation(
            dataset_path="code/data/dataset/pgmr/final/test.json"
        )


def test_ensure_no_test_adaptation_allows_validation_json() -> None:
    ensure_no_test_adaptation(
        dataset_path="code/data/dataset/pgmr/final/validation.json"
    )


def test_find_latest_benchmark_raw(tmp_path: Path) -> None:
    first = tmp_path / "run1" / "benchmark_raw.json"
    second = tmp_path / "run2" / "benchmark_raw.json"

    first.parent.mkdir()
    second.parent.mkdir()

    first.write_text("[]", encoding="utf-8")
    second.write_text("[]", encoding="utf-8")

    latest = find_latest_benchmark_raw(outputs_root=tmp_path)

    assert latest.name == "benchmark_raw.json"
    assert latest.parent.name in {"run1", "run2"}


def test_run_trace_reflect_curate_updates_playbook(tmp_path: Path) -> None:
    raw_path = tmp_path / "run" / "benchmark_raw.json"
    playbook_path = tmp_path / "playbook.json"
    raw_path.parent.mkdir()

    raw_path.write_text(
        json.dumps(
            [
                {
                    "id": "1",
                    "family": "nlp4re",
                    "split": "validation",
                    "question": "Which NLP tasks are used?",
                    "raw_model_output": "SELECT ?task WHERE { ?paper pgmr:nlp_task ?task . }",
                    "extracted_query": "SELECT ?task WHERE { ?paper pgmr:nlp_task ?task . }",
                    "metrics": {
                        "query_extracted": True,
                        "prediction_execution_success": True,
                        "answer_f1": 0.0
                    }
                }
            ]
        ),
        encoding="utf-8",
    )

    summary = run_trace_reflect_curate(
        raw_path=raw_path,
        playbook_path=playbook_path,
        mode="pgmr_lite",
        family="nlp4re",
        split="validation",
    )

    playbook = load_playbook(playbook_path)

    assert summary["trace_count"] == 1
    assert summary["delta_count"] >= 1
    assert any(
        bullet.category == "missing_contribution_pattern"
        for bullet in playbook.bullets
    )
    assert (raw_path.parent / "ace_error_traces.json").exists()
    assert (raw_path.parent / "ace_deltas.json").exists()
    assert (raw_path.parent / "ace_iteration_summary.json").exists()


def test_create_family_filtered_dataset(tmp_path: Path) -> None:
    dataset_path = tmp_path / "ace_playbook.json"
    output_dir = tmp_path / "filtered"

    dataset_path.write_text(
        json.dumps(
            [
                {"id": "1", "family": "nlp4re", "question": "A"},
                {"id": "2", "family": "empirical_research_practice", "question": "B"},
                {"id": "3", "family": "nlp4re", "question": "C"},
            ]
        ),
        encoding="utf-8",
    )

    filtered_path = create_family_filtered_dataset(
        dataset_path=dataset_path,
        family="nlp4re",
        output_dir=output_dir,
    )

    filtered = json.loads(filtered_path.read_text(encoding="utf-8"))

    assert len(filtered) == 2
    assert {item["id"] for item in filtered} == {"1", "3"}
    assert all(item["family"] == "nlp4re" for item in filtered)
