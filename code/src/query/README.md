# Query Package

`src/query/` builds prompts and generates model responses for single-query and benchmark evaluation workflows.

## Modules

| Module | Purpose |
| --- | --- |
| `prompt_builder.py` | Selects prompt templates by mode/family, fills the question, and optionally prepends ACE context. |
| `inference_session.py` | Prepares reusable inference sessions for OpenAI or local Hugging Face models and returns response text plus usage data. |
| `query_executor.py` | Simpler single-call query generation helper used by `main.py query`. |

## Prompt Modes

Supported prompt modes include:

- `empire_compass`
- `empire_compass_mini`
- `pgmr`
- `pgmr_mini`
- `zero_shot`
- `few_shot`

Family-specific modes require:

```bash
--family nlp4re
```

or:

```bash
--family empirical_research_practice
```

## Example

```bash
PYTHONPATH=code python code/src/main.py query \
  --model gpt_4o_mini \
  --prompt-mode empire_compass_mini \
  --family empirical_research_practice \
  --question "Which papers report threats to validity?"
```
