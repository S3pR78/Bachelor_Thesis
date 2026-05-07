from __future__ import annotations

import json
from pathlib import Path

from src.ace.online.context import HARMFUL_DISABLED_REASON, OnlineAceContext


def _rule(rule_id: str, *, priority: int = 50, enabled: bool = True) -> dict:
    return {
        "id": rule_id,
        "family": "nlp4re",
        "mode": "pgmr_lite",
        "category": "routing",
        "title": f"Rule {rule_id}",
        "content": "Use the template contribution path.",
        "priority": priority,
        "enabled": enabled,
    }


def _write_playbook(path: Path, rules: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "ace_playbook_v1",
                "family": "nlp4re",
                "mode": "pgmr_lite",
                "bullets": rules,
            }
        ),
        encoding="utf-8",
    )


def test_context_loads_existing_playbook_and_selects_enabled_rules(
    tmp_path: Path,
) -> None:
    playbook_path = tmp_path / "playbook.json"
    _write_playbook(
        playbook_path,
        [
            _rule("low", priority=10),
            _rule("disabled", priority=100, enabled=False),
            _rule("high", priority=90),
        ],
    )

    context = OnlineAceContext.load(
        initial_playbook_path=playbook_path,
        family="nlp4re",
        mode="pgmr_lite",
        ace_max_bullets=2,
    )

    assert context.initial_playbook_exists is True
    assert context.selected_rule_ids() == ["high", "low"]
    assert context.enabled_rule_count() == 2


def test_context_can_start_empty_when_explicit_initial_path_is_missing(
    tmp_path: Path,
) -> None:
    context = OnlineAceContext.load(
        initial_playbook_path=tmp_path / "missing.json",
        family="nlp4re",
        mode="pgmr_lite",
    )

    assert context.initial_playbook_exists is False
    assert context.playbook.family == "nlp4re"
    assert context.playbook.mode == "pgmr_lite"
    assert context.selected_rule_ids() == []


def test_context_adds_rule_and_tracks_helpful_count(tmp_path: Path) -> None:
    context = OnlineAceContext.load(
        initial_playbook_path=tmp_path / "missing.json",
        family="nlp4re",
        mode="pgmr_lite",
    )

    added = context.add_rule(_rule("new", priority=80))
    context.mark_helpful("new", item_id="item-1", delta=0.12)

    assert added.id == "new"
    assert context.selected_rule_ids() == ["new"]
    assert context.playbook.bullets[0].helpful_count == 1
    assert context.playbook.bullets[0].last_helpful_item_id == "item-1"
    assert context.playbook.bullets[0].last_helpful_delta == 0.12


def test_context_disables_harmful_rule_when_enabled(tmp_path: Path) -> None:
    context = OnlineAceContext.load(
        initial_playbook_path=tmp_path / "missing.json",
        family="nlp4re",
        mode="pgmr_lite",
        disable_harmful_rules=True,
        min_harmful_count=2,
    )
    context.add_rule(_rule("bad"))

    assert context.mark_harmful("bad", item_id="item-1", delta=-0.03) == []
    disabled_ids = context.mark_harmful("bad", item_id="item-2", delta=-0.08)

    rule = context.playbook.bullets[0]
    assert disabled_ids == ["bad"]
    assert rule.enabled is False
    assert rule.disabled_reason == HARMFUL_DISABLED_REASON
    assert rule.harmful_count == 2
    assert rule.last_harmful_item_id == "item-2"


def test_context_deletes_harmful_rule_when_configured(tmp_path: Path) -> None:
    context = OnlineAceContext.load(
        initial_playbook_path=tmp_path / "missing.json",
        family="nlp4re",
        mode="pgmr_lite",
        delete_harmful_rules=True,
        min_harmful_count=1,
    )
    context.add_rule(_rule("bad"))

    deleted_ids = context.mark_harmful("bad", item_id="item-1", delta=-0.2)

    assert deleted_ids == ["bad"]
    assert context.selected_rule_ids() == []
    assert context.deleted_rule_ids() == ["bad"]
    assert context.to_playbook_dict()["deleted_rules"][0]["id"] == "bad"


def test_context_merges_very_similar_enabled_rules_instead_of_adding_duplicate(
    tmp_path: Path,
) -> None:
    context = OnlineAceContext.load(
        initial_playbook_path=tmp_path / "missing.json",
        family="nlp4re",
        mode="pgmr_lite",
    )
    context.add_rule(
        {
            "id": "baseline_path_v1",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "extraction",
            "title": "Use baseline type path",
            "content": "Use ?evaluation pgmr:baseline ?baseline . then ?baseline pgmr:baseline_type ?type .",
            "priority": 80,
            "enabled": True,
            "source_item_id": "item-1",
            "source_iteration": 0,
        }
    )

    merged = context.add_rule(
        {
            "id": "baseline_path_v2",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "extraction",
            "title": "Use baseline-type path",
            "content": "Use ?evaluation pgmr:baseline ?baseline . and ?baseline pgmr:baseline_type ?type .",
            "priority": 85,
            "enabled": True,
            "source_item_id": "item-2",
            "source_iteration": 1,
        }
    )

    assert len(context.playbook.bullets) == 1
    assert merged.id == "baseline_path_v1"
    assert merged.priority == 85
    assert merged.source_item_id == "item-2"
    assert merged.source_iteration == 1


def test_context_merges_by_same_pgmr_placeholder_set(tmp_path: Path) -> None:
    context = OnlineAceContext.load(
        initial_playbook_path=tmp_path / "missing.json",
        family="nlp4re",
        mode="pgmr_lite",
    )
    context.add_rule(
        {
            "id": "rule_a",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "projection",
            "title": "Use NLP data type",
            "content": "Use pgmr:nlp_data_type in projection logic.",
            "priority": 80,
            "enabled": True,
        }
    )
    result = context.add_rule_with_result(
        {
            "id": "rule_b",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "projection",
            "title": "Do not invent type placeholder",
            "content": "Avoid wrong projection and use pgmr:nlp_data_type.",
            "priority": 82,
            "enabled": True,
        }
    )
    assert result["rule_merged"] is True
    assert result["merge_reason"] == "same PGMR placeholder set"
    assert len(context.playbook.bullets) == 1


def test_context_does_not_merge_unrelated_rules(tmp_path: Path) -> None:
    context = OnlineAceContext.load(
        initial_playbook_path=tmp_path / "missing.json",
        family="nlp4re",
        mode="pgmr_lite",
    )
    context.add_rule(_rule("one", priority=80))
    result = context.add_rule_with_result(
        {
            "id": "two",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "aggregation",
            "title": "Use COUNT for frequency questions",
            "content": "Use COUNT(?paper) GROUP BY ?type for how-many questions.",
            "priority": 85,
            "enabled": True,
        }
    )
    assert result["new_rule_added"] is True
    assert result["rule_merged"] is False
    assert len(context.playbook.bullets) == 2


def test_context_merge_updates_evidence_and_pattern(tmp_path: Path) -> None:
    context = OnlineAceContext.load(
        initial_playbook_path=tmp_path / "missing.json",
        family="nlp4re",
        mode="pgmr_lite",
    )
    context.add_rule(
        {
            "id": "base",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "projection",
            "title": "Use time variable",
            "content": "Focus on ?dataProductionTime.",
            "positive_pattern": None,
            "priority": 80,
            "enabled": True,
            "source_item_id": "item-1",
        }
    )
    merged = context.add_rule_with_result(
        {
            "id": "new",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "category": "projection",
            "title": "Use time variable path",
            "content": "Focus on ?dataProductionTime and avoid ?nlpDataset projection.",
            "positive_pattern": "?contribution pgmr:nlp_data_production_time ?dataProductionTime .",
            "priority": 81,
            "enabled": True,
            "source_item_id": "item-2",
        }
    )
    active = merged["rule"]
    assert active.id == "base"
    assert active.positive_pattern == "?contribution pgmr:nlp_data_production_time ?dataProductionTime ."
    assert "item-2" in active.evidence_item_ids
