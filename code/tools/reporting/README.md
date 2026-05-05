# Reporting Tools

Reporting tools create human-readable or machine-readable summaries of dataset quality. They do not change the dataset itself.

## Scripts

| Script | Purpose |
| --- | --- |
| `export_dataset_validation_report.py` | Build a validation report for dataset fields, schema expectations, and quality checks. |
| `export_dataset_field_distribution_report.py` | Count and summarize distributions of fields such as family, answer type, query shape, complexity, and split. |

## Examples

```bash
PYTHONPATH=code python code/tools/reporting/export_dataset_validation_report.py \
  --dataset code/data/dataset/working/master_validated_with_paraphrases.json \
  --schema code/config/schemas/benchmark_dataset_schema_v1.json \
  --output code/data/dataset/reports/master_validated_with_paraphrases.validation_report.json
```

```bash
PYTHONPATH=code python code/tools/reporting/export_dataset_field_distribution_report.py \
  --dataset code/data/dataset/working/master_validated_with_paraphrases.json \
  --output code/data/dataset/reports/master_validated_with_paraphrases.field_distribution_report.json
```

## When To Use

Run reporting after major dataset changes:

- after merging selected candidates
- after deduplication
- after adding paraphrases
- before final split export
- before citing dataset counts in the thesis
