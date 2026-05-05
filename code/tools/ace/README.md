# ACE Tools

ACE means Adaptive Context Engineering in this repository. ACE workflows turn repeated model failures into compact playbook rules that can be prepended to future prompts.

There are two ACE workflow types:

- Offline ACE-style playbook construction: run a full evaluation, inspect errors afterward, and derive or curate playbook rules from that completed run.
- Online ACE: update the in-memory context during a run, retry the same failed question with the new rule, and carry the improved context forward to later questions.

## Scripts

| Script | Purpose |
| --- | --- |
| `create_ace_splits_from_master.py` | Create train, validation, ACE playbook, and benchmark splits from a master dataset. Supports size controls, family balancing, forced IDs, paraphrase requirements, dry runs, and overwrite protection. |
| `inspect_errors_for_ace.py` | Read `benchmark_raw.json`, extract failed or weak examples, and write ACE error traces for later reflection. |
| `curate_ace_playbook.py` | Apply a delta report to an ACE playbook and produce a curated playbook JSON. |
| `import_llm_deltas_to_playbook.py` | Import LLM-generated candidate rules into an existing playbook, with family/mode metadata and a cap on newly imported rules. |
| `online/run_online_ace_loop.py` | Run the true per-question online ACE loop. The wrapper only parses CLI arguments and calls `src.ace.online`. |

## Offline Workflow

1. Run an evaluation:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model qwen25_coder_7b_instruct \
  --dataset code/data/dataset/pgmr/final/ace_dev_pool_sample_80.json \
  --prompt-mode pgmr_mini \
  --prediction-format pgmr_lite
```

2. Build ACE error traces:

```bash
PYTHONPATH=code python code/tools/ace/inspect_errors_for_ace.py \
  --raw code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json \
  --mode pgmr_lite \
  --output code/outputs/evaluation_runs/<model>/<run>/ace_error_traces.json
```

3. Import curated/LLM-generated deltas:

```bash
PYTHONPATH=code python code/tools/ace/import_llm_deltas_to_playbook.py \
  --playbook code/data/ace_playbooks/<model>/nlp4re_pgmr_lite_playbook.json \
  --deltas code/outputs/evaluation_runs/<model>/<run>/ace_llm_deltas_nlp4re.json \
  --family nlp4re \
  --mode pgmr_lite \
  --max-new-rules 5
```

4. Rerun evaluation with ACE enabled:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model qwen25_coder_7b_instruct \
  --dataset code/data/dataset/pgmr/final/benchmark.json \
  --prompt-mode pgmr_mini \
  --prediction-format pgmr_lite \
  --ace-playbook-dir code/data/ace_playbooks \
  --ace-mode pgmr_lite \
  --ace-max-bullets 5
```

## Playbook Location

Active playbooks are stored under:

```text
code/data/ace_playbooks/<model>/<family>_<mode>_playbook.json
```

Examples:

- `code/data/ace_playbooks/qwen25_coder_7b_instruct/nlp4re_pgmr_lite_playbook.json`
- `code/data/ace_playbooks/mistral_7b_instruct/empirical_research_practice_direct_sparql_playbook.json`

## Note

The main CLI mode `ace-llm` orchestrates trace building, LLM reflection, and importing. In this checkout, the source package for LLM reflection exists at `code/src/ace/llm_reflector.py`; check the orchestrated script path before relying on fully automatic ACE imports.

## Online Workflow

Online ACE source lives under `code/src/ace/online/`. The CLI requires an
explicit `--initial-playbook` path and writes the final online playbook to the
run output directory instead of overwriting the source playbook.

Example dry-run:

```bash
PYTHONPATH=code python code/tools/ace/online/run_online_ace_loop.py \
  --model qwen25_coder_7b_pgmr_qlora \
  --dataset code/data/dataset/pgmr/final/ace_playbook.json \
  --prompt-mode pgmr_mini \
  --prediction-format pgmr_lite \
  --sparql-endpoint https://www.orkg.org/triplestore \
  --initial-playbook code/data/ace_playbooks/online/qwen25_coder_7b_pgmr_qlora/pgmr_mini/nlp4re__pgmr_lite_playbook.json \
  --output-dir code/outputs/ace_online_runs/dry_run \
  --family nlp4re \
  --iterations 3 \
  --limit 10 \
  --shuffle \
  --sample-seed 42 \
  --dry-run
```

The full command removes `--dry-run` and may load a local model, call OpenAI for
reflection, and query the configured SPARQL endpoint.
