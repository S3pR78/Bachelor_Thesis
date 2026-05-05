# PGMR Tools

PGMR-lite is a placeholder-based representation of ORKG SPARQL. It helps models generate query structure without needing to memorize every ORKG predicate/class identifier. After generation, placeholders are restored to executable SPARQL using memory files in `code/data/orkg_memory/templates/`.

## Scripts

| Script | Purpose |
| --- | --- |
| `transform_dataset.py` | Convert dataset entries from `gold_sparql` to `gold_pgmr_sparql` and record replaced/unmapped terms. |
| `collect_unmapped_terms.py` | Analyze datasets for ORKG terms that are not covered by the current PGMR memory templates. |
| `evaluate_model_outputs.py` | Run a local seq2seq PGMR model over a dataset and write raw/postprocessed prediction reports. |
| `restore_and_execute_predictions.py` | Restore PGMR-lite predictions to ORKG SPARQL and optionally execute them against the endpoint. |

## Typical PGMR-lite Flow

1. Transform a direct-SPARQL dataset:

```bash
PYTHONPATH=code python code/tools/pgmr/transform_dataset.py \
  --input code/data/dataset/final/benchmark.json \
  --output code/data/dataset/pgmr/final/benchmark.json \
  --memory-dir code/data/orkg_memory/templates
```

2. Evaluate a PGMR model:

```bash
PYTHONPATH=code python code/tools/pgmr/evaluate_model_outputs.py \
  --model t5_base_pgmr_mini_15ep \
  --dataset code/data/dataset/pgmr/final/validation.json \
  --output code/outputs/pgmr_model_eval/final_validation_predictions.json
```

3. Restore and execute predictions:

```bash
PYTHONPATH=code python code/tools/pgmr/restore_and_execute_predictions.py \
  --report code/outputs/pgmr_model_eval/final_validation_predictions.json \
  --dataset code/data/dataset/pgmr/final/validation.json \
  --output code/outputs/pgmr_model_eval/final_validation_restore_execute.json \
  --memory-dir code/data/orkg_memory/templates \
  --endpoint https://www.orkg.org/triplestore
```

## Main CLI Alternative

PGMR-lite can also be evaluated through the main CLI:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model gpt_4o_mini \
  --dataset code/data/dataset/pgmr/final/benchmark.json \
  --prompt-mode pgmr_mini \
  --prediction-format pgmr_lite \
  --pgmr-memory-dir code/data/orkg_memory/templates
```

## Important Fields

PGMR-transformed dataset entries add:

- `gold_pgmr_sparql`: placeholder-based target query
- `pgmr_status`: whether transformation succeeded cleanly
- `pgmr_replaced_terms`: ORKG terms replaced by placeholders
- `pgmr_unmapped_terms`: terms missing from the memory template

During evaluation/restoration, prediction reports also include:

- `postprocessed_prediction`
- `pgmr_restored_query`
- `pgmr_missing_mapping_tokens`
- `pgmr_remaining_tokens`
- execution status, if an endpoint was provided
