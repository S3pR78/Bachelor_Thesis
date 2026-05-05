# Tools

`code/tools/` contains workflow scripts for dataset construction, evaluation analysis, review, reporting, PGMR-lite processing, and ACE support. These scripts are less reusable than `code/src/`, but they are the practical entry points for most project work.

Run tools from the repository root:

```bash
PYTHONPATH=code python code/tools/<area>/<script>.py --help
```

Some tools execute SPARQL against the ORKG endpoint or call OpenAI; those require network access and relevant credentials.

## Workflow Areas

| Directory | Purpose | Start here when you need to... |
| --- | --- | --- |
| `generation/` | Build and run prompts for dataset expansion. | Generate new candidate question/query pairs. |
| `review/` | Check, review, summarize, and select generated candidates. | Decide whether generated entries are green/yellow/red quality. |
| `evaluate/` | Run post-hoc analysis over existing benchmark outputs. | Add semantic LLM judge scores without rerunning model inference. |
| `dataset/` | Normalize, enrich, deduplicate, validate, sample, and split datasets. | Prepare working datasets for final export. |
| `pgmr/` | Convert SPARQL to PGMR-lite, evaluate PGMR model outputs, and restore predictions. | Work with placeholder-based query generation. |
| `ace/` | Create ACE splits, inspect errors, curate/import playbook rules. | Improve model prompts based on observed errors. |
| `reporting/` | Export dataset validation and field-distribution reports. | Generate documentation/analysis outputs. |
| `legacy/` | Historical one-off scripts. | Read old workflows without treating them as current. |

## Recommended High-Level Flow

1. Generate candidates with `generation/`.
2. Review and select candidates with `review/`.
3. Enrich, normalize, validate, deduplicate, and split with `dataset/`.
4. Transform final data to PGMR-lite with `pgmr/` if needed.
5. Evaluate models with `code/src/main.py evaluate`.
6. Use `evaluate/` tools for post-hoc semantic judging when execution metrics need more explanation.
7. Use `ace/` tools to inspect errors and improve ACE playbooks.
8. Export reports with `reporting/`.

## Data Safety

Many tools write JSON outputs. Prefer writing to a new file first, then use `--overwrite` only when you intentionally want to replace an existing artifact.

Active working files should usually live in `code/data/dataset/working/`; final stable exports should live in `code/data/dataset/final/`; reports should live in `code/data/dataset/reports/`.
