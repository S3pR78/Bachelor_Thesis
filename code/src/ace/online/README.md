# Online ACE

Online ACE is the per-question adaptive workflow. For each question, the
current context is used to generate and evaluate a query. If the attempt fails,
a reflector proposes one small rule, the in-memory context is updated, and the
same question is retried with that updated context before moving on.

This differs from offline ACE-style playbook construction, where a full
evaluation run is analyzed only after completion and context rules are derived
afterward.

The implementation is intentionally being added in small steps. This package is
the home for the online loop, dataset selection, context management, reflection,
trace writing, and cost tracking.

## Modules

| Module | Purpose |
| --- | --- |
| `selection.py` | Deterministic dataset filtering, shuffling, limiting, and selected ID capture. |
| `context.py` | In-memory online playbook management, rule selection, rule addition, and helpful/harmful tracking. |
| `costs.py` | Reflection usage aggregation and terminal cost formatting. |
| `trace.py` | JSON writers for trace, summary, final playbook, and cost summary outputs. |
| `loop.py` | Per-question online ACE loop with pluggable generation, evaluation, and reflection hooks. |
| `reflector.py` | OpenAI-backed online reflector interface that returns one concise JSON rule. |
| `pipeline.py` | Adapter from the online loop hooks to existing prompt building, model generation, PGMR restoration, SPARQL execution, and metrics. |
| `reporting.py` | Terminal progress and final summary formatting. |

## Command

The CLI wrapper is intentionally thin:

```bash
PYTHONPATH=code python code/tools/ace/online/run_online_ace_loop.py \
  --model qwen25_coder_7b_pgmr_qlora \
  --dataset code/data/dataset/pgmr/final/ace_playbook.json \
  --prompt-mode pgmr_mini \
  --prediction-format pgmr_lite \
  --family nlp4re \
  --pgmr-memory-dir code/data/orkg_memory/templates \
  --sparql-endpoint https://www.orkg.org/triplestore \
  --initial-playbook code/data/ace_playbooks/online/qwen25_coder_7b_pgmr_qlora/pgmr_mini/nlp4re__pgmr_lite_playbook.json \
  --output-dir code/outputs/ace_online_runs/qwen25_coder_7b_pgmr_qlora/pgmr_mini/nlp4re_seed42_limit10 \
  --iterations 3 \
  --limit 10 \
  --shuffle \
  --sample-seed 42 \
  --reflect-model gpt_4o_mini
```

Use `--dry-run` to validate argument parsing and deterministic item selection
without loading a model, calling OpenAI, calling SPARQL, or writing run outputs.

## Playbooks

Online playbooks are workflow-specific and should live under:

```text
code/data/ace_playbooks/online/<model_key>/<prompt_mode>/<family>__<prediction_format>_playbook.json
```

The CLI requires `--initial-playbook`, but if that file does not exist yet the
run starts from an empty in-memory online playbook. The source playbook is never
overwritten. The final learned playbook is written to the run output directory
as `online_ace_playbook_final.json`.

## Outputs

Each run writes these files to `--output-dir`:

| File | Purpose |
| --- | --- |
| `online_ace_trace.json` | Item and iteration-level attempts, rules used, generated queries, metrics, rule usefulness, and costs. |
| `online_ace_summary.json` | Run metadata, selected item IDs, solved counts, rule counts, metric means/deltas, and cost summary. |
| `online_ace_playbook_final.json` | Final in-memory playbook including added rules and helpful/harmful tracking. |
| `online_ace_cost_summary.json` | Aggregated reflector token usage and estimated cost when pricing is known. |

## Local Testing

Unit tests are written around mocks or no-endpoint execution. They must not load
7B models, call OpenAI, or call the real SPARQL endpoint.

```bash
PYTHONPATH=code python -m pytest \
  code/tests/ace/test_online_selection.py \
  code/tests/ace/test_online_costs.py \
  code/tests/ace/test_online_context.py \
  code/tests/ace/test_online_trace.py \
  code/tests/ace/test_online_loop.py \
  code/tests/ace/test_online_reflector.py \
  code/tests/ace/test_online_pipeline.py \
  code/tests/ace/test_online_reporting.py
```
