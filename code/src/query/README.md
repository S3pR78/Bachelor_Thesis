# Query Source Package

This package includes query generation and execution helpers for the pipeline.

## Modules

- `inference_session.py`
  - Manages inference sessions for model-based query generation.
- `prompt_builder.py`
  - Builds prompts and input structures for query generation.
- `query_executor.py`
  - Executes generated queries against the configured SPARQL endpoint.

## Usage

These modules are used by the model generation and evaluation pipelines that produce and execute queries.
