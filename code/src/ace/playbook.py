from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLAYBOOK_SCHEMA_VERSION = "ace_playbook_v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def stable_bullet_id(
    *,
    family: str,
    mode: str,
    category: str,
    title: str,
    content: str,
) -> str:
    raw = "|".join(
        [
            normalize_text(family),
            normalize_text(mode),
            normalize_text(category),
            normalize_text(title),
            normalize_text(content),
        ]
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    safe_family = normalize_text(family).replace(" ", "_") or "global"
    safe_mode = normalize_text(mode).replace(" ", "_") or "any"
    safe_category = normalize_text(category).replace(" ", "_") or "rule"
    return f"{safe_family}_{safe_mode}_{safe_category}_{digest}"


@dataclass
class AceBullet:
    id: str
    family: str
    mode: str
    category: str
    title: str
    content: str
    bullet_type: str = "hard_rule"
    priority: int = 50
    enabled: bool = True
    positive_pattern: str | None = None
    avoid: str | None = None
    applicability: list[str] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    evidence_item_ids: list[str] = field(default_factory=list)
    helpful_count: int = 0
    harmful_count: int = 0
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AceBullet":
        required = ["family", "mode", "category", "title", "content"]
        missing = [key for key in required if not str(payload.get(key, "")).strip()]
        if missing:
            raise ValueError(f"ACE bullet is missing required fields: {missing}")

        bullet_id = str(payload.get("id") or "").strip()
        if not bullet_id:
            bullet_id = stable_bullet_id(
                family=str(payload["family"]),
                mode=str(payload["mode"]),
                category=str(payload["category"]),
                title=str(payload["title"]),
                content=str(payload["content"]),
            )

        return cls(
            id=bullet_id,
            family=str(payload["family"]).strip(),
            mode=str(payload["mode"]).strip(),
            category=str(payload["category"]).strip(),
            title=str(payload["title"]).strip(),
            content=str(payload["content"]).strip(),
            bullet_type=str(payload.get("bullet_type", "hard_rule")).strip(),
            priority=int(payload.get("priority", 50)),
            enabled=bool(payload.get("enabled", True)),
            positive_pattern=payload.get("positive_pattern"),
            avoid=payload.get("avoid"),
            applicability=list(payload.get("applicability", [])),
            source=dict(payload.get("source", {})),
            evidence_item_ids=list(payload.get("evidence_item_ids", [])),
            helpful_count=int(payload.get("helpful_count", 0)),
            harmful_count=int(payload.get("harmful_count", 0)),
            created_at_utc=str(payload.get("created_at_utc") or utc_now_iso()),
            updated_at_utc=str(payload.get("updated_at_utc") or utc_now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "family": self.family,
            "mode": self.mode,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "bullet_type": self.bullet_type,
            "priority": self.priority,
            "enabled": self.enabled,
            "positive_pattern": self.positive_pattern,
            "avoid": self.avoid,
            "applicability": self.applicability,
            "source": self.source,
            "evidence_item_ids": self.evidence_item_ids,
            "helpful_count": self.helpful_count,
            "harmful_count": self.harmful_count,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
        }


@dataclass
class AceDelta:
    operation: str
    bullet: AceBullet
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AceDelta":
        operation = str(payload.get("operation", "add")).strip().lower()
        if operation not in {"add", "update", "disable"}:
            raise ValueError(f"Unsupported ACE delta operation: {operation}")
        bullet_payload = payload.get("bullet")
        if not isinstance(bullet_payload, dict):
            raise ValueError("ACE delta must contain a bullet object.")
        return cls(
            operation=operation,
            bullet=AceBullet.from_dict(bullet_payload),
            reason=str(payload.get("reason", "")),
            evidence=dict(payload.get("evidence", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "bullet": self.bullet.to_dict(),
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass
class AcePlaybook:
    family: str
    mode: str
    bullets: list[AceBullet] = field(default_factory=list)
    schema_version: str = PLAYBOOK_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls, *, family: str, mode: str) -> "AcePlaybook":
        return cls(family=family, mode=mode)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AcePlaybook":
        schema_version = str(payload.get("schema_version", PLAYBOOK_SCHEMA_VERSION))
        if schema_version != PLAYBOOK_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported ACE playbook schema version: {schema_version}"
            )

        bullets_payload = payload.get("bullets", [])
        if not isinstance(bullets_payload, list):
            raise ValueError("ACE playbook 'bullets' must be a list.")

        return cls(
            schema_version=schema_version,
            family=str(payload.get("family", "")).strip(),
            mode=str(payload.get("mode", "")).strip(),
            bullets=[AceBullet.from_dict(item) for item in bullets_payload],
            created_at_utc=str(payload.get("created_at_utc") or utc_now_iso()),
            updated_at_utc=str(payload.get("updated_at_utc") or utc_now_iso()),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "family": self.family,
            "mode": self.mode,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "metadata": self.metadata,
            "bullets": [bullet.to_dict() for bullet in self.bullets],
        }

    def save(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def filter_bullets(
        self,
        *,
        family: str | None = None,
        mode: str | None = None,
        categories: set[str] | None = None,
        max_bullets: int | None = None,
        include_disabled: bool = False,
    ) -> list[AceBullet]:
        selected: list[AceBullet] = []

        for bullet in self.bullets:
            if not include_disabled and not bullet.enabled:
                continue
            if family and normalize_text(bullet.family) not in {
                normalize_text(family),
                "global",
            }:
                continue
            if mode and normalize_text(bullet.mode) not in {normalize_text(mode), "any"}:
                continue
            if categories and bullet.category not in categories:
                continue
            selected.append(bullet)

        selected.sort(
            key=lambda item: (
                -int(item.priority),
                int(item.harmful_count),
                -int(item.helpful_count),
                item.id,
            )
        )

        if max_bullets is not None:
            selected = selected[: max(0, max_bullets)]

        return selected

    def apply_delta(self, delta: AceDelta) -> None:
        existing_by_id = {bullet.id: index for index, bullet in enumerate(self.bullets)}
        bullet = delta.bullet
        bullet.updated_at_utc = utc_now_iso()

        if delta.operation == "add":
            if bullet.id in existing_by_id:
                self._merge_bullet(existing_by_id[bullet.id], bullet)
            else:
                self.bullets.append(bullet)

        elif delta.operation == "update":
            if bullet.id in existing_by_id:
                self._merge_bullet(existing_by_id[bullet.id], bullet)
            else:
                self.bullets.append(bullet)

        elif delta.operation == "disable":
            if bullet.id in existing_by_id:
                self.bullets[existing_by_id[bullet.id]].enabled = False
                self.bullets[existing_by_id[bullet.id]].updated_at_utc = utc_now_iso()

        self.updated_at_utc = utc_now_iso()
        self.deduplicate()

    def apply_deltas(self, deltas: list[AceDelta]) -> None:
        for delta in deltas:
            self.apply_delta(delta)

    def _merge_bullet(self, index: int, new_bullet: AceBullet) -> None:
        old = self.bullets[index]
        old.title = new_bullet.title or old.title
        old.content = new_bullet.content or old.content
        old.category = new_bullet.category or old.category
        old.bullet_type = new_bullet.bullet_type or old.bullet_type
        old.priority = max(old.priority, new_bullet.priority)
        old.enabled = new_bullet.enabled
        old.positive_pattern = new_bullet.positive_pattern or old.positive_pattern
        old.avoid = new_bullet.avoid or old.avoid
        old.applicability = sorted(set(old.applicability + new_bullet.applicability))
        old.evidence_item_ids = sorted(
            set(old.evidence_item_ids + new_bullet.evidence_item_ids)
        )
        old.helpful_count += new_bullet.helpful_count
        old.harmful_count += new_bullet.harmful_count
        old.source = {**old.source, **new_bullet.source}
        old.updated_at_utc = utc_now_iso()

    def deduplicate(self) -> None:
        seen: dict[str, AceBullet] = {}
        deduped: list[AceBullet] = []

        for bullet in self.bullets:
            key = "|".join(
                [
                    normalize_text(bullet.family),
                    normalize_text(bullet.mode),
                    normalize_text(bullet.category),
                    normalize_text(bullet.title),
                    normalize_text(bullet.content),
                ]
            )
            if key not in seen:
                seen[key] = bullet
                deduped.append(bullet)
                continue

            existing = seen[key]
            existing.helpful_count += bullet.helpful_count
            existing.harmful_count += bullet.harmful_count
            existing.priority = max(existing.priority, bullet.priority)
            existing.evidence_item_ids = sorted(
                set(existing.evidence_item_ids + bullet.evidence_item_ids)
            )

        self.bullets = deduped


def load_playbook(path: str | Path) -> AcePlaybook:
    playbook_path = Path(path)
    if not playbook_path.exists():
        raise FileNotFoundError(f"ACE playbook not found: {playbook_path}")
    payload = json.loads(playbook_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ACE playbook JSON must be an object.")
    return AcePlaybook.from_dict(payload)


def load_or_empty_playbook(
    path: str | Path,
    *,
    family: str,
    mode: str,
) -> AcePlaybook:
    playbook_path = Path(path)
    if not playbook_path.exists():
        return AcePlaybook.empty(family=family, mode=mode)
    return load_playbook(playbook_path)
