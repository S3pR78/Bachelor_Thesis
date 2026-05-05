# ORKG Text-to-SPARQL / PGMR-lite Bachelor Thesis Repository

This repository contains the code, data, prompts, experiments, and thesis notes for a bachelor thesis project on generating and evaluating ORKG SPARQL queries from natural-language research questions.

The project combines three related workflows:

- building and validating a benchmark/training dataset for ORKG question answering
- prompting, fine-tuning, and evaluating models that generate SPARQL or PGMR-lite queries
- improving prompts with ACE playbooks, error traces, and LLM-assisted reflection

## What This Repository Does

The main task is text-to-query generation for ORKG-style research questions. A model receives a natural-language question and should produce either:

- direct executable SPARQL using ORKG predicates/classes, or
- PGMR-lite, a placeholder-based query form that can later be restored to executable ORKG SPARQL.

The repository includes tools for generating candidate dataset entries, reviewing them, enriching them with execution results, splitting final datasets, training/fine-tuning models, evaluating model outputs, and analyzing errors.

## Repository Map

| Path | Purpose |
| --- | --- |
| `code/src/` | Reusable Python source packages for querying, evaluation, training, SPARQL handling, PGMR-lite, and ACE. |
| `code/tools/` | Script entry points for dataset preparation, candidate review, reporting, PGMR conversion, and ACE utilities. |
| `code/data/` | Dataset files, ORKG memory files, ACE playbooks, reports, working data, final exports, and archives. |
| `code/prompts/` | Prompt templates and generated prompts for Empire Compass, PGMR, PGMR-mini, and dataset expansion. |
| `code/config/` | Model, training, path, and schema configuration files. |
| `code/outputs/` | Evaluation runs, benchmark summaries, raw predictions, ACE traces, and archived experiment outputs. |
| `code/tests/` | Unit tests for ACE and evaluation metrics. |
| `text/` | Thesis notes, methodology drafts, literature, and written analysis. |

Start with [code/README.md](code/README.md) for the implementation map, [code/tools/README.md](code/tools/README.md) for script workflows, and [code/data/README.md](code/data/README.md) for data structure.

## Main Concepts

`SPARQL`: The final executable query language used against the ORKG triplestore.

`PGMR-lite`: A controlled placeholder representation for ORKG queries. It replaces hard ORKG identifiers with memory-backed placeholders, then restores them later with `code/data/orkg_memory/templates/`.

`ACE`: Adaptive Context Engineering. In this repo ACE means model/family-specific playbooks of compact rules and patterns that are prepended to prompts to reduce repeated mistakes.

`family`: The dataset/prompt family. The active families are `nlp4re` and `empirical_research_practice`.

`prompt mode`: The prompt template style used for query generation. Active modes include `empire_compass`, `empire_compass_mini`, `pgmr`, `pgmr_mini`, `zero_shot`, `few_shot`, and evaluation-only `pgmr_lite_meta`.

## Setup

Run commands from the repository root.

```bash
cd /path/to/BT
export PYTHONPATH=code
```

There is currently no pinned `requirements.txt` or `pyproject.toml` in the repository. From imports in the source, the project commonly needs:

```bash
pip install torch transformers huggingface_hub openai python-dotenv requests pandas streamlit
```

For LoRA/QLoRA training or adapter loading, also install:

```bash
pip install peft accelerate bitsandbytes
```

OpenAI-backed tools require an API key. The code loads a repo-root `.env` file, so this works:

```bash
OPENAI_API_KEY=...
```

You can also export the key in your shell:

```bash
export OPENAI_API_KEY=...
```

Do not commit your real `.env` file.

Empire Compass prompt generation uses Node/TypeScript assets under `code/prompts/empire_compass/`, so Node.js/npm are needed if those prompts must be regenerated. The generator was adapted from the Empire Compass repository; for more information, see <https://github.com/okarras/empire-Compass/>.

## Main CLI

The main CLI entry point is:

```bash
PYTHONPATH=code python code/src/main.py <mode> [args]
```

Available modes:

| Mode | Use |
| --- | --- |
| `query` | Generate one query for one question. |
| `evaluate` | Run a model on a dataset split, execute predictions/gold queries, and write raw + summary reports. |
| `train` | Run a configured fine-tuning job from `code/config/train_config.json`. |
| `ace-llm` | Build ACE traces from an evaluation run and generate/import candidate playbook rules. |

Example single query:

```bash
PYTHONPATH=code python code/src/main.py query \
  --model gpt_4o_mini \
  --prompt-mode pgmr_mini \
  --family nlp4re \
  --question "Which papers mention requirements traceability?" \
  --postprocess-pgmr \
  --restore-pgmr
```

Example evaluation:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model gpt_4o_mini \
  --dataset code/data/dataset/final/benchmark.json \
  --prompt-mode empire_compass_mini \
  --prediction-format sparql \
  --limit 5
```

Example PGMR-lite evaluation:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model gpt_4o_mini \
  --dataset code/data/dataset/pgmr/final/benchmark.json \
  --prompt-mode pgmr_mini \
  --prediction-format pgmr_lite \
  --pgmr-memory-dir code/data/orkg_memory/templates
```

Evaluation outputs are written below `code/outputs/evaluation_runs/<model>/<run-name>/` and normally include:

- `benchmark_raw.json`
- `benchmark_summary.json`
- optional ACE traces or LLM delta files

## Typical Workflows

### Dataset Construction

1. Work from source and generated candidates under `code/data/dataset/sources/` and `code/data/dataset/expansion/`.
2. Review generated candidates with tools in `code/tools/review/`.
3. Enrich, normalize, deduplicate, validate, and split data with tools in `code/tools/dataset/`.
4. Write reports into `code/data/dataset/reports/`.
5. Export final datasets into `code/data/dataset/final/` and PGMR-transformed datasets into `code/data/dataset/pgmr/final/`.

More detail: [code/tools/dataset/README.md](code/tools/dataset/README.md) and [code/data/dataset/README.md](code/data/dataset/README.md).

### Model Evaluation

1. Choose a model key from `code/config/model_config.json`.
2. Choose a dataset split from `code/data/dataset/final/` or `code/data/dataset/pgmr/final/`.
3. Run `code/src/main.py evaluate`.
4. Inspect `benchmark_summary.json` for aggregate metrics and `benchmark_raw.json` for per-example traces.
5. Use ACE tools if repeated error patterns should be turned into playbook rules.

More detail: [code/src/evaluate/README.md](code/src/evaluate/README.md).

### PGMR-lite Pipeline

1. Transform datasets from `gold_sparql` to `gold_pgmr_sparql`.
2. Generate PGMR-lite predictions.
3. Postprocess model output.
4. Restore placeholders through ORKG memory templates.
5. Execute restored SPARQL and evaluate.

More detail: [code/tools/pgmr/README.md](code/tools/pgmr/README.md) and [code/src/pgmr/README.md](code/src/pgmr/README.md).

### ACE Pipeline

1. Run a benchmark evaluation.
2. Build ACE error traces from `benchmark_raw.json`.
3. Reflect on repeated errors and generate candidate rules.
4. Curate/import rules into model-specific playbooks.
5. Rerun evaluation with `--ace-playbook-dir` and `--ace-max-bullets`.

More detail: [code/tools/ace/README.md](code/tools/ace/README.md) and [code/src/ace/README.md](code/src/ace/README.md).

## Important Files

| File | Why it matters |
| --- | --- |
| `code/config/model_config.json` | Defines model keys, providers, local model paths, OpenAI model IDs, generation settings, and adapter paths. |
| `code/config/train_config.json` | Defines fine-tuning runs, dataset inputs, training settings, LoRA settings, and output paths. |
| `code/config/path_config.json` | Central path registry used by prompt builders, dataset tools, and evaluation code. |
| `code/data/dataset/final/*.json` | Stable direct-SPARQL train/validation/benchmark exports. |
| `code/data/dataset/pgmr/final/*.json` | Stable PGMR-lite train/validation/benchmark exports. |
| `code/data/orkg_memory/templates/*.json` | Placeholder-to-ORKG mappings used for PGMR restoration and URI grounding checks. |
| `code/data/ace_playbooks/` | ACE playbooks grouped by model and family. |

## Tests

Tests live in `code/tests/` and are written for `pytest`.

```bash
PYTHONPATH=code pytest code/tests
```

In the current environment I could not run tests because `pytest` is not installed.

## Known Setup Notes

- Always set `PYTHONPATH=code` when running scripts from the repository root.
- The current environment is missing several runtime dependencies such as `torch` and `pytest`; install dependencies before using the model CLI or tests.
- Local Hugging Face models are loaded with `local_files_only=True`, so model directories in `code/models/` must already exist unless you run separate download/preparation steps.
- Some tools execute queries against `https://www.orkg.org/triplestore`; those steps need network access and may be slow or endpoint-dependent.
