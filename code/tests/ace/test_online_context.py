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

