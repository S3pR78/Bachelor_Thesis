# Utils Package

`src/utils/` contains small shared helpers used across the project.

## Modules

| Module | Purpose |
| --- | --- |
| `config_loader.py` | Loads JSON configuration files, resolves path keys from `code/config/path_config.json`, and retrieves model entries from `model_config.json`. |

## Common Use

Most source packages and tools use this package instead of hardcoding important paths.

Examples of configured path keys:

- `dataset.final.train`
- `dataset.working.master_split`
- `prompts.pgmr_mini_nlp4re_prompt`
- `outputs.evaluation_runs`
- `config.model_config`
