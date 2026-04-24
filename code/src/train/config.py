from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_train_config(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Train config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    if "runs" not in config or not isinstance(config["runs"], dict):
        raise ValueError("Train config must contain a top-level 'runs' object.")

    return config


def get_train_run_config(config: dict[str, Any], run_name: str) -> dict[str, Any]:
    runs = config.get("runs", {})

    if run_name not in runs:
        available = ", ".join(sorted(runs.keys()))
        raise KeyError(
            f"Unknown training run '{run_name}'. Available runs: {available}"
        )

    run_config = runs[run_name]

    required_keys = ["model", "method", "task", "dataset", "prompt", "training", "output"]
    missing = [key for key in required_keys if key not in run_config]

    if missing:
        raise ValueError(f"Training run '{run_name}' is missing keys: {missing}")

    return run_config
