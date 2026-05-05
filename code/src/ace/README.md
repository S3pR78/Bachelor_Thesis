# ACE Package

`src/ace/` contains the reusable logic for Adaptive Context Engineering. ACE playbooks are compact, model/family-specific rule lists that can be rendered into prompts to help the model avoid repeated mistakes.

## Modules

| Module | Purpose |
| --- | --- |
| `playbook.py` | Dataclasses and JSON load/save helpers for ACE bullets, deltas, and playbooks. |
| `rendering.py` | Converts a playbook into a compact prompt block. |
| `routing.py` | Resolves the correct playbook path from model, family, and mode. |
| `traces.py` | Builds and saves error trace reports from evaluation outputs. |
| `reflector.py` | Offline rule reflection helpers that turn trace patterns into candidate deltas. |
| `llm_reflector.py` | OpenAI-backed reflection that proposes playbook rule deltas from error traces. |
| `curator.py` | Applies delta reports to playbooks and handles curation logic. |
| `offline_loop.py` | Runs local/offline ACE iteration loops for debugging and playbook updates. |
| `llm_pipeline.py` | CLI orchestration helper used by `main.py ace-llm`. |

## How ACE Is Used

ACE is optional in normal querying/evaluation. The prompt builder only prepends ACE context when `ace_max_bullets > 0` and a playbook path can be resolved.

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

## Playbook Naming

Playbooks are expected under:

```text
code/data/ace_playbooks/<model>/<family>_<mode>_playbook.json
```

Supported modes are usually:

- `pgmr_lite`
- `direct_sparql`

## Related Tools

See `code/tools/ace/` for scripts that create splits, inspect errors, and import curated deltas.
