from __future__ import annotations

from pathlib import Path

from src.ace.playbook import AceDelta, AcePlaybook, load_playbook
from src.ace.rendering import render_ace_context


def test_playbook_filters_by_family_mode_and_priority(tmp_path: Path) -> None:
    playbook = AcePlaybook.from_dict(
        {
            "schema_version": "ace_playbook_v1",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "bullets": [
                {
                    "family": "nlp4re",
                    "mode": "pgmr_lite",
                    "category": "contribution_pattern",
                    "title": "Use contribution pattern",
                    "content": "Connect paper to contribution before template fields.",
                    "priority": 80,
                },
                {
                    "family": "empirical_research_practice",
                    "mode": "pgmr_lite",
                    "category": "venue_filter",
                    "title": "Use venue filter",
                    "content": "Use label filter for venue questions.",
                    "priority": 90,
                },
                {
                    "family": "global",
                    "mode": "any",
                    "category": "output_format",
                    "title": "Return only query",
                    "content": "Do not add explanations.",
                    "priority": 100,
                },
            ],
        }
    )

    selected = playbook.filter_bullets(
        family="nlp4re",
        mode="pgmr_lite",
        max_bullets=10,
    )

    assert [bullet.title for bullet in selected] == [
        "Return only query",
        "Use contribution pattern",
    ]


def test_playbook_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "playbook.json"
    playbook = AcePlaybook.from_dict(
        {
            "schema_version": "ace_playbook_v1",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "bullets": [
                {
                    "family": "nlp4re",
                    "mode": "pgmr_lite",
                    "category": "output_format",
                    "title": "Return only PGMR",
                    "content": "Return only the PGMR-lite query.",
                }
            ],
        }
    )

    playbook.save(path)
    loaded = load_playbook(path)

    assert loaded.family == "nlp4re"
    assert loaded.mode == "pgmr_lite"
    assert loaded.bullets[0].title == "Return only PGMR"


def test_apply_delta_adds_and_deduplicates_bullets() -> None:
    playbook = AcePlaybook.empty(family="nlp4re", mode="pgmr_lite")

    delta_payload = {
        "operation": "add",
        "bullet": {
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "missing_contribution_pattern",
            "title": "Use contribution pattern",
            "content": "Connect paper to contribution before NLP4RE fields.",
            "helpful_count": 1,
        },
        "reason": "Observed validation errors.",
    }

    playbook.apply_delta(AceDelta.from_dict(delta_payload))
    playbook.apply_delta(AceDelta.from_dict(delta_payload))

    assert len(playbook.bullets) == 1
    assert playbook.bullets[0].helpful_count == 2


def test_render_ace_context_outputs_compact_rules(tmp_path: Path) -> None:
    path = tmp_path / "playbook.json"
    playbook = AcePlaybook.from_dict(
        {
            "schema_version": "ace_playbook_v1",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "bullets": [
                {
                    "family": "nlp4re",
                    "mode": "pgmr_lite",
                    "category": "contribution_pattern",
                    "title": "Use contribution pattern",
                    "content": "Connect paper to contribution first.",
                    "positive_pattern": "?paper pgmr:has_contribution ?contribution .",
                    "avoid": "Do not attach template fields directly to ?paper.",
                    "priority": 80,
                }
            ],
        }
    )
    playbook.save(path)

    rendered = render_ace_context(
        playbook_path=str(path),
        family="nlp4re",
        mode="pgmr_lite",
        max_bullets=3,
    )

    assert "ACE playbook rules" in rendered
    assert "Use contribution pattern" in rendered
    assert "?paper pgmr:has_contribution ?contribution ." in rendered
