# Source Packages

`code/src/` contains the reusable Python packages behind the main CLI and workflow scripts. If a behavior is shared by more than one tool, it should normally live here instead of inside a one-off script.

Run package-backed commands from the repository root with:

```bash
PYTHONPATH=code python code/src/main.py <mode> [args]
```

## Main CLI

`main.py` exposes four modes:

| Mode | Purpose | Typical output |
| --- | --- | --- |
| `query` | Build a prompt for one question and generate one model response. | Printed raw response, optional PGMR postprocessing/restoration. |
| `evaluate` | Run a model over a dataset split and compute execution/quality metrics. | `benchmark_raw.json` and `benchmark_summary.json` under `code/outputs/evaluation_runs/`. |
| `train` | Run a configured training job from `code/config/train_config.json`. | Fine-tuned model or adapter directory under `code/models/`. |
| `ace-llm` | Convert evaluation errors into ACE traces and candidate playbook rules. | ACE trace and delta files in an evaluation run directory. |

## Package Map

| Package | What it does | Used by |
| --- | --- | --- |
| `ace/` | ACE playbook loading, rendering, routing, curation, trace building, offline reflection, and LLM reflection helpers. | `main.py ace-llm`, ACE tools, prompt builder. |
| `core/` | Model/provider integration: local Hugging Face model loading, optional PEFT adapters, OpenAI client access, and model downloads. | Query, evaluation, training, OpenAI tools. |
| `evaluate/` | Dataset loading, model evaluation loop, SPARQL extraction, execution payloads, metric calculation, summaries, and cost accounting. | `main.py evaluate`, reporting tools, tests. |
| `pgmr/` | PGMR-lite transformation, postprocessing, memory loading, and restoration to executable ORKG SPARQL. | PGMR tools, query CLI, evaluation pipeline. |
| `query/` | Prompt selection/building, ACE context insertion, inference session preparation, and model response generation. | `main.py query`, `main.py evaluate`, training dataset construction. |
| `sparql/` | SPARQL prefix handling, query normalization, query-form detection, and endpoint execution. | Dataset validation, evaluation, PGMR restore. |
| `train/` | Dataset-to-prompt conversion and training runners for T5 full fine-tuning and causal-LM LoRA/QLoRA. | `main.py train`. |
| `utils/` | Shared JSON/path configuration loading. | Most packages and tools. |

## Prompt Modes

The query and evaluation pipelines can build prompts in several modes:

| Mode | Meaning |
| --- | --- |
| `empire_compass` | Full Empire Compass prompt generated from TypeScript templates. |
| `empire_compass_mini` | Smaller static prompt template. |
| `pgmr` | Full PGMR prompt for placeholder-oriented query generation. |
| `pgmr_mini` | Smaller PGMR prompt used for lightweight/fine-tuned runs. |
| `zero_shot` / `few_shot` | Pass-through/simple prompt modes handled as plain model prompting. |
| `pgmr_lite_meta` | Evaluation-only prompt that includes structured metadata fields. |

Modes with family-specific templates require `--family nlp4re` or `--family empirical_research_practice`.

## ACE Context

ACE is optional. It is enabled by adding playbook arguments to `query` or `evaluate`:

```bash
--ace-playbook-dir code/data/ace_playbooks \
--ace-mode pgmr_lite \
--ace-max-bullets 5
```

The prompt builder resolves model/family/mode-specific playbooks and prepends a compact rule block to the normal prompt. With `--ace-max-bullets 0`, ACE is disabled.

## Dependency Notes

Several modules import heavy optional dependencies at import time:

- `torch`, `transformers`, and optionally `peft` for local model inference/training
- `openai` and `python-dotenv` for OpenAI-backed generation
- `requests` for SPARQL execution

If `python code/src/main.py --help` fails before printing help, a dependency such as `torch` is probably missing.
