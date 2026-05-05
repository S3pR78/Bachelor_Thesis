from __future__ import annotations

import json
from pathlib import Path

from src.ace.online.trace import OnlineAceTraceWriter, build_empty_summary


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_trace_writer_writes_skeleton_trace(tmp_path: Path) -> None:
    writer = OnlineAceTraceWriter(tmp_path)
    writer.add_item_trace(
        {
            "item_id": "1",
            "family": "nlp4re",
            "iterations": [
                {
                    "iteration": 0,
                    "reflection_used": False,
                    "new_rule_added": False,
                }
            ],
        }
    )

    trace_path = writer.write_trace(metadata={"model": "demo"})
    trace = _read_json(trace_path)

    assert trace_path.name == "online_ace_trace.json"
    assert trace["schema_version"] == "online_ace_trace_v1"
    assert trace["metadata"]["model"] == "demo"
    assert trace["items"][0]["item_id"] == "1"
    assert trace["items"][0]["iterations"][0]["iteration"] == 0


def test_trace_writer_writes_summary_with_cost_summary(tmp_path: Path) -> None:
    writer = OnlineAceTraceWriter(tmp_path)
    summary = build_empty_summary(
        metadata={"model": "demo", "max_iterations": 3},
        selected_item_ids=["1", "2"],
        cost_summary={
            "reflection_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        },
    )

    summary_path = writer.write_summary(summary)
    payload = _read_json(summary_path)

    assert summary_path.name == "online_ace_summary.json"
    assert payload["schema_version"] == "online_ace_summary_v1"
    assert payload["selected_item_ids"] == ["1", "2"]
    assert payload["num_items"] == 2
    assert payload["max_iterations"] == 3
    assert payload["cost_summary"]["reflection_calls"] == 0


def test_trace_writer_writes_final_playbook(tmp_path: Path) -> None:
    writer = OnlineAceTraceWriter(tmp_path)
    playbook = {
        "schema_version": "ace_playbook_v1",
        "family": "nlp4re",
        "mode": "pgmr_lite",
        "bullets": [],
        "deleted_rules": [],
    }

    playbook_path = writer.write_final_playbook(playbook)
    payload = _read_json(playbook_path)

    assert playbook_path.name == "online_ace_playbook_final.json"
    assert payload["family"] == "nlp4re"
    assert payload["deleted_rules"] == []


def test_trace_writer_writes_cost_summary(tmp_path: Path) -> None:
    writer = OnlineAceTraceWriter(tmp_path)

    cost_path = writer.write_cost_summary(
        {
            "reflection_calls": 2,
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "total_tokens": 110,
            "estimated_cost_usd": None,
        }
    )
    payload = _read_json(cost_path)

    assert cost_path.name == "online_ace_cost_summary.json"
    assert payload["schema_version"] == "online_ace_cost_summary_v1"
    assert payload["reflection_calls"] == 2
    assert payload["estimated_cost_usd"] is None


def test_trace_writer_write_all_returns_output_paths(tmp_path: Path) -> None:
    writer = OnlineAceTraceWriter(tmp_path)

    paths = writer.write_all(
        metadata={"model": "demo"},
        summary={
            "run_metadata": {"model": "demo"},
            "selected_item_ids": [],
            "cost_summary": {},
        },
        playbook_payload={
            "schema_version": "ace_playbook_v1",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "bullets": [],
        },
        cost_summary={"reflection_calls": 0},
    )

    assert set(paths) == {"trace", "summary", "final_playbook", "cost_summary"}
    assert Path(paths["trace"]).exists()
    assert Path(paths["summary"]).exists()
    assert Path(paths["final_playbook"]).exists()
    assert Path(paths["cost_summary"]).exists()

