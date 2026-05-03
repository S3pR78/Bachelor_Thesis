from __future__ import annotations

import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.model_loader import get_model_dir
from src.train.causal_lm_dataset import (
    CausalLMMaskedCollator,
    CausalLMPromptTargetDataset,
)
from src.train.config import get_train_run_config, load_train_config
from src.train.seq2seq_trainer import (
    DEFAULT_MODEL_CONFIG_PATH,
    build_output_dir,
    get_model_entry,
    load_model_config,
    load_training_examples_from_run_config,
    save_json,
)


SUPPORTED_METHODS = {"lora", "qlora", "causal_lm_lora", "causal_lm_qlora"}


def _resolve_model_source(model_entry: dict[str, Any]) -> tuple[str, bool]:
    try:
        return str(get_model_dir(model_entry)), True
    except FileNotFoundError:
        return str(model_entry["model_id"]), False


def _torch_dtype_from_name(dtype_name: str):
    import torch

    normalized = str(dtype_name).strip().lower()
    if normalized in {"bf16", "bfloat16"}:
        return torch.bfloat16
    if normalized in {"fp16", "float16"}:
        return torch.float16
    if normalized in {"fp32", "float32"}:
        return torch.float32
    raise ValueError(f"Unsupported torch dtype: {dtype_name}")


def _load_tokenizer(model_source: str, cache_dir: str | None, local_files_only: bool):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        model_source,
        cache_dir=cache_dir,
        local_files_only=local_files_only,
        use_fast=True,
    )

    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    return tokenizer


def _build_bnb_config(run_config: dict[str, Any]):
    import torch
    from transformers import BitsAndBytesConfig

    quantization_config = run_config.get("quantization", {})
    training_config = run_config["training"]

    compute_dtype_name = (
        quantization_config.get("bnb_4bit_compute_dtype")
        or training_config.get("bnb_4bit_compute_dtype")
        or "float16"
    )

    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=bool(
            quantization_config.get("bnb_4bit_use_double_quant", True)
        ),
        bnb_4bit_quant_type=str(
            quantization_config.get("bnb_4bit_quant_type", "nf4")
        ),
        bnb_4bit_compute_dtype=_torch_dtype_from_name(compute_dtype_name),
    )


def _get_lora_values(run_config: dict[str, Any]) -> dict[str, Any]:
    training_config = run_config["training"]
    lora_config = run_config.get("lora", {})

    return {
        "r": int(lora_config.get("r", training_config.get("lora_r", 16))),
        "lora_alpha": int(
            lora_config.get("alpha", training_config.get("lora_alpha", 32))
        ),
        "lora_dropout": float(
            lora_config.get("dropout", training_config.get("lora_dropout", 0.05))
        ),
        "target_modules": lora_config.get(
            "target_modules",
            training_config.get(
                "target_modules",
                [
                    "q_proj",
                    "k_proj",
                    "v_proj",
                    "o_proj",
                    "gate_proj",
                    "up_proj",
                    "down_proj",
                ],
            ),
        ),
    }


def _load_lora_model(
    *,
    model_source: str,
    cache_dir: str | None,
    local_files_only: bool,
    run_config: dict[str, Any],
    use_qlora: bool,
    load_in_4bit: bool,
):
    import torch
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM

    training_config = run_config["training"]

    dtype_name = str(training_config.get("torch_dtype", "float16"))
    torch_dtype = _torch_dtype_from_name(dtype_name)

    model_kwargs: dict[str, Any] = {
        "cache_dir": cache_dir,
        "local_files_only": local_files_only,
        "low_cpu_mem_usage": True,
    }

    if torch.cuda.is_available():
        model_kwargs["device_map"] = "auto"
        model_kwargs["torch_dtype"] = torch_dtype

    if load_in_4bit:
        model_kwargs["quantization_config"] = _build_bnb_config(run_config)

    model = AutoModelForCausalLM.from_pretrained(
        model_source,
        **model_kwargs,
    )

    if hasattr(model.config, "use_cache"):
        model.config.use_cache = False

    if use_qlora or load_in_4bit:
        model = prepare_model_for_kbit_training(model)

    lora_values = _get_lora_values(run_config)
    peft_config = LoraConfig(
        r=lora_values["r"],
        lora_alpha=lora_values["lora_alpha"],
        lora_dropout=lora_values["lora_dropout"],
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=lora_values["target_modules"],
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    return model


def build_causal_lm_training_args(
    *,
    output_dir: Path,
    training_config: dict[str, Any],
    use_qlora: bool,
    override_epochs: int | None,
):
    import torch
    from transformers import TrainingArguments

    num_train_epochs = (
        override_epochs
        if override_epochs is not None
        else training_config["num_train_epochs"]
    )

    fp16 = bool(training_config.get("fp16", torch.cuda.is_available()))
    bf16 = bool(training_config.get("bf16", False))

    if not torch.cuda.is_available():
        fp16 = False
        bf16 = False

    evaluation_strategy = training_config.get(
        "evaluation_strategy",
        training_config.get("eval_strategy", "epoch"),
    )

    kwargs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "num_train_epochs": num_train_epochs,
        "learning_rate": float(training_config["learning_rate"]),
        "per_device_train_batch_size": int(
            training_config.get("per_device_train_batch_size", 1)
        ),
        "per_device_eval_batch_size": int(
            training_config.get("per_device_eval_batch_size", 1)
        ),
        "gradient_accumulation_steps": int(
            training_config.get("gradient_accumulation_steps", 1)
        ),
        "logging_steps": int(training_config.get("logging_steps", 10)),
        "save_strategy": training_config.get("save_strategy", "epoch"),
        "save_total_limit": int(training_config.get("save_total_limit", 2)),
        "fp16": fp16,
        "bf16": bf16,
        "report_to": [],
        "remove_unused_columns": False,
        "gradient_checkpointing": bool(
            training_config.get("gradient_checkpointing", True)
        ),
        "optim": training_config.get(
            "optim",
            "paged_adamw_8bit" if use_qlora else "adamw_torch",
        ),
        "lr_scheduler_type": training_config.get("lr_scheduler_type", "cosine"),
        "warmup_ratio": float(training_config.get("warmup_ratio", 0.03)),
    }

    signature = inspect.signature(TrainingArguments)
    if "eval_strategy" in signature.parameters:
        kwargs["eval_strategy"] = evaluation_strategy
    else:
        kwargs["evaluation_strategy"] = evaluation_strategy

    return TrainingArguments(**kwargs)


def run_causal_lm_lora_training(
    train_config_path: Path,
    run_name: str,
    max_train_samples: int | None = None,
    max_eval_samples: int | None = None,
    override_epochs: int | None = None,
    dry_run: bool = False,
) -> int:
    train_config = load_train_config(train_config_path)
    run_config = get_train_run_config(train_config, run_name)

    method = str(run_config["method"]).strip().lower()
    if method not in SUPPORTED_METHODS:
        raise ValueError(
            f"Causal-LM LoRA trainer supports {sorted(SUPPORTED_METHODS)}, got: {method}"
        )

    model_key = str(run_config["model"])
    task = str(run_config["task"])

    model_config = load_model_config()
    model_entry = get_model_entry(model_config, model_key)

    if model_entry.get("provider") != "huggingface":
        raise ValueError("Causal-LM LoRA trainer only supports Hugging Face models.")

    if model_entry.get("interface") != "causal_lm":
        raise ValueError(
            "Causal-LM LoRA trainer expects interface='causal_lm', "
            f"got: {model_entry.get('interface')}"
        )

    training_config = run_config["training"]
    quantization_config = run_config.get("quantization", {})

    use_qlora = bool(
        training_config.get(
            "use_qlora",
            method in {"qlora", "causal_lm_qlora"},
        )
    )
    load_in_4bit = bool(
        training_config.get(
            "load_in_4bit",
            quantization_config.get("load_in_4bit", use_qlora),
        )
    )

    train_examples = load_training_examples_from_run_config(
        run_config,
        split="train",
        limit=max_train_samples,
    )
    eval_examples = load_training_examples_from_run_config(
        run_config,
        split="validation",
        limit=max_eval_samples,
    )

    print("Training run:", run_name)
    print("Task:", task)
    print("Model key:", model_key)
    print("Method:", method)
    print("Use QLoRA:", use_qlora)
    print("Load in 4bit:", load_in_4bit)
    print("Train examples:", len(train_examples))
    print("Eval examples:", len(eval_examples))

    if not train_examples:
        raise ValueError("No training examples prepared.")
    if not eval_examples:
        raise ValueError("No validation examples prepared.")

    print("\nFirst training input:")
    print(train_examples[0]["input_text"])
    print("\nFirst training target:")
    print(train_examples[0]["target_text"])

    if dry_run:
        print("\nDry run finished. No model was loaded and no training was started.")
        return 0

    from transformers import Trainer, set_seed

    set_seed(int(training_config.get("seed", 42)))

    model_source, local_files_only = _resolve_model_source(model_entry)
    cache_dir = model_entry.get("paths", {}).get("cache_dir")

    output_dir = build_output_dir(run_config, run_name)
    final_adapter_dir = output_dir / "final_adapter"
    output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = _load_tokenizer(
        model_source=model_source,
        cache_dir=cache_dir,
        local_files_only=local_files_only,
    )

    model = _load_lora_model(
        model_source=model_source,
        cache_dir=cache_dir,
        local_files_only=local_files_only,
        run_config=run_config,
        use_qlora=use_qlora,
        load_in_4bit=load_in_4bit,
    )

    if tokenizer.pad_token_id is not None:
        model.config.pad_token_id = tokenizer.pad_token_id

    max_prompt_length = int(
        training_config.get(
            "max_prompt_length",
            training_config.get("max_source_length", 512),
        )
    )
    max_target_length = int(training_config.get("max_target_length", 512))

    train_dataset = CausalLMPromptTargetDataset(
        examples=train_examples,
        tokenizer=tokenizer,
        max_prompt_length=max_prompt_length,
        max_target_length=max_target_length,
    )
    eval_dataset = CausalLMPromptTargetDataset(
        examples=eval_examples,
        tokenizer=tokenizer,
        max_prompt_length=max_prompt_length,
        max_target_length=max_target_length,
    )

    data_collator = CausalLMMaskedCollator(tokenizer=tokenizer)

    training_args = build_causal_lm_training_args(
        output_dir=output_dir,
        training_config=training_config,
        use_qlora=use_qlora,
        override_epochs=override_epochs,
    )

    metadata = {
        "run_name": run_name,
        "task": task,
        "model_key": model_key,
        "model_id": model_entry["model_id"],
        "method": method,
        "use_qlora": use_qlora,
        "load_in_4bit": load_in_4bit,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "train_examples": len(train_examples),
        "eval_examples": len(eval_examples),
        "train_config_path": str(train_config_path),
        "model_config_path": str(DEFAULT_MODEL_CONFIG_PATH),
        "output_dir": str(output_dir),
        "final_adapter_dir": str(final_adapter_dir),
        "max_train_samples": max_train_samples,
        "max_eval_samples": max_eval_samples,
        "override_epochs": override_epochs,
        "train_config_used": run_config,
    }
    save_json(output_dir / "run_metadata.json", metadata)

    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset,
        "data_collator": data_collator,
    }

    trainer_signature = inspect.signature(Trainer)
    if "processing_class" in trainer_signature.parameters:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in trainer_signature.parameters:
        trainer_kwargs["tokenizer"] = tokenizer

    trainer = Trainer(**trainer_kwargs)

    train_result = trainer.train()
    train_metrics = train_result.metrics
    trainer.save_metrics("train", train_metrics)
    trainer.save_state()

    eval_metrics = trainer.evaluate()
    trainer.save_metrics("eval", eval_metrics)

    final_adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(final_adapter_dir))
    tokenizer.save_pretrained(str(final_adapter_dir))

    save_json(
        output_dir / "final_metrics.json",
        {
            "train": train_metrics,
            "eval": eval_metrics,
        },
    )

    print("\nTraining finished.")
    print(f"Run output directory: {output_dir}")
    print(f"Final adapter directory: {final_adapter_dir}")
    return 0