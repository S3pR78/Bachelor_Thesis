# Data Directory

`code/data/` stores the project data assets used by dataset construction, model evaluation, PGMR restoration, ACE playbooks, and analysis.

## Structure

| Path | Purpose |
| --- | --- |
| `dataset/` | Main dataset workspace: sources, expansion artifacts, working files, reports, final exports, PGMR exports, and archives. |
| `orkg_memory/` | Memory templates that map PGMR placeholders to ORKG predicates/classes and support grounding checks. |
| `ace_playbooks/` | Active ACE playbooks grouped by model, family, and mode. |
| `ace_playbooks_rule_based_frozen/` | Frozen historical/rule-based playbook snapshots for reproducibility and comparison. |

## Source Of Truth

For active direct-SPARQL dataset work, start with:

```text
code/data/dataset/working/
```

For stable direct-SPARQL exports used in experiments, use:

```text
code/data/dataset/final/
```

For stable PGMR-lite exports used in PGMR experiments, use:

```text
code/data/dataset/pgmr/final/
```

For ORKG mapping/memory files, use:

```text
code/data/orkg_memory/templates/
```

## Dataset Families

The active supported families are:

- `nlp4re`
- `empirical_research_practice`

Many prompts, playbooks, memory files, and evaluation reports are split by these families.

## Data Lifecycle

1. Source or generated material starts in `dataset/sources/` or `dataset/expansion/`.
2. Reviewed and consolidated data moves into `dataset/working/`.
3. Analysis outputs go into `dataset/reports/`.
4. Stable direct-SPARQL exports go into `dataset/final/`.
5. PGMR-lite transformed exports go into `dataset/pgmr/final/`.
6. Superseded historical files move into `dataset/archive/`.

## Do Not Confuse

- `dataset/expansion/` contains generated/review-stage candidates, not final benchmark data.
- `dataset/working/` contains active construction files, not necessarily stable releases.
- `dataset/final/` contains stable direct-SPARQL files used by experiments.
- `dataset/pgmr/final/` contains stable PGMR-lite versions of those datasets.
- `outputs/` outside `data/` contains run results, not source datasets.
