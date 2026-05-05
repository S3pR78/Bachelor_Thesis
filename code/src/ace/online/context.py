"""Online ACE playbook context management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ace.playbook import (
    AceBullet,
    AcePlaybook,
    load_or_empty_playbook,
    utc_now_iso,
)


HARMFUL_DISABLED_REASON = "harmful_in_online_ace"


@dataclass
class OnlineAceContext:
    """Mutable in-memory playbook used during an online ACE run."""

    playbook: AcePlaybook
    initial_playbook_path: Path
    initial_playbook_exists: bool
    ace_max_bullets: int = 3
    disable_harmful_rules: bool = False
    delete_harmful_rules: bool = False
    min_harmful_count: int = 2
    deleted_rules: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(
        cls,
        *,
        initial_playbook_path: str | Path,
        family: str,
        mode: str,
        ace_max_bullets: int = 3,
        disable_harmful_rules: bool = False,
        delete_harmful_rules: bool = False,
        min_harmful_count: int = 2,
    ) -> "OnlineAceContext":
        """Load an explicit playbook path or start from an empty in-memory one."""
        path = Path(initial_playbook_path)
        playbook = load_or_empty_playbook(path, family=family, mode=mode)
        playbook.metadata = {
            **playbook.metadata,
            "workflow": "online",
            "initial_playbook_path": str(path),
            "initial_playbook_exists": path.exists(),
        }
        return cls(
            playbook=playbook,
            initial_playbook_path=path,
            initial_playbook_exists=path.exists(),
            ace_max_bullets=ace_max_bullets,
            disable_harmful_rules=disable_harmful_rules,
            delete_harmful_rules=delete_harmful_rules,
            min_harmful_count=min_harmful_count,
        )

    def select_rules(
        self,
        *,
        family: str | None = None,
        mode: str | None = None,
        max_bullets: int | None = None,
    ) -> list[AceBullet]:
        """Select enabled rules for prompt context."""
        return self.playbook.filter_bullets(
            family=family or self.playbook.family,
            mode=mode or self.playbook.mode,
            max_bullets=self.ace_max_bullets if max_bullets is None else max_bullets,
        )

    def selected_rule_ids(
        self,
        *,
        family: str | None = None,
        mode: str | None = None,
        max_bullets: int | None = None,
    ) -> list[str]:
        """Return selected enabled rule IDs."""
        return [
            rule.id
            for rule in self.select_rules(
                family=family,
                mode=mode,
                max_bullets=max_bullets,
            )
        ]

    def add_rule(self, rule_payload: dict[str, Any]) -> AceBullet:
        """Add or merge one reflector-proposed rule into the active playbook."""
        bullet = AceBullet.from_dict(
            {
                **rule_payload,
                "family": rule_payload.get("family") or self.playbook.family,
                "mode": rule_payload.get("mode") or self.playbook.mode,
                "enabled": rule_payload.get("enabled", True),
                "created_at_utc": rule_payload.get("created_at_utc") or utc_now_iso(),
                "updated_at_utc": rule_payload.get("updated_at_utc") or utc_now_iso(),
            }
        )

        existing = self._find_rule(bullet.id)
        if existing is None:
            self.playbook.bullets.append(bullet)
            added = bullet
        else:
            existing.title = bullet.title
            existing.content = bullet.content
            existing.category = bullet.category
            existing.priority = max(existing.priority, bullet.priority)
            existing.enabled = bullet.enabled
            existing.positive_pattern = (
                bullet.positive_pattern or existing.positive_pattern
            )
            existing.avoid = bullet.avoid or existing.avoid
            existing.updated_at_utc = utc_now_iso()
            added = existing

        self.playbook.updated_at_utc = utc_now_iso()
        self.playbook.deduplicate()
        return self._find_rule(added.id) or added

    def mark_helpful(
        self,
        rule_id: str,
        *,
        item_id: str,
        delta: float,
    ) -> None:
        """Record that a rule improved the next attempt for an item."""
        rule = self._require_rule(rule_id)
        rule.helpful_count += 1
        rule.last_helpful_item_id = str(item_id)
        rule.last_helpful_delta = float(delta)
        rule.updated_at_utc = utc_now_iso()
        self.playbook.updated_at_utc = utc_now_iso()

    def mark_harmful(
        self,
        rule_id: str,
        *,
        item_id: str,
        delta: float,
    ) -> list[str]:
        """Record harm and apply the configured disable/delete policy."""
        rule = self._require_rule(rule_id)
        rule.harmful_count += 1
        rule.last_harmful_item_id = str(item_id)
        rule.last_harmful_delta = float(delta)
        rule.updated_at_utc = utc_now_iso()
        self.playbook.updated_at_utc = utc_now_iso()
        return self.apply_harmful_rule_policy()

    def apply_harmful_rule_policy(self) -> list[str]:
        """Disable or delete rules that reached the harmful threshold."""
        changed_rule_ids: list[str] = []

        for rule in list(self.playbook.bullets):
            if int(rule.harmful_count) < int(self.min_harmful_count):
                continue

            if self.delete_harmful_rules:
                self.playbook.bullets.remove(rule)
                self.deleted_rules.append(rule.to_dict())
                changed_rule_ids.append(rule.id)
                continue

            if self.disable_harmful_rules and rule.enabled:
                rule.enabled = False
                rule.disabled_reason = HARMFUL_DISABLED_REASON
                rule.updated_at_utc = utc_now_iso()
                changed_rule_ids.append(rule.id)

        if changed_rule_ids:
            self.playbook.updated_at_utc = utc_now_iso()

        return changed_rule_ids

    def enabled_rule_count(self) -> int:
        """Return the number of currently enabled rules."""
        return sum(1 for rule in self.playbook.bullets if rule.enabled)

    def deleted_rule_ids(self) -> list[str]:
        """Return deleted rule IDs for trace and summary metadata."""
        return [str(rule.get("id")) for rule in self.deleted_rules]

    def to_playbook_dict(self) -> dict[str, Any]:
        """Return the final in-memory playbook payload."""
        payload = self.playbook.to_dict()
        payload["deleted_rules"] = self.deleted_rules
        return payload

    def _find_rule(self, rule_id: str) -> AceBullet | None:
        for rule in self.playbook.bullets:
            if rule.id == rule_id:
                return rule
        return None

    def _require_rule(self, rule_id: str) -> AceBullet:
        rule = self._find_rule(rule_id)
        if rule is None:
            raise KeyError(f"Unknown ACE rule id: {rule_id}")
        return rule
