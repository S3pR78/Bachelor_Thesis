"""Skeleton for the true online ACE loop.

Online ACE updates context during a run: each failed question can trigger one
small rule update, and the same question is retried with the updated context.
The implementation will be added in small, testable steps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from src.ace.online.selection import (
    load_dataset_items,
    select_dataset_items,
    selected_item_ids,
)


@dataclass(frozen=True)
class OnlineAceConfig:
    """Configuration parsed by the thin online ACE CLI wrapper."""

    model: str
    dataset: Path
    prompt_mode: str
    prediction_format: str
    sparql_endpoint: str
    initial_playbook: Path
    output_dir: Path
    family: str | None = None
    pgmr_memory_dir: Path | None = None
    iterations: int = 3
    limit: int | None = None
    shuffle: bool = False
    sample_seed: int = 42
    reflect_model: str = "gpt_4o_mini"
    ace_max_bullets: int = 3
    disable_harmful_rules: bool = False
    delete_harmful_rules: bool = False
    min_harmful_count: int = 2
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of this config."""
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        return data


def run_online_ace_loop(config: OnlineAceConfig) -> int:
    """Run the online ACE loop.

    Step 1 only verifies CLI wiring. Real dataset selection, generation,
    evaluation, reflection, context mutation, and output writing will be added
    in later steps.
    """
    if config.dry_run:
        dataset_items = load_dataset_items(config.dataset)
        selected_items = select_dataset_items(
            dataset_items,
            family=config.family,
            limit=config.limit,
            shuffle=config.shuffle,
            sample_seed=config.sample_seed,
        )

        print("Online ACE dry run configuration:")
        print(json.dumps(config.to_dict(), indent=2, sort_keys=True))
        print()
        print("Selected item IDs:")
        print(json.dumps(selected_item_ids(selected_items), indent=2))
        return 0

    raise NotImplementedError(
        "Online ACE loop is not implemented yet. "
        "Step 1 only adds the package structure and CLI skeleton; use --dry-run "
        "to validate argument parsing."
    )
