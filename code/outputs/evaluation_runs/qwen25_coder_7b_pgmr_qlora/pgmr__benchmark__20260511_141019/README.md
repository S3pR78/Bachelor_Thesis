# Frozen ACE Benchmark Run

## Purpose

This run evaluates the model on the final held-out benchmark using the final frozen ACE playbooks.

This is **not** an online ACE repair run. The playbook is not updated during this evaluation. The model receives the relevant family- and format-specific ACE playbook as additional prompt context, generates one query per benchmark question, and is then evaluated normally.

## Run Configuration

| Field | Value |
|---|---|
| Model key | `qwen25_coder_7b_pgmr_qlora` |
| Prompt mode | `pgmr` |
| Prediction format | `pgmr_lite` |
| Dataset | `code/data/dataset/pgmr/final/benchmark.json` |
| ACE mode | Frozen playbook evaluation |
| Playbook update during benchmark | No |
| Online repair attempts | No |
| Reflector / Curator used during benchmark | No |

## ACE Playbooks Used

The evaluation should use the final refined ACE playbooks from:

- `code/data/ace_playbooks/qwen25_coder_7b_pgmr_qlora/empirical_research_practice__pgmr_lite.txt`
- `code/data/ace_playbooks/qwen25_coder_7b_pgmr_qlora/nlp4re__pgmr_lite.txt`

The prompt builder routes by model key, template family, and prediction format.

## Methodological Meaning

This run corresponds to the **Frozen ACE Benchmark** condition:

1. ACE playbooks were built before benchmark evaluation using the dedicated ACE playbook split.
2. The playbooks were refined and safety-checked.
3. During this benchmark run, the playbooks are fixed.
4. No benchmark item is used to generate or accept new rules.
5. The resulting metrics can be compared directly against the corresponding non-ACE baseline run for the same model and prompt mode.

This differs from `test_time_repair`, where temporary per-item repair attempts may be made without carrying rules across benchmark items.

## Output Files

Expected files in this folder:

- `benchmark_raw.json` — per-item predictions, restored/executed queries, diagnostics, and metrics.
- `benchmark_summary.json` — aggregate benchmark metrics.
- `README.md` — this description file.

## Selected Metrics

_Summary exists, but standard metric keys were not found in a flat form._

## Notes

Use this run for comparing **baseline vs. frozen ACE**. Do not interpret it as online learning or benchmark-time adaptation.
