from __future__ import annotations

from pathlib import Path

from src.train.causal_lm_lora_trainer import run_causal_lm_lora_training
from src.train.config import get_train_run_config, load_train_config
from src.train.seq2seq_trainer import run_seq2seq_training


CAUSAL_LM_LORA_METHODS = {
    "lora",
    "qlora",
    "causal_lm_lora",
    "causal_lm_qlora",
}


def run_training(
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

    if method == "full_finetune":
        return run_seq2seq_training(
            train_config_path=train_config_path,
            run_name=run_name,
            max_train_samples=max_train_samples,
            max_eval_samples=max_eval_samples,
            override_epochs=override_epochs,
            dry_run=dry_run,
        )

    if method in CAUSAL_LM_LORA_METHODS:
        return run_causal_lm_lora_training(
            train_config_path=train_config_path,
            run_name=run_name,
            max_train_samples=max_train_samples,
            max_eval_samples=max_eval_samples,
            override_epochs=override_epochs,
            dry_run=dry_run,
        )

    raise ValueError(
        f"Unsupported training method '{method}'. "
        "Use 'full_finetune' for T5 or 'lora'/'qlora' for Causal-LM adapters."
    )