# Prompts

`code/prompts/` contains prompt templates and generated prompt artifacts used for query generation and dataset expansion.

## Structure

| Path | Purpose |
| --- | --- |
| `empire_compass/` | TypeScript-based Empire Compass prompt templates and generator. |
| `empire_compass_mini/` | Static smaller direct-SPARQL prompt templates by family. |
| `pgmr/` | Full PGMR prompt templates by family. |
| `pgmr_mini/` | Smaller PGMR prompt templates by family, used by lightweight/fine-tuned runs. |
| `dataset_expansion/` | Prompt assets for generating new dataset candidates. |

## Query Prompt Families

The active families are:

- `nlp4re`
- `empirical_research_practice`

For family-specific prompt modes, pass the family explicitly:

```bash
PYTHONPATH=code python code/src/main.py query \
  --model gpt_4o_mini \
  --prompt-mode pgmr_mini \
  --family empirical_research_practice \
  --question "Which papers report threats to validity?"
```

## Prompt Modes

| Mode | Source |
| --- | --- |
| `empire_compass` | Generated from `empire_compass/templates/` through the TypeScript generator. |
| `empire_compass_mini` | Static `.txt` files in `empire_compass_mini/`. |
| `pgmr` | Static `.txt` files in `pgmr/`. |
| `pgmr_mini` | Static `.txt` files in `pgmr_mini/`. |

Paths are resolved through `code/config/path_config.json`.

The TypeScript generator in `empire_compass/` was copied/adapted from the Empire Compass repository. For more information about the original generator, see <https://github.com/okarras/empire-Compass/>.

## Dataset Expansion Prompts

Dataset expansion prompts are built from:

- wrapper prompts in `dataset_expansion/wrappers/`
- concrete run prompts in `dataset_expansion/runs/` or `dataset_expansion/scaled_runs/`
- assembled generated prompts in `dataset_expansion/assembled/`

See [dataset_expansion/README.md](dataset_expansion/README.md) for the full expansion prompt workflow.
