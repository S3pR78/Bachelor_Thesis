"""Full fine-tuning runner for seq2seq text-to-text models."""

from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.train.config import get_train_run_config, load_train_config
from src.train.dataset import build_training_examples, load_dataset


DEFAULT_MODEL_CONFIG_PATH = Path("code/config/model_config.json")


def load_model_config(path: Path = DEFAULT_MODEL_CONFIG_PATH) -> dict[str, Any]:
    """Load the model registry used by training runs."""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Model config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    if "models" not in config or not isinstance(config["models"], dict):
        raise ValueError("Model config must contain a top-level 'models' object.")

    return config


def get_model_entry(model_config: dict[str, Any], model_key: str) -> dict[str, Any]:
    models = model_config["models"]

    if model_key not in models:
        available = ", ".join(sorted(models.keys()))
        raise KeyError(f"Unknown model '{model_key}'. Available models: {available}")

    return models[model_key]


def utc_run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_output_dir(run_config: dict[str, Any], run_name: str) -> Path:
    """Create a timestamped output directory for one training run."""
    output_config = run_config["output"]
    base_dir = Path(output_config["base_dir"])
    configured_run_name = str(output_config.get("run_name", run_name))

    return base_dir / configured_run_name / utc_run_timestamp()


def load_training_examples_from_run_config(
    run_config: dict[str, Any],
    split: str,
    limit: int | None = None,
) -> list[dict[str, str]]:
    """Load train/validation examples according to one run config."""
    dataset_config = run_config["dataset"]
    prompt_config = run_config["prompt"]
    target_field = dataset_config["target_field"]
    required_status = dataset_config.get("required_status")
    filters = dataset_config.get("filters")

    if split == "train":
        dataset_path = Path(dataset_config["train_path"])
    elif split == "validation":
        dataset_path = Path(dataset_config["validation_path"])
    else:
        raise ValueError(f"Unsupported split: {split}")

    entries = load_dataset(dataset_path)

    return build_training_examples(
        entries=entries,
        prompt_config=prompt_config,
        target_field=target_field,
        required_status=required_status,
        filters=filters,
        limit=limit,
    )


def build_seq2seq_training_args(
    output_dir: Path,
    training_config: dict[str, Any],
    override_epochs: int | None = None,
):
    import torch
    from transformers import Seq2SeqTrainingArguments

    num_train_epochs = (
        override_epochs
        if override_epochs is not None
        else training_config["num_train_epochs"]
    )

    fp16 = bool(training_config.get("fp16", False))
    if fp16 and not torch.cuda.is_available():
        print("fp16=True requested, but CUDA is not available. Disabling fp16.")
        fp16 = False

    evaluation_strategy = training_config.get(
        "evaluation_strategy",
        training_config.get("eval_strategy", "epoch"),
    )

    kwargs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "num_train_epochs": num_train_epochs,
        "learning_rate": float(training_config["learning_rate"]),
        "per_device_train_batch_size": int(training_config["per_device_train_batch_size"]),
        "per_device_eval_batch_size": int(training_config["per_device_eval_batch_size"]),
        "gradient_accumulation_steps": int(
            training_config.get("gradient_accumulation_steps", 1)
        ),
        "logging_steps": int(training_config.get("logging_steps", 25)),
        "save_strategy": training_config.get("save_strategy", "epoch"),
        "save_total_limit": int(training_config.get("save_total_limit", 2)),
        "fp16": fp16,
        "predict_with_generate": True,
        "report_to": [],
    }

    signature = inspect.signature(Seq2SeqTrainingArguments)
    if "eval_strategy" in signature.parameters:
        kwargs["eval_strategy"] = evaluation_strategy
    else:
        kwargs["evaluation_strategy"] = evaluation_strategy

    return Seq2SeqTrainingArguments(**kwargs)


def create_text_to_text_dataset(
    examples: list[dict[str, str]],
    tokenizer: Any,
    max_source_length: int,
    max_target_length: int,
):
    import torch
    from torch.utils.data import Dataset

    class TextToTextDataset(Dataset):
        def __init__(self) -> None:
            inputs = [example["input_text"] for example in examples]
            targets = [example["target_text"] for example in examples]

            model_inputs = tokenizer(
                inputs,
                max_length=max_source_length,
                truncation=True,
                padding=False,
            )

            try:
                labels = tokenizer(
                    text_target=targets,
                    max_length=max_target_length,
                    truncation=True,
                    padding=False,
                )
            except TypeError:
                with tokenizer.as_target_tokenizer():
                    labels = tokenizer(
                        targets,
                        max_length=max_target_length,
                        truncation=True,
                        padding=False,
                    )

            model_inputs["labels"] = labels["input_ids"]
            self.encodings = model_inputs

        def __len__(self) -> int:
            return len(examples)

        def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
            return {
                key: torch.tensor(value[index])
                for key, value in self.encodings.items()
            }

    return TextToTextDataset()


def run_seq2seq_training(
    train_config_path: Path,
    run_name: str,
    max_train_samples: int | None = None,
    max_eval_samples: int | None = None,
    override_epochs: int | None = None,
    dry_run: bool = False,
) -> int:
    train_config = load_train_config(train_config_path)
    run_config = get_train_run_config(train_config, run_name)

    model_key = str(run_config["model"])
    method = str(run_config["method"])
    task = str(run_config["task"])

    if method != "full_finetune":
        raise ValueError(f"This trainer only supports method='full_finetune', got: {method}")

    model_config = load_model_config()
    model_entry = get_model_entry(model_config, model_key)

    if model_entry.get("provider") != "huggingface":
        raise ValueError("Seq2Seq trainer only supports Hugging Face models.")

    if model_entry.get("interface") != "seq2seq":
        raise ValueError(
            f"Seq2Seq trainer expects interface='seq2seq', got: {model_entry.get('interface')}"
        )

    model_id = str(model_entry["model_id"])
    paths = model_entry.get("paths", {})
    cache_dir = paths.get("cache_dir")

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
    print("Model id:", model_id)
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

    import torch
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Seq2SeqTrainer,
        set_seed,
    )

    set_seed(int(run_config["training"].get("seed", 42)))

    output_dir = build_output_dir(run_config, run_name)
    final_model_dir = output_dir / "final_model"
    output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        cache_dir=cache_dir,
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_id,
        cache_dir=cache_dir,
    )

    max_source_length = int(run_config["training"]["max_source_length"])
    max_target_length = int(run_config["training"]["max_target_length"])

    train_dataset = create_text_to_text_dataset(
        examples=train_examples,
        tokenizer=tokenizer,
        max_source_length=max_source_length,
        max_target_length=max_target_length,
    )
    eval_dataset = create_text_to_text_dataset(
        examples=eval_examples,
        tokenizer=tokenizer,
        max_source_length=max_source_length,
        max_target_length=max_target_length,
    )

    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
    )

    training_args = build_seq2seq_training_args(
        output_dir=output_dir,
        training_config=run_config["training"],
        override_epochs=override_epochs,
    )

    metadata = {
        "run_name": run_name,
        "task": task,
        "model_key": model_key,
        "model_id": model_id,
        "method": method,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "train_examples": len(train_examples),
        "eval_examples": len(eval_examples),
        "train_config_path": str(train_config_path),
        "model_config_path": str(DEFAULT_MODEL_CONFIG_PATH),
        "output_dir": str(output_dir),
        "final_model_dir": str(final_model_dir),
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

    trainer_signature = inspect.signature(Seq2SeqTrainer)
    if "processing_class" in trainer_signature.parameters:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in trainer_signature.parameters:
        trainer_kwargs["tokenizer"] = tokenizer

    trainer = Seq2SeqTrainer(**trainer_kwargs)

    train_result = trainer.train()
    train_metrics = train_result.metrics
    trainer.save_metrics("train", train_metrics)
    trainer.save_state()

    eval_metrics = trainer.evaluate()
    trainer.save_metrics("eval", eval_metrics)

    trainer.save_model(str(final_model_dir))
    tokenizer.save_pretrained(str(final_model_dir))

    save_json(
        output_dir / "final_metrics.json",
        {
            "train": train_metrics,
            "eval": eval_metrics,
        },
    )

    print("\nTraining finished.")
    print(f"Run output directory: {output_dir}")
    print(f"Final model directory: {final_model_dir}")

    return 0
