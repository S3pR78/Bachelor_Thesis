# Train Source Package

This package contains data loading and training utilities for fine-tuning models.

## Modules

- `causal_lm_dataset.py`
  - Builds datasets for causal language model training.
- `causal_lm_lora_trainer.py`
  - Trainer implementation for LoRA-based fine-tuning on causal language models.
- `config.py`
  - Configuration parsing and training settings.
- `dataset.py`
  - Dataset wrappers and loading helpers for training.
- `runner.py`
  - Orchestrates the training run.
- `seq2seq_trainer.py`
  - Trainer implementation for sequence-to-sequence model training.

## Usage

Use these modules for building and executing training pipelines on custom datasets.
