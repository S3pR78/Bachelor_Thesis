# Core Package

`src/core/` contains model and provider integration code shared by query generation, evaluation, training, and OpenAI-backed tools.

## Modules

| Module | Purpose |
| --- | --- |
| `model_loader.py` | Loads local Hugging Face seq2seq or causal-LM models, optional PEFT adapters, tokenizers, and raw generation responses. |
| `openai_provider.py` | Creates OpenAI clients and sends chat-completion requests. |
| `download_manager.py` | Resolves/downloads original Hugging Face model snapshots into local model directories. |

## Model Configuration

Models are selected by keys from:

```text
code/config/model_config.json
```

Each model entry defines:

- `provider`: `huggingface` or `openai`
- `model_id`: provider model identifier
- `interface`: `seq2seq`, `causal_lm`, or `chat`
- local `paths`, such as `model_root`, `cache_dir`, and `finetuned_path`
- optional `adapter_path` for LoRA/QLoRA models
- generation settings such as `max_new_tokens`, `temperature`, and `do_sample`

## Important Behavior

Local Hugging Face models are loaded with `local_files_only=True`. If the configured model directory does not exist under `code/models/`, loading fails instead of downloading automatically during inference.

OpenAI models require an API key. `openai_provider.py` loads `.env` from the repository root, so this file works:

```bash
OPENAI_API_KEY=...
```

You can also set the same key as a shell environment variable:

```bash
export OPENAI_API_KEY=...
```

Do not commit your real `.env` file.
