from __future__ import annotations

import json
from pathlib import Path

from src.ace.curator import apply_delta_report_to_playbook
from src.ace.playbook import load_playbook


def test_curator_applies_deltas_to_empty_playbook(tmp_path: Path) -> None:
    playbook_path = tmp_path / "playbook.json"
    delta_path = tmp_path / "ace_deltas.json"

    delta_path.write_text(
        json.dumps(
            {
                "schema_version": "ace_delta_v1",
                "deltas": [
                    {
                        "operation": "add",
                        "bullet": {
                            "family": "nlp4re",
                            "mode": "pgmr_lite",
                            "category": "pgmr_unmapped_placeholders",
                            "title": "Use only known PGMR placeholders",
                            "content": "Use only placeholders defined in the PGMR memory.",
                            "priority": 90,
                        },
                        "reason": "Validation feedback.",
                        "evidence": {"support_count": 2},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    _, summary = apply_delta_report_to_playbook(
        playbook_path=playbook_path,
        delta_path=delta_path,
        family="nlp4re",
        mode="pgmr_lite",
    )

    loaded = load_playbook(playbook_path)

    assert summary.applied_delta_count == 1
    assert len(loaded.bullets) == 1
    assert loaded.bullets[0].title == "Use only known PGMR placeholders"


def test_curator_filters_by_family_and_mode(tmp_path: Path) -> None:
    playbook_path = tmp_path / "playbook.json"
    delta_path = tmp_path / "ace_deltas.json"

    delta_path.write_text(
        json.dumps(
            {
                "schema_version": "ace_delta_v1",
                "deltas": [
                    {
                        "operation": "add",
                        "bullet": {
                            "family": "empirical_research_practice",
                            "mode": "pgmr_lite",
                            "category": "venue_filter",
                            "title": "Use venue filter",
                            "content": "Add venue label filter.",
                            "priority": 90,
                        },
                    },
                    {
                        "operation": "add",
                        "bullet": {
                            "family": "nlp4re",
                            "mode": "pgmr_lite",
                            "category": "contribution_pattern",
                            "title": "Use contribution pattern",
                            "content": "Connect paper to contribution first.",
                            "priority": 80,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    _, summary = apply_delta_report_to_playbook(
        playbook_path=playbook_path,
        delta_path=delta_path,
        family="nlp4re",
        mode="pgmr_lite",
    )

    loaded = load_playbook(playbook_path)

    assert summary.applied_delta_count == 1
    assert summary.skipped_reasons["family_mismatch"] == 1
    assert len(loaded.bullets) == 1
    assert loaded.bullets[0].family == "nlp4re"


def test_curator_dry_run_does_not_write_playbook(tmp_path: Path) -> None:
    playbook_path = tmp_path / "playbook.json"
    delta_path = tmp_path / "ace_deltas.json"

    delta_path.write_text(
        json.dumps(
            {
                "schema_version": "ace_delta_v1",
                "deltas": [
                    {
                        "operation": "add",
                        "bullet": {
                            "family": "nlp4re",
                            "mode": "pgmr_lite",
                            "category": "output_format",
                            "title": "Return only query",
                            "content": "Return only the query.",
                            "priority": 100,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    _, summary = apply_delta_report_to_playbook(
        playbook_path=playbook_path,
        delta_path=delta_path,
        family="nlp4re",
        mode="pgmr_lite",
        dry_run=True,
    )

    assert summary.applied_delta_count == 1
    assert not playbook_path.exists()


def test_curator_respects_allowed_categories(tmp_path: Path) -> None:
    playbook_path = tmp_path / "playbook.json"
    delta_path = tmp_path / "ace_deltas.json"

    delta_path.write_text(
        json.dumps(
            {
                "schema_version": "ace_delta_v1",
                "deltas": [
                    {
                        "operation": "add",
                        "bullet": {
                            "family": "nlp4re",
                            "mode": "pgmr_lite",
                            "category": "answer_mismatch",
                            "title": "Preserve constraints",
                            "content": "Keep all question constraints.",
                            "priority": 70,
                        },
                    },
                    {
                        "operation": "add",
                        "bullet": {
                            "family": "nlp4re",
                            "mode": "pgmr_lite",
                            "category": "missing_contribution_pattern",
                            "title": "Use contribution pattern",
                            "content": "Connect paper to contribution.",
                            "priority": 90,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    _, summary = apply_delta_report_to_playbook(
        playbook_path=playbook_path,
        delta_path=delta_path,
        family="nlp4re",
        mode="pgmr_lite",
        allowed_categories={"missing_contribution_pattern"},
    )

    loaded = load_playbook(playbook_path)

    assert summary.applied_delta_count == 1
    assert summary.skipped_reasons["category_not_allowed"] == 1
    assert loaded.bullets[0].category == "missing_contribution_pattern"
