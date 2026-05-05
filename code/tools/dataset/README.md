# Dataset Tools

These tools prepare dataset JSON files for validation, training, benchmark evaluation, and PGMR-lite transformation.

Most scripts follow this pattern:

```bash
PYTHONPATH=code python code/tools/dataset/<script>.py --input-file ... --output-file ...
```

Use `--overwrite` only when replacing a file intentionally.

## Scripts

| Script | Purpose | Common inputs/outputs |
| --- | --- | --- |
| `normalize_sparql_in_dataset.py` | Normalize `gold_sparql` text for consistent storage and comparison. | input dataset -> normalized dataset |
| `dedupe_dataset_entries.py` | Remove duplicate entries and write a dedupe report. | input dataset -> deduped dataset + report |
| `validate_dataset_execution.py` | Execute dataset SPARQL against an endpoint and report/query execution status. | dataset + endpoint -> validation report |
| `enrich_dataset_with_gold_results.py` | Add gold execution results to entries. | dataset + endpoint -> enriched dataset |
| `enrich_selected_candidates.py` | Add metadata and schema fields to selected expansion candidates. | selected candidates -> enriched candidates |
| `split_dataset_by_rules.py` | Split a master dataset into train/validation/benchmark/ACE pools according to fixed rules. | master dataset -> split dataset + summary |
| `export_split_files.py` | Export a split-containing dataset into separate split files. | split dataset -> `train.json`, `validation.json`, etc. |
| `sample_dataset_entries.py` | Draw reproducible samples for manual inspection or ACE dev pools. | input dataset -> sample file |
| `add_paraphrased_questions_openai.py` | Generate paraphrases for questions with OpenAI. | dataset -> dataset with `paraphrased_questions` |
| `create_train_with_paraphrases.py` | Expand training data by turning paraphrases into additional training examples. | final train dataset -> augmented train dataset |

## Typical Dataset Preparation Flow

```bash
PYTHONPATH=code python code/tools/dataset/normalize_sparql_in_dataset.py \
  --input-file code/data/dataset/working/master_validated_working.json \
  --output-file code/data/dataset/working/master_validated_normalized.json
```

```bash
PYTHONPATH=code python code/tools/dataset/dedupe_dataset_entries.py \
  --input-file code/data/dataset/working/master_validated_normalized.json \
  --output-file code/data/dataset/working/master_validated_deduped.json \
  --report-file code/data/dataset/reports/master_dedupe_report.json
```

```bash
PYTHONPATH=code python code/tools/dataset/validate_dataset_execution.py \
  --dataset code/data/dataset/working/master_validated_deduped.json \
  --endpoint https://www.orkg.org/triplestore \
  --output code/data/dataset/reports/master_execution_validation_report.json
```

```bash
PYTHONPATH=code python code/tools/dataset/export_split_files.py \
  --input-file code/data/dataset/working/master_validated_with_paraphrases_split_v2.json \
  --output-dir code/data/dataset/final
```

## Dataset Fields

The final dataset entries normally include:

- identity/source fields: `id`, `source_dataset`, `source_id`, `family`, `split`
- input/output fields: `question`, `paraphrased_questions`, `gold_sparql`
- query descriptors: `query_type`, `answer_type`, `query_shape`, `query_components`, `special_types`
- risk/review fields: `complexity_level`, `ambiguity_risk`, `lexical_gap_risk`, `hallucination_risk`, `review_status`, `gold_status`
- ACE/split fields: `previous_split`, `ace_split`

PGMR-transformed files add:

- `gold_pgmr_sparql`
- `pgmr_status`
- `pgmr_replaced_terms`
- `pgmr_unmapped_terms`

## Where Outputs Belong

- active working datasets: `code/data/dataset/working/`
- reports and summaries: `code/data/dataset/reports/`
- stable direct-SPARQL exports: `code/data/dataset/final/`
- stable PGMR-lite exports: `code/data/dataset/pgmr/final/`
