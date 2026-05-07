# Fine-Tuning Setup Analysis

This document summarizes the current repository state relevant to fine-tuning for the thesis project. It is a technical basis for later methodology and results writing, not a final thesis section.

Facts below are taken from the repository files and local artifacts inspected on 2026-05-07. Interpretive comments are explicitly marked as interpretation.

## 1. Repository Areas Relevant for Fine-Tuning

### Core configuration files

| Path | Role |
| --- | --- |
| `README.md` | High-level project overview. It defines the main Text-to-SPARQL and PGMR-lite workflows, the main CLI, dataset locations, model configuration, and known setup notes. |
| `code/README.md` | Implementation map for `src/`, `tools/`, `data/`, `prompts/`, `config/`, `outputs/`, and tests. |
| `code/config/train_config.json` | Main fine-tuning run registry. It defines run keys, model keys, method, task, dataset paths, target fields, prompt modes, training hyperparameters, LoRA/QLoRA settings, quantization settings, and output directories. |
| `code/config/model_config.json` | Model registry. It maps model keys to Hugging Face or OpenAI model IDs, interface type, local model paths, generation settings, and adapter/fine-tuned paths. |
| `code/config/path_config.json` | Central path registry used by prompt builders, evaluation, dataset tooling, and prompt lookup. It includes prompt paths for Empire Compass mini, PGMR mini, and PGMR. |
| `code/config/schemas/train_config_schema_v1.json` | JSON schema for training configs. It constrains supported methods, target fields, prompt modes, training keys, LoRA keys, and quantization keys. |

### Training code

| Path | Role |
| --- | --- |
| `code/src/main.py` | Main CLI entry point. The `train` subcommand dispatches configured fine-tuning runs. |
| `code/src/train/config.py` | Loads and validates `train_config.json`. It checks schema version, required keys, supported methods, prompt modes, target fields, LoRA requirements, and length-field requirements. |
| `code/src/train/runner.py` | Selects the trainer implementation based on `method`. `full_finetune` goes to the seq2seq trainer; `lora` and `qlora` methods go to the causal LM adapter trainer. |
| `code/src/train/dataset.py` | Loads dataset JSON files, applies filters, selects target fields, and builds prompt/target examples. |
| `code/src/train/seq2seq_trainer.py` | Full fine-tuning runner for seq2seq models such as T5. |
| `code/src/train/causal_lm_dataset.py` | Prompt/target tokenization for causal LMs. It masks prompt tokens with `-100` so loss is computed only on the target query. |
| `code/src/train/causal_lm_lora_trainer.py` | LoRA/QLoRA trainer for causal language models such as Qwen2.5-Coder and Mistral. |

### Prompting and query code

| Path | Role |
| --- | --- |
| `code/src/query/prompt_builder.py` | Builds prompts for `empire_compass`, `empire_compass_mini`, `pgmr`, `pgmr_mini`, `zero_shot`, and `few_shot`. Training uses the same prompt-building functions as querying/evaluation for standard prompt modes. |
| `code/prompts/empire_compass_mini/` | Mini direct-SPARQL prompt templates for `nlp4re` and `empirical_research_practice`. |
| `code/prompts/pgmr_mini/` | Mini PGMR-lite prompt templates for both template families. |
| `code/prompts/pgmr/` | Full PGMR-lite prompt templates for both template families. |
| `code/prompts/empire_compass/` | Full Empire Compass prompt generation assets and rendered prompts. |

### Datasets and PGMR tooling

| Path | Role |
| --- | --- |
| `code/data/dataset/final/` | Final direct-SPARQL dataset files. These contain `gold_sparql` and are used for direct-SPARQL fine-tuning and evaluation. |
| `code/data/dataset/pgmr/final/` | PGMR-lite transformed dataset files. These contain both `gold_sparql` and `gold_pgmr_sparql`, plus PGMR status metadata. |
| `code/data/orkg_memory/templates/` | PGMR memory files used to transform/restore placeholder queries. |
| `code/tools/dataset/create_train_with_paraphrases.py` | Expands train data by turning paraphrased questions into additional training items while keeping the gold query unchanged. |
| `code/tools/pgmr/transform_dataset.py` | Converts `gold_sparql` into `gold_pgmr_sparql`, adding `pgmr_status`, replaced terms, and unmapped terms. |

### Models, outputs, and Slurm scripts

| Path | Role |
| --- | --- |
| `code/models/` | Local original models and fine-tuned artifacts. T5 fine-tuning saves a full final model. Qwen/Mistral QLoRA runs save adapters and checkpoints. |
| `code/outputs/evaluation_runs/` | Evaluation outputs for original and fine-tuned models. Fine-tuned model evaluations exist for T5 PGMR-mini, Qwen PGMR, Qwen Empire Compass, Mistral PGMR, and Mistral Empire Compass. |
| `code/outputs/slurm_logs/` | Existing Slurm log files for training, evaluation, querying, and ACE. Detailed log extraction is left for Section 6 after logs are provided. |
| `code/scripts/slurm/training/` | Slurm scripts for the five configured training runs. These scripts request 1 GPU, 8 CPUs, and 80G memory. |

## 2. Training Configuration Overview

Source: `code/config/train_config.json`

Schema version: `train_config_schema_v1`

The config currently defines five fine-tuning runs:

1. `t5_base_pgmr_mini_full_finetune_15ep`
2. `qwen25_coder_7b_pgmr_qlora_3ep`
3. `qwen25_coder_7b_empire_compass_qlora_3ep`
4. `mistral_7b_pgmr_qlora_3ep`
5. `mistral_7b_empire_compass_qlora_3ep`

### Run summary table

| Run name | Model key | Base model | Method | Task | Train path | Validation path | Target field | Prompt mode | Prediction format |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `t5_base_pgmr_mini_full_finetune_15ep` | `t5_base` | `google-t5/t5-base` | `full_finetune` | `pgmr_mini` | `code/data/dataset/pgmr/final/train_with_paraphrases.json` | `code/data/dataset/pgmr/final/validation.json` | `gold_pgmr_sparql` | `pgmr_mini` | `pgmr lite` |
| `qwen25_coder_7b_pgmr_qlora_3ep` | `qwen25_coder_7b_instruct` | `Qwen/Qwen2.5-Coder-7B-Instruct` | `qlora` | `pgmr` | `code/data/dataset/pgmr/final/train_with_paraphrases.json` | `code/data/dataset/pgmr/final/validation.json` | `gold_pgmr_sparql` | `pgmr` | `pgmr lite` |
| `qwen25_coder_7b_empire_compass_qlora_3ep` | `qwen25_coder_7b_instruct` | `Qwen/Qwen2.5-Coder-7B-Instruct` | `qlora` | `direct_sparql` | `code/data/dataset/final/train_with_paraphrases.json` | `code/data/dataset/final/validation.json` | `gold_sparql` | `empire_compass` | `direct sparql` |
| `mistral_7b_pgmr_qlora_3ep` | `mistral_7b_instruct` | `mistralai/Mistral-7B-Instruct-v0.3` | `qlora` | `pgmr` | `code/data/dataset/pgmr/final/train_with_paraphrases.json` | `code/data/dataset/pgmr/final/validation.json` | `gold_pgmr_sparql` | `pgmr` | `pgmr lite` |
| `mistral_7b_empire_compass_qlora_3ep` | `mistral_7b_instruct` | `mistralai/Mistral-7B-Instruct-v0.3` | `qlora` | `direct_sparql` | `code/data/dataset/final/train_with_paraphrases.json` | `code/data/dataset/final/validation.json` | `gold_sparql` | `empire_compass` | `direct sparql` |

Note: `prediction_format` is part of the evaluation CLI, not the training config. The training config specifies the learned target field, but not the later evaluation prediction format.

### Hyperparameters and output directories

| Run name | Epochs | Learning rate | Train batch | Eval batch | Grad accum. | Max input length | Max target/output length | Output base dir | Output run name |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| `t5_base_pgmr_mini_full_finetune_15ep` | 15 | `5e-05` | 4 | 4 | 2 | `max_source_length=768` | 512 | `code/models/google-t5_t5-base/finetuned` | `pgmr_mini_full_finetune_15ep` |
| `qwen25_coder_7b_pgmr_qlora_3ep` | 3 | `0.0002` | 1 | 1 | 8 | `max_prompt_length=2048` | 512 | `code/models/Qwen25_Coder_7B_Instruct/finetuned` | `pgmr_qlora_3ep` |
| `qwen25_coder_7b_empire_compass_qlora_3ep` | 3 | `0.0001` | 1 | 1 | 8 | `max_prompt_length=4096` | 1024 | `code/models/Qwen25_Coder_7B_Instruct/finetuned` | `empire_compass_qlora_3ep` |
| `mistral_7b_pgmr_qlora_3ep` | 3 | `0.0002` | 1 | 1 | 8 | `max_prompt_length=2048` | 512 | `code/models/Mistral_7B_Instruct/finetuned` | `pgmr_qlora_3ep` |
| `mistral_7b_empire_compass_qlora_3ep` | 3 | `0.0001` | 1 | 1 | 8 | `max_prompt_length=4096` | 1024 | `code/models/Mistral_7B_Instruct/finetuned` | `empire_compass_qlora_3ep` |

### Other training settings

| Run type | Settings |
| --- | --- |
| T5 full fine-tuning | `logging_steps=25`, `evaluation_strategy=epoch`, `save_strategy=epoch`, `save_total_limit=2`, `fp16=false`, `bf16=true`, `seed=42`. |
| Qwen/Mistral QLoRA | `logging_steps=10`, `evaluation_strategy=epoch`, `save_strategy=epoch`, `save_total_limit=2`, `fp16=true`, `bf16=false`, `gradient_checkpointing=true`, `use_qlora=true`, `load_in_4bit=true`, `optim=paged_adamw_8bit`, `lr_scheduler_type=cosine`, `warmup_ratio=0.03`, `seed=42`. |

### LoRA and quantization parameters

The four QLoRA runs use the same LoRA and quantization config:

| Parameter | Value |
| --- | --- |
| `r` | 16 |
| `alpha` | 32 |
| `dropout` | 0.05 |
| `target_modules` | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| `load_in_4bit` | `true` |
| `bnb_4bit_quant_type` | `nf4` |
| `bnb_4bit_use_double_quant` | `true` |
| `bnb_4bit_compute_dtype` | `float16` |

T5 does not define LoRA or quantization parameters in the config.

### Dataset filters and paraphrase use

| Run name | Dataset filter | Paraphrase-augmented data? |
| --- | --- | --- |
| `t5_base_pgmr_mini_full_finetune_15ep` | `pgmr_status == ok` | Yes, `train_with_paraphrases.json` |
| `qwen25_coder_7b_pgmr_qlora_3ep` | `pgmr_status == ok` | Yes, `train_with_paraphrases.json` |
| `qwen25_coder_7b_empire_compass_qlora_3ep` | No filters, `{}` | Yes, `train_with_paraphrases.json` |
| `mistral_7b_pgmr_qlora_3ep` | `pgmr_status == ok` | Yes, `train_with_paraphrases.json` |
| `mistral_7b_empire_compass_qlora_3ep` | No filters, `{}` | Yes, `train_with_paraphrases.json` |

## 3. Model Configuration Overview

Source: `code/config/model_config.json`

### Original base models

| Model key | Provider | `model_id` | Interface | Variant | Model path | Generation settings |
| --- | --- | --- | --- | --- | --- | --- |
| `t5_base` | `huggingface` | `google-t5/t5-base` | `seq2seq` | `original` | `code/models/t5_base/original` | `max_new_tokens=512`, `temperature=0.0`, `do_sample=false` |
| `qwen25_coder_7b_instruct` | `huggingface` | `Qwen/Qwen2.5-Coder-7B-Instruct` | `causal_lm` | `original` | `code/models/Qwen25_Coder_7B_Instruct/original` | `max_new_tokens=512`, `temperature=0.0`, `do_sample=false` |
| `mistral_7b_instruct` | `huggingface` | `mistralai/Mistral-7B-Instruct-v0.3` | `causal_lm` | `original` | `code/models/Mistral_7B_Instruct/original` | `max_new_tokens=512`, `temperature=0.0`, `do_sample=false` |

### Fine-tuned or adapter-backed model entries

| Model key | Provider | `model_id` | Interface | Variant in config | Fine-tuned path or adapter path | Generation settings |
| --- | --- | --- | --- | --- | --- | --- |
| `t5_base_pgmr_mini_full_finetune` | `huggingface` | `google-t5/t5-base` | `seq2seq` | `finetuned` | `paths.finetuned_path=code/models/t5_base/finetuned/pgmr_mini_full_finetune_15ep/20260504_233633/final_model` | `max_new_tokens=512`, `temperature=0.0`, `do_sample=false` |
| `qwen25_coder_7b_pgmr_qlora` | `huggingface` | `Qwen/Qwen2.5-Coder-7B-Instruct` | `causal_lm` | `original` | `adapter_path=code/models/Qwen25_Coder_7B_Instruct/finetuned/pgmr_qlora_3ep/20260505_101002/checkpoint-302` | `max_new_tokens=512`, `temperature=0.0`, `do_sample=false` |
| `qwen25_coder_7b_empire_compass_qlora` | `huggingface` | `Qwen/Qwen2.5-Coder-7B-Instruct` | `causal_lm` | `original` | `adapter_path=code/models/Qwen25_Coder_7B_Instruct/finetuned/empire_compass_qlora_3ep/20260505_121226/checkpoint-302` | `max_new_tokens=768`, `temperature=0.0`, `do_sample=false` |
| `mistral_7b_pgmr_qlora` | `huggingface` | `mistralai/Mistral-7B-Instruct-v0.3` | `causal_lm` | `original` | `adapter_path=code/models/Mistral_7B_Instruct/finetuned/pgmr_qlora_3ep/20260505_105209/checkpoint-302` | `max_new_tokens=512`, `temperature=0.0`, `do_sample=false` |
| `mistral_7b_empire_compass_qlora` | `huggingface` | `mistralai/Mistral-7B-Instruct-v0.3` | `causal_lm` | `original` | `adapter_path=code/models/Mistral_7B_Instruct/finetuned/empire_compass_qlora_3ep/20260505_140058/checkpoint-302` | `max_new_tokens=768`, `temperature=0.0`, `do_sample=false` |

### Relationship between original and fine-tuned variants

Facts:

- T5 is represented as a separate `variant=finetuned` model entry with a full `finetuned_path`.
- Qwen2.5-Coder and Mistral fine-tuned entries keep `variant=original` and point to the original base model path plus a top-level `adapter_path`.
- Inference code in `code/src/core/model_loader.py` loads the base causal LM and attaches the PEFT adapter if `adapter_path` is configured.
- For causal LM adapter entries, the config points to `checkpoint-302`, although the local training directories also contain `checkpoint-453` and `final_adapter`.

Potential point to verify later:

- The current training config output base dir for T5 is `code/models/google-t5_t5-base/finetuned`, while the model config points to an existing fine-tuned path under `code/models/t5_base/finetuned/...`. This may be a historical naming change or an inconsistency worth checking before final thesis wording.

## 4. Training Code Path

### CLI command

Training is started through:

```bash
PYTHONPATH=code python code/src/main.py train --run <run-key>
```

Optional CLI arguments:

```bash
PYTHONPATH=code python code/src/main.py train \
  --run <run-key> \
  --train-config code/config/train_config.json \
  --max-train-samples 10 \
  --max-eval-samples 10 \
  --override-epochs 1 \
  --dry-run
```

`--dry-run` prepares and prints examples without loading a model or starting training.

### Config loading and dispatch

Facts:

1. `code/src/main.py` parses the `train` subcommand and calls `run_train_task`.
2. `run_train_task` calls `src.train.runner.run_training`.
3. `run_training` loads `train_config.json` through `src.train.config.load_train_config`.
4. `load_train_config` validates the config before returning it.
5. `src.train.runner` selects the trainer:
   - `method == "full_finetune"` uses `run_seq2seq_training`.
   - `method in {"lora", "qlora", "causal_lm_lora", "causal_lm_qlora"}` uses `run_causal_lm_lora_training`.

### Dataset loading and example construction

Facts:

- Datasets are JSON lists loaded from `dataset.train_path` or `dataset.validation_path`.
- Filters are exact string comparisons. For example, `{"pgmr_status": "ok"}` keeps only entries whose `pgmr_status` string is `ok`.
- The target is selected using `dataset.target_field`.
- Entries with an empty selected target are skipped.
- Each training example has:
  - `id`
  - `family`
  - `input_text`
  - `target_text`

### Prompt construction

Facts:

- `prompt.mode` controls how `input_text` is built.
- `pgmr_mini` loads `code/prompts/pgmr_mini/<family prompt>` and formats `{family}` and `{question}`.
- `pgmr` loads `code/prompts/pgmr/<family prompt>` and formats `{family}` and `{question}`.
- `empire_compass` resolves the family-specific full Empire Compass prompt, generates it through the TypeScript prompt generator if missing, and replaces `[Research Question]`.
- `empire_compass_mini` loads the mini prompt and replaces `{question}`.
- `zero_shot` and `few_shot` currently fall back to the plain question through the query prompt builder.

### Target fields

Facts:

- Direct-SPARQL runs use `gold_sparql`.
- PGMR-lite runs use `gold_pgmr_sparql`.
- The train config schema allows only these two target fields.

### T5 full fine-tuning path

Facts:

- The T5 run uses the seq2seq trainer.
- The model entry must have `provider=huggingface` and `interface=seq2seq`.
- The trainer loads `AutoTokenizer` and `AutoModelForSeq2SeqLM`.
- Inputs are tokenized with `max_source_length`.
- Targets are tokenized with `max_target_length`.
- Training uses `DataCollatorForSeq2Seq` and `Seq2SeqTrainer`.
- `predict_with_generate=True` is set in training arguments.
- The final model and tokenizer are saved to `final_model`.
- The run writes:
  - `run_metadata.json`
  - Hugging Face trainer checkpoint/state outputs
  - train metrics through `trainer.save_metrics("train", ...)`
  - eval metrics through `trainer.save_metrics("eval", ...)`
  - `final_metrics.json`

### Causal LM QLoRA path

Facts:

- Qwen2.5-Coder and Mistral runs use the causal LM LoRA trainer.
- The model entry must have `provider=huggingface` and `interface=causal_lm`.
- The trainer resolves a local base model directory if available, otherwise falls back to the Hugging Face `model_id`.
- The tokenizer is loaded with `AutoTokenizer`; if no pad token exists, the EOS token is used as the pad token.
- Prompts are wrapped using the tokenizer chat template when available. Otherwise, they use a simple `User: ... Assistant:` format.
- Prompt tokens are masked from the loss with label value `-100`; only target query tokens contribute to loss.
- For QLoRA:
  - `BitsAndBytesConfig` is built for 4-bit loading.
  - `prepare_model_for_kbit_training` is applied when QLoRA or 4-bit loading is active.
  - `LoraConfig` is created with the configured rank, alpha, dropout, and target modules.
  - `get_peft_model` attaches trainable LoRA adapters to the base model.
- Training uses the standard Hugging Face `Trainer`.
- The final adapter and tokenizer are saved to `final_adapter`.
- The run writes:
  - `run_metadata.json`
  - checkpoints
  - train/eval metrics
  - `final_metrics.json`

### Output locations

Facts:

- Output directories are timestamped as:

```text
<output.base_dir>/<output.run_name>/<UTC timestamp>/
```

- T5 saves a full model under:

```text
<run output dir>/final_model
```

- Qwen/Mistral QLoRA saves an adapter under:

```text
<run output dir>/final_adapter
```

## 5. Dataset Usage for Fine-Tuning

### Dataset files

Current local dataset sizes:

| Dataset file | Entries | Non-empty `gold_sparql` | Non-empty `gold_pgmr_sparql` | `pgmr_status == ok` |
| --- | ---: | ---: | ---: | ---: |
| `code/data/dataset/final/train.json` | 602 | 602 | 0 | 0 |
| `code/data/dataset/final/train_with_paraphrases.json` | 1204 | 1204 | 0 | 0 |
| `code/data/dataset/final/validation.json` | 50 | 50 | 0 | 0 |
| `code/data/dataset/final/benchmark.json` | 51 | 51 | 0 | 0 |
| `code/data/dataset/pgmr/final/train.json` | 602 | 602 | 602 | 602 |
| `code/data/dataset/pgmr/final/train_with_paraphrases.json` | 1204 | 1204 | 1204 | 1204 |
| `code/data/dataset/pgmr/final/validation.json` | 50 | 50 | 50 | 50 |
| `code/data/dataset/pgmr/final/benchmark.json` | 51 | 51 | 51 | 51 |

Current local family distribution:

| Dataset file | Family distribution |
| --- | --- |
| `code/data/dataset/final/train.json` | `empirical_research_practice: 325`, `nlp4re: 277` |
| `code/data/dataset/final/train_with_paraphrases.json` | `empirical_research_practice: 650`, `nlp4re: 554` |
| `code/data/dataset/final/validation.json` | `empirical_research_practice: 26`, `nlp4re: 24` |
| `code/data/dataset/final/benchmark.json` | `empirical_research_practice: 24`, `nlp4re: 27` |

### Original vs paraphrase-augmented training data

Facts:

- `train.json` contains 602 training entries.
- `train_with_paraphrases.json` contains 1204 training entries.
- In the current local files, `train_with_paraphrases.json` contains 602 original items and 602 paraphrase-derived items identified by IDs containing `__para_`.
- The tool `code/tools/dataset/create_train_with_paraphrases.py` keeps the original gold query unchanged for paraphrase items and changes the natural-language `question`.

### Direct-SPARQL fine-tuning

Facts:

- Direct-SPARQL fine-tuning uses files under `code/data/dataset/final/`.
- The target field is `gold_sparql`.
- The configured direct-SPARQL runs use the paraphrase-augmented train file and the original validation file:
  - `code/data/dataset/final/train_with_paraphrases.json`
  - `code/data/dataset/final/validation.json`
- Current direct-SPARQL fine-tuning runs:
  - `qwen25_coder_7b_empire_compass_qlora_3ep`
  - `mistral_7b_empire_compass_qlora_3ep`

### PGMR-lite fine-tuning

Facts:

- PGMR-lite fine-tuning uses files under `code/data/dataset/pgmr/final/`.
- The target field is `gold_pgmr_sparql`.
- The configured PGMR-lite runs use:
  - `code/data/dataset/pgmr/final/train_with_paraphrases.json`
  - `code/data/dataset/pgmr/final/validation.json`
- PGMR-lite runs filter examples with `pgmr_status == ok`.
- In the current local PGMR files inspected here, all entries in train, train-with-paraphrases, validation, and benchmark have `pgmr_status == ok`.
- Current PGMR-lite fine-tuning runs:
  - `t5_base_pgmr_mini_full_finetune_15ep`
  - `qwen25_coder_7b_pgmr_qlora_3ep`
  - `mistral_7b_pgmr_qlora_3ep`

### Why PGMR-lite can make fine-tuning easier

Interpretation:

- PGMR-lite replaces opaque ORKG identifiers with semantic placeholders. This can reduce the burden on the model to memorize exact ORKG predicate/class IDs.
- The model can focus more on query structure, placeholder placement, and projection variables.
- A later restore step maps placeholders back to real ORKG identifiers through `code/data/orkg_memory/templates/`.
- This separation can make structural query generation easier, but it does not remove all difficulty. The model still needs to produce valid SPARQL shape, correct variable bindings, correct projections, and placeholders that exist in memory.

## 6. Training Runs and Slurm Evidence

Source logs:

- `code/outputs/slurm_logs/training/train_t5_base_pgmr_mini_full_finetune_15ep_24203.out`
- `code/outputs/slurm_logs/training/train_t5_base_pgmr_mini_full_finetune_15ep_24203.err`
- `code/outputs/slurm_logs/training/train_qwen_pgmr_QLora_3ep_24213.out`
- `code/outputs/slurm_logs/training/train_qwen_pgmr_QLora_3ep_24213.err`
- `code/outputs/slurm_logs/training/train_qwen_empire_compass_QLora_3ep_24226.out`
- `code/outputs/slurm_logs/training/train_qwen_empire_compass_QLora_3ep_24226.err`
- `code/outputs/slurm_logs/training/train_mistral_pgmr_QLora_3ep_24214.out`
- `code/outputs/slurm_logs/training/train_mistral_pgmr_QLora_3ep_24214.err`
- `code/outputs/slurm_logs/training/train_mistral_empire_compass_QLora_3ep_24235.out`
- `code/outputs/slurm_logs/training/train_mistral_empire_compass_QLora_3ep_24235.err`

### Training hardware and runtime summary

Facts from the Slurm `.out` logs:

| Run | Log job name / run label visible in log | Node | GPU | GPU memory visible in log | Start time | End time | Wall-clock duration from log timestamps | Trainer `train_runtime` | Completed successfully? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `t5_base_pgmr_mini_full_finetune_15ep` | `t5_base_pgmr_mini_full_15ep_src768` | `gpu-a3090-01` | NVIDIA GeForce RTX 3090 | 23.56 GB | Tue May  5 01:36:03 CEST 2026 | Tue May  5 02:06:58 CEST 2026 | 30 min 55 sec | 1790 sec = 29 min 50 sec | Yes |
| `qwen25_coder_7b_pgmr_qlora_3ep` | `qwen25_coder_7b_pgmr_qlora_3ep` | `gpu-h100-02` | NVIDIA H100 NVL | 93.09 GB | Tue May  5 12:09:20 PM CEST 2026 | Tue May  5 12:37:32 PM CEST 2026 | 28 min 12 sec | 1480 sec = 24 min 40 sec | Yes |
| `qwen25_coder_7b_empire_compass_qlora_3ep` | `qwen25_coder_7b_empire_compass_qlora_3ep` | `gpu-h100-02` | NVIDIA H100 NVL | 93.09 GB | Tue May  5 02:11:46 PM CEST 2026 | Tue May  5 03:11:56 PM CEST 2026 | 1 h 00 min 10 sec | 3515 sec = 58 min 35 sec | Yes |
| `mistral_7b_pgmr_qlora_3ep` | `mistral_7b_pgmr_qlora_3ep` | `gpu-h100-02` | NVIDIA H100 NVL | 93.09 GB | Tue May  5 12:51:34 PM CEST 2026 | Tue May  5 01:22:15 PM CEST 2026 | 30 min 41 sec | 1684 sec = 28 min 04 sec | Yes |
| `mistral_7b_empire_compass_qlora_3ep` | `mistral_7b_empire_compass_qlora_3ep` | `gpu-h100-03` | NVIDIA H100 NVL | 93.09 GB | Tue May  5 04:00:20 PM CEST 2026 | Tue May  5 05:07:24 PM CEST 2026 | 1 h 07 min 04 sec | 3818 sec = 1 h 03 min 38 sec | Yes |

Additional hardware/runtime facts visible in logs:

- All runs used `CUDA_VISIBLE_DEVICES=0`.
- All logs show `torch: 2.11.0+cu130` and `cuda available: True`.
- All logs show NVIDIA driver `580.105.08` and CUDA version `13.0`.
- The T5 run used an RTX 3090 node; all QLoRA runs used H100 NVL nodes.
- The log wall-clock duration is slightly longer than `train_runtime` because it includes setup, model/tokenizer loading, saving, and shell/script overhead.

### Training loss and evaluation loss evidence

Facts from the Slurm `.out` logs:

| Run | Epochs completed | Train examples | Eval examples | Train loss from final trainer metrics | Evaluation loss per epoch |
| --- | ---: | ---: | ---: | ---: | --- |
| `t5_base_pgmr_mini_full_finetune_15ep` | 15 | 1204 | 50 | 0.4148 | epoch 1: 0.3313; 2: 0.2255; 3: 0.1842; 4: 0.1537; 5: 0.1436; 6: 0.1311; 7: 0.1234; 8: 0.1194; 9: 0.1151; 10: 0.1109; 11: 0.1090; 12: 0.1064; 13: 0.1053; 14: 0.1049; 15: 0.1042 |
| `qwen25_coder_7b_pgmr_qlora_3ep` | 3 | 1204 | 50 | 0.05058 | epoch 1: 0.05426; 2: 0.04841; 3: 0.05636 |
| `qwen25_coder_7b_empire_compass_qlora_3ep` | 3 | 1204 | 50 | 0.04416 | epoch 1: 0.04115; 2: 0.03922; 3: 0.04253 |
| `mistral_7b_pgmr_qlora_3ep` | 3 | 1204 | 50 | 0.03996 | epoch 1: 0.05266; 2: 0.03809; 3: 0.04310 |
| `mistral_7b_empire_compass_qlora_3ep` | 3 | 1204 | 50 | 0.03191 | epoch 1: 0.04050; 2: 0.04145; 3: 0.04681 |

### Trainable parameter evidence for QLoRA runs

Facts from the Slurm `.out` logs:

| Run | Trainable parameters | Total parameters | Trainable percentage |
| --- | ---: | ---: | ---: |
| `qwen25_coder_7b_pgmr_qlora_3ep` | 40,370,176 | 7,655,986,688 | 0.5273% |
| `qwen25_coder_7b_empire_compass_qlora_3ep` | 40,370,176 | 7,655,986,688 | 0.5273% |
| `mistral_7b_pgmr_qlora_3ep` | 41,943,040 | 7,289,966,592 | 0.5754% |
| `mistral_7b_empire_compass_qlora_3ep` | 41,943,040 | 7,289,966,592 | 0.5754% |

### Final output paths visible in logs

| Run | Final output path visible in log |
| --- | --- |
| `t5_base_pgmr_mini_full_finetune_15ep` | `code/models/google-t5_t5-base/finetuned/pgmr_mini_full_finetune_15ep/20260504_233633/final_model` |
| `qwen25_coder_7b_pgmr_qlora_3ep` | `code/models/Qwen_Qwen2.5_Coder_7B_Instruct/finetuned/pgmr_qlora_3ep/20260505_101002/final_adapter` |
| `qwen25_coder_7b_empire_compass_qlora_3ep` | `code/models/Qwen25_Coder_7B_Instruct/finetuned/empire_compass_qlora_3ep/20260505_121226/final_adapter` |
| `mistral_7b_pgmr_qlora_3ep` | `code/models/Mistral_7B_Instruct/finetuned/pgmr_qlora_3ep/20260505_105209/final_adapter` |
| `mistral_7b_empire_compass_qlora_3ep` | `code/models/Mistral_7B_Instruct/finetuned/empire_compass_qlora_3ep/20260505_140058/final_adapter` |

Note: The Qwen PGMR log reports `code/models/Qwen_Qwen2.5_Coder_7B_Instruct/...`, while the current local model config uses `code/models/Qwen25_Coder_7B_Instruct/...`. This path naming mismatch should be verified before final thesis reporting.

### Errors and warnings visible in `.err` logs

No fatal Python traceback, CUDA out-of-memory message, or failed-run marker was found in the scanned `.err` logs. The `.err` files mainly contain progress bars and non-fatal warnings:

- Hugging Face Hub warning: unauthenticated requests; set `HF_TOKEN` for higher rate limits.
- T5 warning: slow tensor creation in the Transformers data collator.
- QLoRA warnings:
  - `torch_dtype` is deprecated; use `dtype` instead.
  - bitsandbytes/PyTorch future warning about `_check_is_size`.
  - `warmup_ratio` is deprecated and will be removed in a future version; use `warmup_steps` instead.

### Known from Slurm scripts, not from logs

Facts from `code/scripts/slurm/training/`:

| Script | Slurm job name | Resources in script | Run key |
| --- | --- | --- | --- |
| `train_t5_base_pgmr_mini_full_15ep.sbatch` | `t5_base_pgmr_mini_full_finetune_15ep` | `gpu:1`, `cpus-per-task=8`, `mem=80G` | `t5_base_pgmr_mini_full_finetune_15ep` |
| `train_qwen25_coder_7b_pgmr_qlora_3ep.sbatch` | `qwen_pgmr_QLora_3ep` | `gpu:1`, `cpus-per-task=8`, `mem=80G` | `qwen25_coder_7b_pgmr_qlora_3ep` |
| `train_qwen25_coder_7b_empire_compass_qlora_3ep.sbatch` | `qwen_empire_compass_QLora_3ep` | `gpu:1`, `cpus-per-task=8`, `mem=80G` | `qwen25_coder_7b_empire_compass_qlora_3ep` |
| `train_mistral_7b_pgmr_qlora_3ep.sbatch` | `mistral_pgmr_QLora_3ep` | `gpu:1`, `cpus-per-task=8`, `mem=80G` | `mistral_7b_pgmr_qlora_3ep` |
| `train_mistral_7b_empire_compass_qlora_3ep.sbatch` | `mistral_empire_compass_QLora_3ep` | `gpu:1`, `cpus-per-task=8`, `mem=80G` | `mistral_7b_empire_compass_qlora_3ep` |

### Existing local training artifacts

Facts from `code/models/`:

| Run | Existing timestamped artifact directory | Final artifact type |
| --- | --- | --- |
| T5 PGMR-mini full fine-tuning | `code/models/t5_base/finetuned/pgmr_mini_full_finetune_15ep/20260504_233633/` | `final_model` |
| Qwen PGMR QLoRA | `code/models/Qwen25_Coder_7B_Instruct/finetuned/pgmr_qlora_3ep/20260505_101002/` | `final_adapter` plus checkpoints |
| Qwen Empire Compass QLoRA | `code/models/Qwen25_Coder_7B_Instruct/finetuned/empire_compass_qlora_3ep/20260505_121226/` | `final_adapter` plus checkpoints |
| Mistral PGMR QLoRA | `code/models/Mistral_7B_Instruct/finetuned/pgmr_qlora_3ep/20260505_105209/` | `final_adapter` plus checkpoints |
| Mistral Empire Compass QLoRA | `code/models/Mistral_7B_Instruct/finetuned/empire_compass_qlora_3ep/20260505_140058/` | `final_adapter` plus checkpoints |

Existing `final_metrics.json` files show final train/eval metrics. The per-epoch evaluation losses above come from the Slurm `.out` logs.

## 7. Methodological Interpretation

Interpretation:

- T5-base is fully fine-tuned because it is small enough to train as a complete seq2seq model and naturally fits a text-to-text setup.
- Qwen2.5-Coder-7B-Instruct and Mistral-7B-Instruct are adapted with QLoRA because full fine-tuning of 7B parameter models is less practical under typical bachelor-thesis hardware constraints.
- Fine-tuning is used here to teach recurring ORKG template structures, output conventions, prompt-specific response patterns, and query syntax. It is not primarily intended to add general world knowledge.
- Direct-SPARQL fine-tuning tests whether models can learn both SPARQL structure and ORKG identifier usage directly in the output.
- PGMR-lite fine-tuning tests whether models perform better when identifier grounding is separated from structural query generation.
- The direct-SPARQL setup has a harder grounding burden because the model must output executable ORKG IDs/classes/predicates.
- The PGMR-lite setup shifts part of the grounding burden to the restore step, but still requires the model to produce syntactically coherent SPARQL and valid placeholders.

## 8. Limitations and Points to Mention Later

These points belong in Discussion or Limitations, not necessarily in the main method description.

- Dataset size is limited compared with large-scale text-to-SQL or code generation fine-tuning datasets.
- The dataset is template-specific and covers the `nlp4re` and `empirical_research_practice` families, so generalization to other ORKG templates is not guaranteed.
- The models may overfit to recurring query patterns, especially because ORKG template queries often share structural regularities.
- Full fine-tuning for T5 and QLoRA adapter tuning for 7B models are practically motivated but not identical training regimes.
- Performance may depend strongly on prompt mode, target representation, and generation settings.
- Direct-SPARQL outputs depend on the model reproducing ORKG identifiers correctly.
- PGMR-lite depends on memory coverage in `code/data/orkg_memory/templates/`; missing placeholders or incomplete mappings can limit restoration.
- PGMR-lite restoration may fail even when the model output is structurally plausible if placeholders are absent, malformed, or not mappable.
- Slurm and hardware constraints influenced practical choices such as QLoRA, batch size 1 for 7B models, gradient accumulation, 4-bit loading, and gradient checkpointing.
- The current model config points Qwen/Mistral adapter-backed models to `checkpoint-302`, while local training directories also contain later checkpoints and `final_adapter`. The intended evaluation checkpoint should be verified before final reporting.
- Current train config output paths and existing artifact paths should be cross-checked before final thesis wording, especially for T5 path naming.

## 9. Commands to Reproduce or Inspect the Setup

Run commands from the repository root with `PYTHONPATH=code` where Python imports are needed.

### Inspect training runs

```bash
jq '.runs | keys' code/config/train_config.json
```

```bash
jq '.runs.t5_base_pgmr_mini_full_finetune_15ep' code/config/train_config.json
```

```bash
jq -r '.runs | to_entries[] | [.key, .value.model, .value.method, .value.task, .value.dataset.train_path, .value.dataset.target_field, .value.prompt.mode] | @tsv' code/config/train_config.json
```

### Inspect model registry

```bash
jq '.models | keys' code/config/model_config.json
```

```bash
jq -r '.models | to_entries[] | [.key, .value.provider, .value.model_id, .value.interface, .value.variant, (.value.adapter_path // .value.paths.finetuned_path // .value.paths.model_path // "[NO MODEL PATH]")] | @tsv' code/config/model_config.json
```

### Preview training examples without training

```bash
PYTHONPATH=code python code/src/main.py train \
  --run qwen25_coder_7b_pgmr_qlora_3ep \
  --max-train-samples 2 \
  --max-eval-samples 2 \
  --dry-run
```

```bash
PYTHONPATH=code python code/src/train/dataset.py \
  --run t5_base_pgmr_mini_full_finetune_15ep \
  --split train \
  --limit 3
```

### Dataset sizes and target coverage

```bash
jq -r '[input_filename, length, (map(select((.gold_sparql // "") != "")) | length), (map(select((.gold_pgmr_sparql // "") != "")) | length), (map(select((.pgmr_status // "") == "ok")) | length)] | @tsv' \
  code/data/dataset/final/train.json \
  code/data/dataset/final/train_with_paraphrases.json \
  code/data/dataset/final/validation.json \
  code/data/dataset/final/benchmark.json \
  code/data/dataset/pgmr/final/train.json \
  code/data/dataset/pgmr/final/train_with_paraphrases.json \
  code/data/dataset/pgmr/final/validation.json \
  code/data/dataset/pgmr/final/benchmark.json
```

### Paraphrase-augmented data

```bash
jq -r '[input_filename, length, (map(select((.id|tostring|contains("__para_")))) | length), (map(select((.id|tostring|contains("__para_")|not))) | length)] | @tsv' \
  code/data/dataset/final/train.json \
  code/data/dataset/final/train_with_paraphrases.json \
  code/data/dataset/pgmr/final/train.json \
  code/data/dataset/pgmr/final/train_with_paraphrases.json
```

### PGMR status distribution

```bash
jq -r 'group_by(.pgmr_status // "[missing]") | map([.[0].pgmr_status // "[missing]", length] | @tsv)[]' \
  code/data/dataset/pgmr/final/train_with_paraphrases.json
```

```bash
jq -r '.[0] | keys_unsorted | @tsv' code/data/dataset/pgmr/final/train.json
```

### Output directories and training artifacts

```bash
find code/models -maxdepth 5 -type d
```

```bash
find code/models/Qwen25_Coder_7B_Instruct/finetuned code/models/Mistral_7B_Instruct/finetuned code/models/t5_base/finetuned \
  -maxdepth 4 -name run_metadata.json -o -name final_metrics.json
```

```bash
jq -r '[.run_name, .task, .model_key, .model_id, .method, .started_at_utc, .train_examples, .eval_examples, .output_dir, (.final_model_dir // .final_adapter_dir)] | @tsv' \
  code/models/Qwen25_Coder_7B_Instruct/finetuned/empire_compass_qlora_3ep/20260505_121226/run_metadata.json
```

### Fine-tuned model evaluation runs

```bash
find code/outputs/evaluation_runs \
  -maxdepth 3 \
  -type d
```

```bash
find code/outputs/evaluation_runs/t5_base_pgmr_mini_full_finetune \
     code/outputs/evaluation_runs/qwen25_coder_7b_pgmr_qlora \
     code/outputs/evaluation_runs/qwen25_coder_7b_empire_compass_qlora \
     code/outputs/evaluation_runs/mistral_7b_pgmr_qlora \
     code/outputs/evaluation_runs/mistral_7b_empire_compass_qlora \
  -maxdepth 2 \
  -type f \
  -name benchmark_summary.json
```

```bash
jq -r '[.run_metadata.model_name, .run_metadata.prompt_mode, .run_metadata.prediction_format, .run_metadata.dataset_path, .run_metadata.completed_items] | @tsv' \
  code/outputs/evaluation_runs/mistral_7b_empire_compass_qlora/empire_compass__benchmark__20260507_203024/benchmark_summary.json
```

### Slurm logs to fill Section 6

```bash
find code/outputs/slurm_logs/training -maxdepth 1 -type f
```

```bash
sed -n '1,220p' code/outputs/slurm_logs/training/<log-file>.out
```

```bash
sed -n '1,220p' code/outputs/slurm_logs/training/<log-file>.err
```

### Slurm training scripts

```bash
rg -n "#SBATCH --job-name|#SBATCH --gres|#SBATCH --cpus-per-task|#SBATCH --mem|--run " code/scripts/slurm/training
```
