# Dataset Tools

This folder contains scripts for processing, validating, and enriching dataset entries in the project.

## Scripts

- `add_paraphrased_questions_openai.py`
  - Generate paraphrased questions with OpenAI to enrich the dataset.
- `create_train_with_paraphrases.py`
  - Build a training dataset that includes paraphrased question variants.
- `dedupe_dataset_entries.py`
  - Remove duplicate examples from a dataset split.
- `enrich_dataset_with_gold_results.py`
  - Add gold-standard SPARQL results to dataset entries.
- `enrich_selected_candidates.py`
  - Enrich selected expansion candidates with additional metadata or gold labels.
- `export_split_files.py`
  - Export dataset splits in the required format for training or evaluation.
- `normalize_sparql_in_dataset.py`
  - Normalize SPARQL queries inside dataset entries to a consistent format.
- `sample_dataset_entries.py`
  - Sample a subset of dataset entries for analysis or debugging.
- `split_dataset_by_rules.py`
  - Split datasets according to custom rules or split definitions.
- `validate_dataset_execution.py`
  - Validate whether dataset SPARQL queries execute successfully against the configured endpoint.

## Usage

These scripts support dataset creation and cleanup workflows. Run them from the repository root with `PYTHONPATH=code`.
