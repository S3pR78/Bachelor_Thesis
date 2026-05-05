# Review Tools

Review tools inspect generated dataset expansion candidates before they are allowed into the active working dataset.

The goal is to separate:

- green candidates: strong enough for inclusion after enrichment/validation
- yellow candidates: possibly useful but requiring repair or caution
- red candidates: rejected or only useful as negative evidence

## Scripts

| Script | Purpose |
| --- | --- |
| `check_expansion_candidates.py` | Run automatic structural checks over generated candidates, including likely duplicate/format/query issues. |
| `review_expansion_candidates.py` | Execute and review candidate SPARQL against the ORKG endpoint; writes review outputs. |
| `select_green_candidates.py` | Merge/select candidates marked as green and write selected pools plus summaries. |
| `benchmark_summary_app.py` | Streamlit app for interactively inspecting benchmark summaries and raw evaluation results. |

## Typical Candidate Review Flow

```bash
PYTHONPATH=code python code/tools/review/check_expansion_candidates.py \
  --candidate-file code/data/dataset/expansion/candidates/b005_nlp4re_wave01_candidates.json \
  --benchmark-file code/data/dataset/final/benchmark.json \
  --candidate-dir code/data/dataset/expansion/candidates
```

```bash
PYTHONPATH=code python code/tools/review/review_expansion_candidates.py \
  --candidate-file code/data/dataset/expansion/candidates/b005_nlp4re_wave01_candidates.json \
  --output-file code/data/dataset/expansion/review/execution/b005_nlp4re_wave01_execution_review.json \
  --sparql-endpoint https://www.orkg.org/triplestore
```

```bash
PYTHONPATH=code python code/tools/review/select_green_candidates.py \
  --candidate-file code/data/dataset/expansion/candidates/b005_nlp4re_wave01_candidates.json \
  --review-file code/data/dataset/expansion/review/execution/b005_nlp4re_wave01_execution_review.json \
  --green-output-file code/data/dataset/expansion/selected/green_candidates_merged.json \
  --yellow-output-file code/data/dataset/expansion/selected/yellow_candidates_merged.json \
  --red-output-file code/data/dataset/expansion/selected/red_candidates_merged.json \
  --summary-output-file code/data/dataset/expansion/selected/selection_summary.json
```

## Streamlit Summary App

Use the summary app to inspect evaluation outputs:

```bash
PYTHONPATH=code streamlit run code/tools/review/benchmark_summary_app.py
```

This app is for local review and analysis; it does not create final dataset exports.

## Output Locations

- automatic check reports: `code/data/dataset/expansion/review/`
- execution review files: `code/data/dataset/expansion/review/execution/`
- selected candidate pools: `code/data/dataset/expansion/selected/`
