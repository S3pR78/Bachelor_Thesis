# Source Packages

This folder contains the main Python source packages used by the project.

## Package structure

- `ace/`
  - ACE-specific pipeline and playbook utilities.
- `core/`
  - Core model and provider integration helpers.
- `evaluate/`
  - Evaluation pipeline for SPARQL predictions and PGMR-lite output.
- `pgmr/`
  - PGMR-lite postprocessing, transformation, and restore utilities.
- `query/`
  - Query generation, prompt building, and execution helpers.
- `sparql/`
  - SPARQL execution and normalization utilities.
- `train/`
  - Training dataset construction and trainer classes.
- `utils/`
  - Small utility modules for configuration loading and shared helpers.

## Notes

Use `PYTHONPATH=code` when running scripts and package modules from the repository root.
