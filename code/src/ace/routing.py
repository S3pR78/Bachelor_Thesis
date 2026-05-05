"""Resolve model/family/mode-specific ACE playbook files."""

from __future__ import annotations

import re
from pathlib import Path


def safe_name(value: str | None) -> str:
    """Convert model/family/mode names into filesystem-safe names."""
    text = str(value or "").strip().lower()
    text = text.replace("/", "_").replace("-", "_")
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def resolve_ace_playbook_path(
    *,
    ace_playbook_path: str | None = None,
    ace_playbook_dir: str | None = None,
    family: str | None,
    mode: str | None,
    model_name: str | None = None,
) -> str | None:
    """Resolve an ACE playbook for model/family/mode.

    Priority:
    1. explicit --ace-playbook path
    2. model-specific playbook:
       <dir>/<model>/<family>_<mode>_playbook.json
    3. shared playbook:
       <dir>/shared/<family>_<mode>_playbook.json
    4. legacy fallback:
       <dir>/<family>_<mode>_playbook.json
    """
    if ace_playbook_path:
        return ace_playbook_path

    if not ace_playbook_dir or not family or not mode:
        return None

    root = Path(ace_playbook_dir)
    safe_family = safe_name(family)
    safe_mode = safe_name(mode)
    safe_model = safe_name(model_name)

    candidates: list[Path] = []

    if safe_model:
        candidates.extend(
            [
                root / safe_model / f"{safe_family}_{safe_mode}_playbook.json",
                root / safe_model / f"{safe_family}_playbook.json",
            ]
        )

    candidates.extend(
        [
            root / "shared" / f"{safe_family}_{safe_mode}_playbook.json",
            root / "shared" / f"{safe_family}_playbook.json",
            root / f"{safe_family}_{safe_mode}_playbook.json",
            root / f"{safe_family}_playbook.json",
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None
