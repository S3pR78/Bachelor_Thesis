# PGMR Package

`src/pgmr/` contains reusable PGMR-lite logic. PGMR-lite replaces ORKG identifiers with placeholders so models can focus on query structure, then restores placeholders with memory files.

## Modules

| Module | Purpose |
| --- | --- |
| `transform.py` | Converts direct ORKG SPARQL into PGMR-lite form. |
| `memory.py` | Loads memory templates and mapping data for supported families. |
| `postprocess.py` | Cleans PGMR-lite model output into a more regular query string. |
| `restore.py` | Restores PGMR placeholders back to executable ORKG SPARQL. |

## Memory Files

Memory templates live in:

```text
code/data/orkg_memory/templates/
```

Current templates:

- `nlp4re_memory.json`
- `empirical_research_practice_memory.json`

## How It Is Used

The main CLI can postprocess and restore one generated PGMR query:

```bash
PYTHONPATH=code python code/src/main.py query \
  --model gpt_4o_mini \
  --prompt-mode pgmr_mini \
  --family nlp4re \
  --question "Which papers mention traceability?" \
  --postprocess-pgmr \
  --restore-pgmr
```

Dataset-scale PGMR workflows live under `code/tools/pgmr/`.
