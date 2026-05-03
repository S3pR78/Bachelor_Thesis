from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.ace.curator import apply_delta_report_to_playbook
from src.ace.reflector import reflect_trace_report, save_delta_report
from src.ace.traces import build_trace_report, save_trace_report


def ensure_no_test_adaptation(
    *,
    dataset_path: str | Path,
    allow_test_adaptation: bool = False,
) -> None:
    """Prevent accidental ACE adaptation on test data."""
    normalized = str(dataset_path).lower().replace("\\", "/")

    if allow_test_adaptation:
        return

    if "/test" in normalized or "test.json" in normalized or "_test_" in normalized:
        raise ValueError(
            "Refusing to run ACE adaptation on a test dataset. "
            "Use train/validation data for ACE playbook construction. "
            "Pass allow_test_adaptation=True only for debugging, never for thesis results."
        )


def find_latest_benchmark_raw(
    *,
    outputs_root: str | Path = "code/outputs/evaluation_runs",
    started_after_epoch: float | None = None,
) -> Path:
    """Find the newest benchmark_raw.json created after evaluation started."""
    root = Path(outputs_root)
    candidates = list(root.rglob("benchmark_raw.json"))

    if started_after_epoch is not None:
        candidates = [
            path for path in candidates
            if path.stat().st_mtime >= started_after_epoch
        ]

    if not candidates:
        raise FileNotFoundError(
            f"No benchmark_raw.json found under {root} after evaluation."
        )

    return max(candidates, key=lambda path: path.stat().st_mtime)


def run_trace_reflect_curate(
    *,
    raw_path: str | Path,
    playbook_path: str | Path,
    mode: str,
    family: str | None = None,
    split: str | None = None,
    min_support: int = 1,
    max_evidence_items: int = 5,
    min_priority: int = 0,
    max_deltas: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the ACE feedback part for one benchmark_raw.json.

    This function does not call a model. It only:
    1. builds traces,
    2. reflects traces into deltas,
    3. curates deltas into the playbook.
    """
    raw_path = Path(raw_path)
    run_dir = raw_path.parent

    trace_path = run_dir / "ace_error_traces.json"
    delta_path = run_dir / "ace_deltas.json"

    trace_report = build_trace_report(
        raw_path=raw_path,
        mode=mode,
        family=family,
        split=split,
        include_success=False,
    )
    save_trace_report(trace_report, trace_path)

    delta_report = reflect_trace_report(
        trace_report=trace_report,
        trace_path=str(trace_path),
        min_support=min_support,
        max_evidence_items=max_evidence_items,
    )
    save_delta_report(delta_report, delta_path)

    _, curation_summary = apply_delta_report_to_playbook(
        playbook_path=playbook_path,
        delta_path=delta_path,
        output_path=playbook_path,
        family=family,
        mode=mode,
        min_priority=min_priority,
        max_deltas=max_deltas,
        dry_run=dry_run,
    )

    summary = {
        "raw_path": str(raw_path),
        "trace_path": str(trace_path),
        "delta_path": str(delta_path),
        "playbook_path": str(playbook_path),
        "mode": mode,
        "family": family,
        "split": split,
        "trace_count": trace_report["trace_count"],
        "error_trace_count": trace_report["error_trace_count"],
        "category_counts": trace_report["category_counts"],
        "delta_count": delta_report["delta_count"],
        "curation": curation_summary.to_dict(),
        "created_at_epoch": time.time(),
    }

    summary_path = run_dir / "ace_iteration_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return summary
