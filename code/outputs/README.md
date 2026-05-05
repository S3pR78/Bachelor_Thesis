# Outputs

`code/outputs/` stores generated experiment results. These files are useful for analysis and reproducibility, but they are not source datasets.

## Structure

| Path | Purpose |
| --- | --- |
| `evaluation_runs/` | Current evaluation outputs grouped by model and run name. |
| `archive/` | Historical experiment outputs and older result files. |

## Evaluation Run Shape

Evaluation runs are created by:

```bash
PYTHONPATH=code python code/src/main.py evaluate ...
```

Each run directory usually contains:

- `benchmark_raw.json`: per-example prompts, raw model outputs, extracted/restored queries, execution payloads, and metric details
- `benchmark_summary.json`: aggregate metric summary and run metadata
- `llm_judge_raw.json`: optional post-hoc semantic LLM judge records for each judged or skipped item
- `llm_judge_summary.json`: optional aggregate LLM judge scores, verdict counts, and skip/zero-score counts
- `benchmark_summary_with_llm_judge.json`: optional copy of the benchmark summary with the LLM judge summary embedded
- `ace_error_traces.json`: optional ACE traces built from errors
- `ace_llm_deltas_*.json`: optional LLM-generated ACE rule candidates
- `llm_reflector_prompt_*.txt`: optional saved LLM reflection prompts

## Naming

Run directories are generated from model name, prompt mode, dataset name, and timestamp. Do not hand-edit results unless you are intentionally creating a curated analysis artifact.

Post-hoc tools should not overwrite `benchmark_summary.json`. They should write companion files so the original deterministic evaluation output remains available.
