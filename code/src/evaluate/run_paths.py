from datetime import datetime, timezone
from pathlib import Path

from src.utils.config_loader import get_configured_path


def make_safe_name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Value must be a non-empty string.")
    
    return "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in value.strip()
    )