"""Validate and load training-run configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TRAIN_CONFIG_SCHEMA_VERSION = "train_config_schema_v1"

TOP_LEVEL_KEYS = {"schema_version", "runs"}

RUN_REQUIRED_KEYS = {
    "model",
    "method",
    "task",
    "dataset",
    "prompt",
    "training",
    "output",
}

RUN_ALLOWED_KEYS = RUN_REQUIRED_KEYS | {
    "lora",
    "quantization",
}

DATASET_REQUIRED_KEYS = {
    "train_path",
    "validation_path",
    "target_field",
}

DATASET_ALLOWED_KEYS = DATASET_REQUIRED_KEYS | {
    "filters",
}

PROMPT_REQUIRED_KEYS = {
    "mode",
}

PROMPT_ALLOWED_KEYS = PROMPT_REQUIRED_KEYS

TRAINING_REQUIRED_KEYS = {
    "num_train_epochs",
    "learning_rate",
    "per_device_train_batch_size",
    "per_device_eval_batch_size",
    "gradient_accumulation_steps",
    "max_target_length",
    "logging_steps",
    "evaluation_strategy",
    "save_strategy",
    "save_total_limit",
    "fp16",
    "seed",
}

TRAINING_ALLOWED_KEYS = TRAINING_REQUIRED_KEYS | {
    "max_source_length",
    "max_prompt_length",
    "bf16",
    "gradient_checkpointing",
    "use_qlora",
    "load_in_4bit",
    "optim",
    "lr_scheduler_type",
    "warmup_ratio",
}

OUTPUT_REQUIRED_KEYS = {
    "base_dir",
    "run_name",
}

OUTPUT_ALLOWED_KEYS = OUTPUT_REQUIRED_KEYS

LORA_REQUIRED_KEYS = {
    "r",
    "alpha",
    "dropout",
    "target_modules",
}

LORA_ALLOWED_KEYS = LORA_REQUIRED_KEYS

QUANTIZATION_ALLOWED_KEYS = {
    "load_in_4bit",
    "bnb_4bit_quant_type",
    "bnb_4bit_use_double_quant",
    "bnb_4bit_compute_dtype",
}

SUPPORTED_METHODS = {
    "full_finetune",
    "lora",
    "qlora",
    "causal_lm_lora",
    "causal_lm_qlora",
}

CAUSAL_LM_ADAPTER_METHODS = {
    "lora",
    "qlora",
    "causal_lm_lora",
    "causal_lm_qlora",
}

SUPPORTED_PROMPT_MODES = {
    "pgmr",
    "pgmr_mini",
    "empire_compass",
    "empire_compass_mini",
    "zero_shot",
    "few_shot",
}

SUPPORTED_TARGET_FIELDS = {
    "gold_pgmr_sparql",
    "gold_sparql",
}


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object.")
    return value


def _validate_allowed_keys(
    obj: dict[str, Any],
    *,
    allowed: set[str],
    context: str,
) -> None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ValueError(f"{context} contains unsupported keys: {unknown}")


def _validate_required_keys(
    obj: dict[str, Any],
    *,
    required: set[str],
    context: str,
) -> None:
    missing = sorted(required - set(obj))
    if missing:
        raise ValueError(f"{context} is missing required keys: {missing}")


def _validate_run(run_name: str, run_config: dict[str, Any]) -> None:
    context = f"Training run '{run_name}'"

    _validate_required_keys(run_config, required=RUN_REQUIRED_KEYS, context=context)
    _validate_allowed_keys(run_config, allowed=RUN_ALLOWED_KEYS, context=context)

    method = str(run_config["method"]).strip()
    if method not in SUPPORTED_METHODS:
        raise ValueError(
            f"{context} has unsupported method {method!r}. "
            f"Supported methods: {sorted(SUPPORTED_METHODS)}"
        )

    dataset = _require_dict(run_config["dataset"], f"{context}.dataset")
    _validate_required_keys(
        dataset,
        required=DATASET_REQUIRED_KEYS,
        context=f"{context}.dataset",
    )
    _validate_allowed_keys(
        dataset,
        allowed=DATASET_ALLOWED_KEYS,
        context=f"{context}.dataset",
    )

    target_field = str(dataset["target_field"]).strip()
    if target_field not in SUPPORTED_TARGET_FIELDS:
        raise ValueError(
            f"{context}.dataset.target_field must be one of "
            f"{sorted(SUPPORTED_TARGET_FIELDS)}, got {target_field!r}"
        )

    filters = dataset.get("filters")
    if filters is not None and not isinstance(filters, dict):
        raise ValueError(f"{context}.dataset.filters must be an object if provided.")

    prompt = _require_dict(run_config["prompt"], f"{context}.prompt")
    _validate_required_keys(
        prompt,
        required=PROMPT_REQUIRED_KEYS,
        context=f"{context}.prompt",
    )
    _validate_allowed_keys(
        prompt,
        allowed=PROMPT_ALLOWED_KEYS,
        context=f"{context}.prompt",
    )

    prompt_mode = str(prompt["mode"]).strip()
    if prompt_mode not in SUPPORTED_PROMPT_MODES:
        raise ValueError(
            f"{context}.prompt.mode must be one of "
            f"{sorted(SUPPORTED_PROMPT_MODES)}, got {prompt_mode!r}"
        )

    training = _require_dict(run_config["training"], f"{context}.training")
    _validate_required_keys(
        training,
        required=TRAINING_REQUIRED_KEYS,
        context=f"{context}.training",
    )
    _validate_allowed_keys(
        training,
        allowed=TRAINING_ALLOWED_KEYS,
        context=f"{context}.training",
    )

    if method == "full_finetune" and "max_source_length" not in training:
        raise ValueError(
            f"{context}.training.max_source_length is required for full_finetune."
        )

    if method in CAUSAL_LM_ADAPTER_METHODS and "max_prompt_length" not in training:
        raise ValueError(
            f"{context}.training.max_prompt_length is required for LoRA/QLoRA."
        )

    if method in CAUSAL_LM_ADAPTER_METHODS:
        lora = _require_dict(run_config.get("lora"), f"{context}.lora")
        _validate_required_keys(
            lora,
            required=LORA_REQUIRED_KEYS,
            context=f"{context}.lora",
        )
        _validate_allowed_keys(
            lora,
            allowed=LORA_ALLOWED_KEYS,
            context=f"{context}.lora",
        )

    if "quantization" in run_config:
        quantization = _require_dict(
            run_config["quantization"],
            f"{context}.quantization",
        )
        _validate_allowed_keys(
            quantization,
            allowed=QUANTIZATION_ALLOWED_KEYS,
            context=f"{context}.quantization",
        )

    output = _require_dict(run_config["output"], f"{context}.output")
    _validate_required_keys(
        output,
        required=OUTPUT_REQUIRED_KEYS,
        context=f"{context}.output",
    )
    _validate_allowed_keys(
        output,
        allowed=OUTPUT_ALLOWED_KEYS,
        context=f"{context}.output",
    )


def validate_train_config(config: dict[str, Any]) -> None:
    _validate_allowed_keys(
        config,
        allowed=TOP_LEVEL_KEYS,
        context="Train config",
    )

    schema_version = config.get("schema_version")
    if schema_version != TRAIN_CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"Train config schema_version must be "
            f"{TRAIN_CONFIG_SCHEMA_VERSION!r}, got {schema_version!r}"
        )

    runs = _require_dict(config.get("runs"), "Train config.runs")
    if not runs:
        raise ValueError("Train config must contain at least one run.")

    for run_name, run_config in runs.items():
        if not isinstance(run_name, str) or not run_name.strip():
            raise ValueError("Training run names must be non-empty strings.")
        _validate_run(run_name, _require_dict(run_config, f"Training run '{run_name}'"))


def load_train_config(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Train config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    validate_train_config(config)
    return config


def get_train_run_config(config: dict[str, Any], run_name: str) -> dict[str, Any]:
    runs = config.get("runs", {})

    if run_name not in runs:
        available = ", ".join(sorted(runs.keys()))
        raise KeyError(
            f"Unknown training run '{run_name}'.\n"
            f"Available runs: {available}"
        )

    return runs[run_name]
