from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ace.playbook import (
    AceDelta,
    AcePlaybook,
    load_or_empty_playbook,
    normalize_text,
)


@dataclass
class CurationSummary:
    source_delta_path: str
    playbook_path: str
    output_path: str
    before_bullet_count: int
    after_bullet_count: int
    candidate_delta_count: int
    applied_delta_count: int = 0
    skipped_delta_count: int = 0
    skipped_reasons: dict[str, int] = field(default_factory=dict)
    applied_delta_ids: list[str] = field(default_factory=list)

    def add_skip(self, reason: str) -> None:
        self.skipped_delta_count += 1
        self.skipped_reasons[reason] = self.skipped_reasons.get(reason, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_delta_path": self.source_delta_path,
            "playbook_path": self.playbook_path,
            "output_path": self.output_path,
            "before_bullet_count": self.before_bullet_count,
            "after_bullet_count": self.after_bullet_count,
            "candidate_delta_count": self.candidate_delta_count,
            "applied_delta_count": self.applied_delta_count,
            "skipped_delta_count": self.skipped_delta_count,
            "skipped_reasons": self.skipped_reasons,
            "applied_delta_ids": self.applied_delta_ids,
        }


def load_delta_report(path: str | Path) -> dict[str, Any]:
    delta_path = Path(path)
    payload = json.loads(delta_path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("ACE delta report must be a JSON object.")

    if not isinstance(payload.get("deltas", []), list):
        raise ValueError("ACE delta report must contain a 'deltas' list.")

    return payload


def infer_family_and_mode_from_delta_report(
    delta_report: dict[str, Any],
) -> tuple[str, str]:
    for delta_payload in delta_report.get("deltas", []):
        bullet = delta_payload.get("bullet", {})
        family = str(bullet.get("family") or "").strip()
        mode = str(bullet.get("mode") or "").strip()
        if family and mode:
            return family, mode

    return "global", "any"


def _is_family_match(delta: AceDelta, family: str | None) -> bool:
    if not family:
        return True

    bullet_family = normalize_text(delta.bullet.family)
    target_family = normalize_text(family)

    return bullet_family in {target_family, "global"}


def _is_mode_match(delta: AceDelta, mode: str | None) -> bool:
    if not mode:
        return True

    bullet_mode = normalize_text(delta.bullet.mode)
    target_mode = normalize_text(mode)

    return bullet_mode in {target_mode, "any"}


def _validate_delta(delta: AceDelta) -> str | None:
    bullet = delta.bullet

    if not bullet.enabled:
        return "disabled_bullet"

    if not bullet.title.strip():
        return "missing_title"

    if not bullet.content.strip():
        return "missing_content"

    if not bullet.family.strip():
        return "missing_family"

    if not bullet.mode.strip():
        return "missing_mode"

    if delta.operation not in {"add", "update", "disable"}:
        return "unsupported_operation"

    return None


def curate_delta_report(
    *,
    playbook: AcePlaybook,
    delta_report: dict[str, Any],
    source_delta_path: str,
    playbook_path: str,
    output_path: str,
    family: str | None = None,
    mode: str | None = None,
    min_priority: int = 0,
    max_deltas: int | None = None,
    allowed_categories: set[str] | None = None,
) -> tuple[AcePlaybook, CurationSummary]:
    delta_payloads = delta_report.get("deltas", [])

    summary = CurationSummary(
        source_delta_path=source_delta_path,
        playbook_path=playbook_path,
        output_path=output_path,
        before_bullet_count=len(playbook.bullets),
        after_bullet_count=len(playbook.bullets),
        candidate_delta_count=len(delta_payloads),
    )

    parsed_deltas: list[AceDelta] = []
    for delta_payload in delta_payloads:
        try:
            parsed_deltas.append(AceDelta.from_dict(delta_payload))
        except Exception:
            summary.add_skip("invalid_delta_payload")

    parsed_deltas.sort(
        key=lambda delta: (
            -int(delta.bullet.priority),
            delta.bullet.category,
            delta.bullet.id,
        )
    )

    if max_deltas is not None:
        parsed_deltas = parsed_deltas[: max(0, max_deltas)]

    for delta in parsed_deltas:
        validation_error = _validate_delta(delta)
        if validation_error:
            summary.add_skip(validation_error)
            continue

        if not _is_family_match(delta, family):
            summary.add_skip("family_mismatch")
            continue

        if not _is_mode_match(delta, mode):
            summary.add_skip("mode_mismatch")
            continue

        if delta.bullet.priority < min_priority:
            summary.add_skip("priority_too_low")
            continue

        if allowed_categories and delta.bullet.category not in allowed_categories:
            summary.add_skip("category_not_allowed")
            continue

        playbook.apply_delta(delta)
        summary.applied_delta_count += 1
        summary.applied_delta_ids.append(delta.bullet.id)

    summary.after_bullet_count = len(playbook.bullets)
    return playbook, summary


def apply_delta_report_to_playbook(
    *,
    playbook_path: str | Path,
    delta_path: str | Path,
    output_path: str | Path | None = None,
    family: str | None = None,
    mode: str | None = None,
    min_priority: int = 0,
    max_deltas: int | None = None,
    allowed_categories: set[str] | None = None,
    dry_run: bool = False,
) -> tuple[AcePlaybook, CurationSummary]:
    delta_report = load_delta_report(delta_path)

    inferred_family, inferred_mode = infer_family_and_mode_from_delta_report(delta_report)
    resolved_family = family or inferred_family
    resolved_mode = mode or inferred_mode

    resolved_output_path = Path(output_path) if output_path else Path(playbook_path)

    playbook = load_or_empty_playbook(
        playbook_path,
        family=resolved_family,
        mode=resolved_mode,
    )

    curated_playbook, summary = curate_delta_report(
        playbook=playbook,
        delta_report=delta_report,
        source_delta_path=str(delta_path),
        playbook_path=str(playbook_path),
        output_path=str(resolved_output_path),
        family=resolved_family,
        mode=resolved_mode,
        min_priority=min_priority,
        max_deltas=max_deltas,
        allowed_categories=allowed_categories,
    )

    if not dry_run:
        curated_playbook.save(resolved_output_path)

    return curated_playbook, summary
