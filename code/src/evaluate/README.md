# Evaluation Package

`src/evaluate/` implements the benchmark evaluation pipeline. It loads dataset entries, builds prompts, generates model outputs, extracts/restores queries, executes prediction and gold queries, computes metrics, and writes run summaries.

## Main Entry

The main entry point is `runner.py`, exposed as:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model gpt_4o_mini \
  --dataset code/data/dataset/final/benchmark.json \
  --prompt-mode empire_compass_mini \
  --prediction-format sparql
```

Outputs are written to:

```text
code/outputs/evaluation_runs/<model>/<run-name>/
```

## Modules

| Module | Purpose |
| --- | --- |
| `runner.py` | End-to-end evaluation orchestration. |
| `dataset_loader.py` | Loads JSON datasets and selects fields from entries. |
| `sparql_extraction.py` | Extracts SPARQL text from raw model output. |
| `run_io.py` | Creates run directories and standard raw/summary output paths. |
| `metric_runner.py` | Calls all configured metrics for one prediction/gold pair. |
| `summary.py` | Aggregates per-example metrics into benchmark summaries. |
| `answer_normalization.py` | Normalizes endpoint result values for answer comparison. |
| `answer_metrics.py` | Shared answer-level scoring helpers. |
| `query_text_normalization.py` | Normalizes SPARQL strings for text metrics. |
| `query_elements.py` | Extracts ORKG classes/properties/resources and structural elements. |
| `kg_memory.py` | Loads allowed ORKG references for grounding/URI hallucination checks. |
| `costs.py` | Estimates provider token/cost payloads when usage data is available. |
| `dataset_analysis.py` | Builds dataset validation and distribution reports. |
| `analysis/` | Additional analysis helpers such as execution error breakdowns. |
| `metrics/` | Individual metric implementations. |

## Metrics

The evaluation pipeline checks several dimensions:

- query extraction success
- supported query form and query-form match
- prediction and gold execution success
- answer exact match and answer precision/recall/F1
- normalized query exact match, BLEU-like query similarity, and ROUGE query similarity
- SPARQL structural match
- KG reference matching and URI hallucination
- PGMR unmapped placeholder diagnostics
- primary error category

ROUGE metrics are auxiliary query-text diagnostics:

- `query_rouge1_f1`
- `query_rouge2_f1`
- `query_rougeL_f1`

For PGMR-lite runs with a gold PGMR query, the pipeline can also report:

- `pgmr_rouge1_f1`
- `pgmr_rouge2_f1`
- `pgmr_rougeL_f1`

## PGMR-lite Evaluation

For PGMR-lite outputs, use:

```bash
--prediction-format pgmr_lite \
--pgmr-memory-dir code/data/orkg_memory/templates
```

The runner postprocesses PGMR output, restores placeholders to ORKG identifiers, and evaluates the restored SPARQL.

## Post-Hoc Semantic Judging

The main evaluation loop intentionally stays deterministic and execution/metric based. For semantic LLM-based analysis after a run has finished, use:

```bash
PYTHONPATH=code python code/tools/evaluate/run_llm_judge.py \
  --input code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json \
  --output-dir code/outputs/evaluation_runs/<model>/<run> \
  --judge-model gpt_4o_mini \
  --prediction-field auto
```

This writes `llm_judge_raw.json`, `llm_judge_summary.json`, and, when `benchmark_summary.json` exists in the same directory, `benchmark_summary_with_llm_judge.json`.
