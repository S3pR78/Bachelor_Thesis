"""Online ACE playbook context management."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Any

from src.ace.playbook import (
    AceBullet,
    AcePlaybook,
    load_or_empty_playbook,
    normalize_text,
    utc_now_iso,
)


HARMFUL_DISABLED_REASON = "harmful_in_online_ace"
SIMILAR_RULE_THRESHOLD = 0.82


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
        """Backwards-compatible wrapper returning the active rule."""
        return self.add_rule_with_result(rule_payload)["rule"]

    def add_rule_with_result(self, rule_payload: dict[str, Any]) -> dict[str, Any]:
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

        merge_reason: str | None = None
        existing = self._find_rule(bullet.id)
        if existing is None:
            existing, merge_reason = self._find_similar_enabled_rule_with_reason(bullet)
        if existing is None:
            self.playbook.bullets.append(bullet)
            added = bullet
            new_rule_added = True
            rule_merged = False
        else:
            existing.title = bullet.title
            existing.content = bullet.content
            existing.category = bullet.category
            existing.priority = max(existing.priority, bullet.priority)
            existing.enabled = bullet.enabled
            if self._should_prefer_new_pattern(
                existing.positive_pattern, bullet.positive_pattern
            ):
                existing.positive_pattern = bullet.positive_pattern
            if not existing.avoid and bullet.avoid:
                existing.avoid = bullet.avoid
            source_item_id = bullet.source_item_id
            if source_item_id and source_item_id not in existing.evidence_item_ids:
                existing.evidence_item_ids.append(source_item_id)
            existing.source_item_id = bullet.source_item_id or existing.source_item_id
            existing.source_iteration = (
                bullet.source_iteration
                if bullet.source_iteration is not None
                else existing.source_iteration
            )
            existing.source = {**existing.source, **bullet.source}
            existing.updated_at_utc = utc_now_iso()
            added = existing
            new_rule_added = False
            rule_merged = True

        self.playbook.updated_at_utc = utc_now_iso()
        self.playbook.deduplicate()
        active = self._find_rule(added.id) or added
        return {
            "rule": active,
            "new_rule_added": new_rule_added,
            "rule_merged": rule_merged,
            "merged_into_rule_id": active.id if rule_merged else None,
            "merge_reason": merge_reason,
            "proposed_rule": bullet.to_dict(),
            "active_rule": active.to_dict(),
        }

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

    def _find_similar_enabled_rule_with_reason(
        self,
        candidate: AceBullet,
    ) -> tuple[AceBullet | None, str | None]:
        candidate_text = self._normalized_rule_text(candidate)
        candidate_placeholders = self._extract_pgmr_tokens(candidate)
        candidate_main_var = self._extract_main_var(candidate)
        for rule in self.playbook.bullets:
            if not rule.enabled:
                continue
            if normalize_text(rule.family) != normalize_text(candidate.family):
                continue
            if normalize_text(rule.mode) != normalize_text(candidate.mode):
                continue
            if normalize_text(rule.category) != normalize_text(candidate.category):
                continue
            existing_text = self._normalized_rule_text(rule)
            similarity = SequenceMatcher(None, candidate_text, existing_text).ratio()
            if similarity >= SIMILAR_RULE_THRESHOLD:
                return rule, "text similarity"

            existing_placeholders = self._extract_pgmr_tokens(rule)
            if candidate_placeholders and candidate_placeholders == existing_placeholders:
                return rule, "same PGMR placeholder set"

            existing_main_var = self._extract_main_var(rule)
            if candidate_main_var and candidate_main_var == existing_main_var:
                return rule, "same main projection variable"
        return None, None

    @staticmethod
    def _normalized_rule_text(rule: AceBullet) -> str:
        return " | ".join(
            normalize_text(text)
            for text in [rule.title, rule.content, rule.positive_pattern, rule.avoid]
        )

    @staticmethod
    def _extract_pgmr_tokens(rule: AceBullet) -> set[str]:
        text = " ".join(
            str(text or "")
            for text in [rule.title, rule.content, rule.positive_pattern, rule.avoid]
        )
        return set(re.findall(r"\b(?:pgmr|pgmrc):[A-Za-z_][\w-]*\b", text))

    @staticmethod
    def _extract_main_var(rule: AceBullet) -> str | None:
        text = " ".join(
            str(text or "")
            for text in [rule.title, rule.content, rule.positive_pattern]
        )
        select_match = re.search(r"select\s+(?:distinct\s+)?(\?[A-Za-z_]\w*)", text, flags=re.IGNORECASE)
        if select_match:
            return select_match.group(1).lower()
        vars_found = re.findall(r"\?[A-Za-z_]\w*", text)
        return vars_found[0].lower() if vars_found else None

    @staticmethod
    def _should_prefer_new_pattern(existing: str | None, proposed: str | None) -> bool:
        existing_text = str(existing or "").strip()
        proposed_text = str(proposed or "").strip()
        if not proposed_text:
            return False
        if not existing_text:
            return True
        return len(proposed_text) > len(existing_text)
