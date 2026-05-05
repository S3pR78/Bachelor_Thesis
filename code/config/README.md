# Configuration

`code/config/` contains JSON configuration files used by the CLI, tools, prompt builders, model loaders, training runners, and dataset validators.

## Files

| File | Purpose |
| --- | --- |
| `path_config.json` | Central path registry for datasets, prompts, outputs, configs, and model-related assets. |
| `model_config.json` | Model registry. Defines model keys, provider, model ID, interface, local paths, generation settings, and optional adapters. |
| `train_config.json` | Training run registry. Defines datasets, prompt mode, training method/settings, LoRA/QLoRA settings, and output directories. |
| `schemas/benchmark_dataset_schema_v1.json` | Schema for benchmark dataset entries. |
| `schemas/model_config.schema.v1.json` | Schema for model config structure. |
| `schemas/train_config_schema_v1.json` | Schema for training config structure. |
| `archive/` | Historical configuration snapshots. |

## Model Keys

Most commands use `--model <key>`, where `<key>` must exist in `model_config.json`.

Examples:

- `gpt_4o_mini`
- `t5_base`
- `t5_base_pgmr_mini_15ep`
- `qwen25_coder_7b_instruct`
- `qwen25_coder_7b_pgmr_mini_qlora`
- `mistral_7b_instruct`
- `mistral_7b_pgmr_mini_qlora`

OpenAI models use `provider: openai` and need `OPENAI_API_KEY`. The key can be exported in the shell or stored in a repo-root `.env` file. Hugging Face/local models use paths under `code/models/` and are loaded locally.

## Training Runs

Training commands use `--run <key>`, where `<key>` must exist under `runs` in `train_config.json`.

Example:

```bash
PYTHONPATH=code python code/src/main.py train \
  --run qwen25_coder_7b_pgmr_mini_qlora_3ep \
  --dry-run
```

Use `--dry-run` first to inspect prepared examples without loading a model.
