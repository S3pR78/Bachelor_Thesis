# PGMR Source Package

This package contains utilities for PGMR-lite transformation, postprocessing, and SPARQL restoration.

## Modules

- `memory.py`
  - Manages memory and placeholder state during PGMR processing.
- `postprocess.py`
  - Applies PGMR-specific cleanup and normalization to model output.
- `restore.py`
  - Restores PGMR placeholders to executable ORKG SPARQL.
- `transform.py`
  - Transforms dataset or model outputs between PGMR and SPARQL formats.

## Usage

These modules are used by the PGMR evaluation and restore workflow under `code/tools/pgmr/`.
