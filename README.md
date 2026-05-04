# BT Repository

This repository contains the code, data, tools, and documentation for the bachelor thesis project on text-to-SPARQL / ORKG benchmark and PGMR-lite workflows.

## Overview

- `code/` contains the main implementation, tools, prompts, and data assets.
- `code/src/` contains the Python package source code for model integration, query generation, evaluation, training, and utilities.
- `code/tools/` contains helper scripts for dataset generation, review, reporting, PGMR processing, and legacy utilities.
- `code/data/` contains dataset files, playbooks, sources, and generated dataset artifacts.
- `outputs/` contains evaluation outputs, reports, and archived results.
- `prompts/` contains prompt templates, dataset expansion prompts, and prompt generation resources.
- `text/` contains notes, methodology, literature summaries, and thesis chapters.
- `plan.md` contains the project plan.

## Getting Started

1. Install required dependencies and set up your Python environment.
2. Use `PYTHONPATH=code` when running repository scripts.
3. Start from the relevant tool folder or package depending on your task:
   - `code/tools/` for workflow scripts
   - `code/src/` for package-level modules

## Navigation

- `code/tools/README.md` — overview of helper tools and workflow phases.
- `code/src/README.md` — overview of the source packages.
- `code/tools/ace/README.md` — ACE helper scripts.
- `code/tools/dataset/README.md` — dataset processing utilities.
- `code/tools/generation/README.md` — prompt and expansion tools.
- `code/tools/reporting/README.md` — reporting and validation exporters.
- `code/tools/review/README.md` — review and candidate selection tools.
- `code/tools/legacy/README.md` — legacy scripts and archives.
- `code/tools/archive_docs/README.md` — archived documentation references.
- `code/src/ace/README.md` — ACE package overview.
- `code/src/core/README.md` — core model/provider utilities.
- `code/src/evaluate/README.md` — evaluation pipeline and metrics.
- `code/src/pgmr/README.md` — PGMR-lite processing utilities.
- `code/src/query/README.md` — query generation and execution helpers.
- `code/src/sparql/README.md` — SPARQL execution and normalization.
- `code/src/train/README.md` — training dataset and trainer modules.
- `code/src/utils/README.md` — shared utilities.

## Run examples

```bash
PYTHONPATH=code python code/tools/review/benchmark_summary_app.py
```

```bash
PYTHONPATH=code python code/tools/pgmr/evaluate_model_outputs.py --help
```

## Notes

- The repository uses a layered workflow: prompt generation, candidate review, dataset enrichment, model evaluation, and reporting.
- The `code/tools/` folder is the best entry point for workflow scripts.
- The `code/src/` packages are intended for reusable code and integration across scripts.
