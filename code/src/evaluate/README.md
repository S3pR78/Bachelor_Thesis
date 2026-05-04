# Evaluation Source Package

This package contains the evaluation pipeline and metrics used to score SPARQL predictions and PGMR-lite outputs.

## Modules

- `answer_metrics.py`
  - Implements answer-based score calculations.
- `answer_normalization.py`
  - Normalizes SPARQL execution results for comparison.
- `costs.py`
  - Computes cost- or difficulty-related evaluation metrics.
- `dataset_analysis.py`
  - Performs dataset-level analysis and summary statistics.
- `dataset_loader.py`
  - Loads evaluation datasets and gold references.
- `kg_memory.py`
  - Manages knowledge graph reference memory for grounding checks.
- `metric_runner.py`
  - Drives execution of evaluation metrics on model outputs.
- `metrics/`
  - Contains individual metric implementations and diagnostic checks.
- `query_elements.py`
  - Parses query elements for structural comparison.
- `query_text_normalization.py`
  - Normalizes query text for similarity metrics.
- `run_io.py`
  - Input/output utilities for evaluation runs.
- `runner.py`
  - Orchestrates evaluation execution workflows.
- `sparql_extraction.py`
  - Extracts SPARQL queries from model outputs.
- `summary.py`
  - Aggregates metric results into summary reports.

## Usage

The evaluation package is intended to be used by evaluation scripts and benchmark utilities under `code/tools/`.
