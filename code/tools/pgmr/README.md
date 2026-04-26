# PGMR Tools

Utilities for evaluating PGMR-lite model outputs and restoring predicted PGMR-lite queries to executable ORKG SPARQL.

## Main tools

### evaluate_model_outputs.py
Generates PGMR-lite predictions for a dataset split, applies PGMR postprocessing, and stores raw/postprocessed predictions plus structural checks.

### restore_and_execute_predictions.py
Restores `pgmr:` / `pgmrc:` placeholders to ORKG predicates/classes and optionally executes restored SPARQL queries against the ORKG triplestore.

## Typical workflow

```bash
PYTHONPATH=code python code/tools/pgmr/evaluate_model_outputs.py \
  --model t5_base_pgmr_lite_final \
  --dataset code/data/dataset/pgmr/final/validation.json \
  --output code/outputs/pgmr_model_eval/final_validation_predictions.json

PYTHONPATH=code python code/tools/pgmr/restore_and_execute_predictions.py \
  --report code/outputs/pgmr_model_eval/final_validation_predictions.json \
  --dataset code/data/dataset/pgmr/final/validation.json \
  --output code/outputs/pgmr_model_eval/final_validation_restore_execute.json \
  --endpoint https://www.orkg.org/triplestore