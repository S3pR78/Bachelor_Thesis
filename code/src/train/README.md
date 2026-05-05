# Train Package

`src/train/` contains dataset conversion and training runners for fine-tuning text-to-query models.

## Main Entry

Training is exposed through:

```bash
PYTHONPATH=code python code/src/main.py train \
  --run <run-key>
```

Run keys are configured in:

```text
code/config/train_config.json
```

Use `--dry-run` first to validate the dataset and prompt construction without loading/training a model:

```bash
PYTHONPATH=code python code/src/main.py train \
  --run qwen25_coder_7b_pgmr_mini_qlora_3ep \
  --dry-run
```

## Modules

| Module | Purpose |
| --- | --- |
| `config.py` | Loads and validates training run configuration. |
| `dataset.py` | Builds training examples from dataset entries and prompt templates. |
| `causal_lm_dataset.py` | Dataset wrapper for causal language model fine-tuning. |
| `seq2seq_trainer.py` | Full fine-tuning runner for seq2seq models such as T5. |
| `causal_lm_lora_trainer.py` | LoRA/QLoRA runner for causal LMs such as Qwen or Mistral. |
| `runner.py` | Dispatches a training run to the correct trainer based on configured method. |

## Supported Methods

- `full_finetune`: full seq2seq fine-tuning
- `lora` / `qlora`: adapter fine-tuning for causal LMs

Training outputs are written under the `output.base_dir` and `output.run_name` configured for each run.
