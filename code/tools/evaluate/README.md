# Evaluation Analysis Tools

`code/tools/evaluate/` contains post-hoc tools that analyze existing evaluation runs. These scripts do not replace the main evaluation loop in `code/src/main.py evaluate`; they read already generated files such as `benchmark_raw.json` and write additional analysis artifacts next to them.

Run tools from the repository root:

```bash
PYTHONPATH=code python code/tools/evaluate/<script>.py --help
```

## Scripts

| Script | Purpose | Input | Output |
| --- | --- | --- | --- |
| `run_llm_judge.py` | Ask an OpenAI judge model to semantically score predicted SPARQL against the question and gold SPARQL. | `benchmark_raw.json` | `llm_judge_raw.json`, `llm_judge_summary.json`, optional `benchmark_summary_with_llm_judge.json` |

## LLM Judge

`run_llm_judge.py` is useful when exact answer metrics and query-text metrics do not fully explain whether a predicted query is semantically close to the requested question.

The judge receives only:

- natural-language question
- template family
- gold ORKG SPARQL query
- predicted/restored ORKG SPARQL query

It does not receive execution result tables.

### Prediction Field Selection

Default mode is `--prediction-field auto`.

Auto mode uses the first non-empty field in this order:

1. `pgmr_restored_query`
2. `restored_query`
3. `extracted_query`
4. `predicted_query`
5. `raw_model_output`

The raw output fallback is recorded in `llm_judge_raw.json` through `prediction_field_used` and `used_raw_model_output_fallback`.

Gold query selection uses the first available field:

1. `gold_sparql`
2. `gold_query`

The default judge does not use `gold_pgmr_sparql`; it compares restored ORKG-SPARQL against gold ORKG-SPARQL.

### Scoring

Each item receives:

- `intent_score`: `0-2`
- `schema_score`: `0-2`
- `projection_score`: `0-2`
- `constraint_score`: `0-2`
- `aggregation_score`: `0-2`
- `overall_score`: `0-10`
- `verdict`: `correct`, `partially_correct`, or `incorrect`

Skipped items are kept in `llm_judge_raw.json` as zero-score failures:

- all score fields are `0`
- `overall_score` is `0`
- `verdict` is `incorrect`
- `skipped` is `true`
- `skip_reason` explains why the item was zero-scored

Summary means include all output records, including skipped items as zeros.

### Example

```bash
PYTHONPATH=code python code/tools/evaluate/run_llm_judge.py \
  --input code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json \
  --output-dir code/outputs/evaluation_runs/<model>/<run> \
  --judge-model gpt_4o_mini \
  --prediction-field auto \
  --only-failures \
  --max-items 20
```

Use `--dry-run` to test field selection and output writing without calling OpenAI:

```bash
PYTHONPATH=code python code/tools/evaluate/run_llm_judge.py \
  --input code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json \
  --output-dir /tmp/llm_judge_dry_run \
  --judge-model gpt_4o_mini \
  --max-items 5 \
  --dry-run
```

OpenAI-backed runs require `OPENAI_API_KEY` in the shell environment or in the repository-root `.env` file.

## Viewing Results

Use the Streamlit app:

```bash
PYTHONPATH=code python -m streamlit run code/tools/review/benchmark_summary_app.py
```

Upload either:

- `benchmark_summary_with_llm_judge.json`
- `llm_judge_summary.json`

The app displays the LLM judge scores in a separate section because the judge uses `0-2` and `0-10` scales, not percentage metrics.
