"""JSON writers for online ACE run outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


TRACE_FILENAME = "online_ace_trace.json"
SUMMARY_FILENAME = "online_ace_summary.json"
FINAL_PLAYBOOK_FILENAME = "online_ace_playbook_final.json"
COST_SUMMARY_FILENAME = "online_ace_cost_summary.json"


def _write_json(path: str | Path, payload: Any) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


@dataclass
class OnlineAceTraceWriter:
    """Collect and write online ACE trace, summary, playbook, and costs."""

    output_dir: Path | str
    items: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)

    @property
    def trace_path(self) -> Path:
        return self.output_dir / TRACE_FILENAME

    @property
    def summary_path(self) -> Path:
        return self.output_dir / SUMMARY_FILENAME

    @property
    def final_playbook_path(self) -> Path:
        return self.output_dir / FINAL_PLAYBOOK_FILENAME

    @property
    def cost_summary_path(self) -> Path:
        return self.output_dir / COST_SUMMARY_FILENAME

    def add_item_trace(self, item_trace: dict[str, Any]) -> None:
        """Append one item trace object to the in-memory trace."""
        self.items.append(item_trace)

    def build_trace_payload(self, *, metadata: dict[str, Any] | None = None) -> dict:
        """Build the skeleton trace payload for this run."""
        return {
            "schema_version": "online_ace_trace_v1",
            "metadata": metadata or {},
            "items": self.items,
        }

    def write_trace(self, *, metadata: dict[str, Any] | None = None) -> Path:
        """Write online_ace_trace.json."""
        return _write_json(
            self.trace_path,
            self.build_trace_payload(metadata=metadata),
        )

    def write_summary(self, summary: dict[str, Any]) -> Path:
        """Write online_ace_summary.json."""
        payload = {
            "schema_version": "online_ace_summary_v1",
            **summary,
        }
        return _write_json(self.summary_path, payload)

    def write_final_playbook(self, playbook_payload: dict[str, Any]) -> Path:
        """Write online_ace_playbook_final.json."""
        return _write_json(self.final_playbook_path, playbook_payload)

    def write_cost_summary(self, cost_summary: dict[str, Any]) -> Path:
        """Write online_ace_cost_summary.json."""
        payload = {
            "schema_version": "online_ace_cost_summary_v1",
            **cost_summary,
        }
        return _write_json(self.cost_summary_path, payload)

    def write_all(
        self,
        *,
        metadata: dict[str, Any] | None,
        summary: dict[str, Any],
        playbook_payload: dict[str, Any],
        cost_summary: dict[str, Any],
    ) -> dict[str, str]:
        """Write all online ACE output files and return their paths."""
        paths = {
            "trace": self.write_trace(metadata=metadata),
            "summary": self.write_summary(summary),
            "final_playbook": self.write_final_playbook(playbook_payload),
            "cost_summary": self.write_cost_summary(cost_summary),
        }
        return {key: str(path) for key, path in paths.items()}


def build_empty_summary(
    *,
    metadata: dict[str, Any],
    selected_item_ids: list[str],
    cost_summary: dict[str, Any],
) -> dict[str, Any]:
    """Build a run summary skeleton before the real online loop is available."""
    return {
        "run_metadata": metadata,
        "selected_item_ids": selected_item_ids,
        "num_items": len(selected_item_ids),
        "total_attempts": 0,
        "max_iterations": metadata.get("max_iterations"),
        "solved_initially": 0,
        "solved_after_reflection": 0,
        "still_unsolved": 0,
        "rules_added": 0,
        "rules_enabled": 0,
        "rules_disabled": 0,
        "rules_deleted": 0,
        "top_helpful_rules": [],
        "top_harmful_rules": [],
        "initial_metrics_mean": {},
        "final_metrics_mean": {},
        "improvements": {},
        "cost_summary": cost_summary,
    }

