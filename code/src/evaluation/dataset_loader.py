import json
from typing import Any

from src.utils.config_loader import get_configured_path


def load_dataset_from_config(dataset_key: str) -> list[dict[str, Any]]:
    dataset_path = get_configured_path(dataset_key)

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data