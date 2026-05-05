# Code Directory

This directory is the implementation workspace for the ORKG text-to-SPARQL project. It contains reusable Python packages, command-line tools, data assets, prompts, configuration, tests, and generated experiment outputs.

## Directory Structure

| Path | Purpose |
| --- | --- |
| `src/` | Python packages used by the main CLI and tools. This is where reusable logic lives. |
| `tools/` | Script-style entry points for one workflow step at a time. These are the best place to start when preparing data or inspecting outputs. |
| `data/` | Datasets, ORKG memory templates, ACE playbooks, working files, final exports, reports, and archives. |
| `prompts/` | Prompt templates and generated prompt artifacts for query generation and dataset expansion. |
| `config/` | JSON configuration for paths, models, training runs, and schemas. |
| `outputs/` | Evaluation runs, benchmark reports, model outputs, ACE traces, and archived experiment results. |
| `tests/` | Unit tests for evaluation metrics, ACE behavior, and query/memory utilities. |

## Running Code

Most scripts import packages as `src.*`, so run from the repository root with:

```bash
PYTHONPATH=code python code/src/main.py --help
```

For individual tools:

```bash
PYTHONPATH=code python code/tools/<area>/<script>.py --help
```

If a script uses local Hugging Face models, the model files must already exist under the path configured in `config/model_config.json`. OpenAI-backed scripts need `OPENAI_API_KEY`, either exported in the shell or stored in a repo-root `.env` file.

## Entry Points

Use `src/main.py` for the main model workflows:

- `query`: one natural-language question to one model output
- `evaluate`: dataset evaluation with query extraction, execution, and metrics
- `train`: configured fine-tuning runs
- `ace-llm`: ACE trace and rule-reflection workflow

Use `tools/` for data and reporting workflows:

- `generation/`: assemble and run dataset expansion prompts
- `review/`: inspect and select generated candidates
- `evaluate/`: run post-hoc analysis over existing evaluation outputs
- `dataset/`: normalize, enrich, deduplicate, validate, and split datasets
- `pgmr/`: transform to PGMR-lite, evaluate PGMR-lite predictions, restore predictions
- `ace/`: build splits, inspect errors, curate playbooks
- `reporting/`: export dataset quality reports

## Development Notes

- Keep reusable code in `src/`.
- Keep workflow-specific scripts in `tools/`.
- Keep active dataset work in `data/dataset/working/`.
- Keep stable exported splits in `data/dataset/final/` and `data/dataset/pgmr/final/`.
- Keep generated evaluation outputs under `outputs/`; do not treat them as source datasets.

## Evaluation Outputs

A normal evaluation run writes `benchmark_raw.json` and `benchmark_summary.json`. Additional post-hoc tools may add companion files such as:

- `llm_judge_raw.json`: per-item semantic LLM judge records
- `llm_judge_summary.json`: aggregate semantic judge scores
- `benchmark_summary_with_llm_judge.json`: original summary plus embedded LLM judge summary

The original `benchmark_summary.json` is intentionally not overwritten.
