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
    """Resolve the ACE playbook path for a model/family/mode.

    Priority:
    1. explicit --ace-playbook path
    2. model-specific playbook:
       <dir>/<model>/<family>_<mode>_playbook.json
    3. shared playbook:
       <dir>/<family>_<mode>_playbook.json
    4. family-only shared playbook:
       <dir>/<family>_playbook.json
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
        candidates.append(root / safe_model / f"{safe_family}_{safe_mode}_playbook.json")
        candidates.append(root / safe_model / f"{safe_family}_playbook.json")

    candidates.append(root / f"{safe_family}_{safe_mode}_playbook.json")
    candidates.append(root / f"{safe_family}_playbook.json")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None
