# ACE Tools

ACE means Adaptive Context Engineering in this repository. The ACE workflow turns repeated model failures into compact playbook rules that can be prepended to future prompts.

## Scripts

| Script | Purpose |
| --- | --- |
| `create_ace_splits_from_master.py` | Create train, validation, ACE playbook, and benchmark splits from a master dataset. Supports size controls, family balancing, forced IDs, paraphrase requirements, dry runs, and overwrite protection. |
| `inspect_errors_for_ace.py` | Read `benchmark_raw.json`, extract failed or weak examples, and write ACE error traces for later reflection. |
| `curate_ace_playbook.py` | Apply a delta report to an ACE playbook and produce a curated playbook JSON. |
| `import_llm_deltas_to_playbook.py` | Import LLM-generated candidate rules into an existing playbook, with family/mode metadata and a cap on newly imported rules. |

## Typical Workflow

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
