from __future__ import annotations

import pytest

from src.train.config import validate_train_config


def test_validate_train_config_allows_pgmr_prompt_mode() -> None:
    config = {
        "schema_version": "train_config_schema_v1",
        "runs": {
            "example_pgmr_run": {
                "model": "qwen25_coder_7b_instruct",
                "method": "qlora",
                "task": "pgmr",
                "dataset": {
                    "train_path": "code/data/dataset/pgmr/final/train_with_paraphrases.json",
                    "validation_path": "code/data/dataset/pgmr/final/validation.json",
                    "target_field": "gold_pgmr_sparql",
                },
                "prompt": {"mode": "pgmr"},
                "training": {
                    "num_train_epochs": 1,
                    "learning_rate": 1e-4,
                    "per_device_train_batch_size": 1,
                    "per_device_eval_batch_size": 1,
                    "gradient_accumulation_steps": 1,
                    "max_prompt_length": 1024,
                    "max_target_length": 256,
                    "logging_steps": 10,
                    "evaluation_strategy": "epoch",
                    "save_strategy": "epoch",
                    "save_total_limit": 1,
                    "fp16": False,
                    "seed": 42,
                },
                "lora": {
                    "r": 1,
                    "alpha": 1,
                    "dropout": 0.1,
                    "target_modules": ["q_proj"],
                },
                "output": {
                    "base_dir": "code/models/placeholder",
                    "run_name": "example_pgmr_run",
                },
            }
        },
    }

    validate_train_config(config)
