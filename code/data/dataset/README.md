# Dataset Workspace

`code/data/dataset/` is the main workspace for benchmark and training data. It contains the complete lifecycle from source examples and generated candidates to reviewed working files and final experiment splits.

## Directory Overview

| Path | Purpose |
| --- | --- |
| `sources/` | Source-aligned seed data and manually curated family-specific source files. |
| `expansion/` | Generated candidate files, review outputs, selected pools, repair material, and expansion methodology. |
| `working/` | Current active dataset files being edited, enriched, deduplicated, or split. |
| `reports/` | Validation, distribution, deduplication, paraphrase, split, and execution reports. |
| `final/` | Stable direct-SPARQL dataset exports used by experiments. |
| `pgmr/` | PGMR-lite transformed dataset exports and mirrors of final splits. |
| `archive/` | Historical datasets and obsolete snapshots kept for reproducibility. |

## Final Splits

The direct-SPARQL final files are:

| File | Purpose |
| --- | --- |
| `final/train.json` | Main training split. |
| `final/train_with_paraphrases.json` | Training split expanded with paraphrased questions. |
| `final/validation.json` | Validation split for tuning/checking runs. |
| `final/benchmark.json` | Benchmark/test split for final evaluation. |
| `final/ace_dev_pool.json` | Development pool for ACE analysis. |
| `final/ace_playbook.json` | Examples reserved for ACE playbook construction. |
| `final/ace_dev_pool_sample_80.json` | Sampled ACE development subset. |

The PGMR-lite equivalents live under:

```text
pgmr/final/
```

and include the same split names plus PGMR-specific fields.

## Entry Shape

Final direct-SPARQL entries typically contain:

- `id`, `source_dataset`, `source_id`, `family`, `split`, `language`
- `question`, `paraphrased_questions`, `gold_sparql`
- `query_type`, `answer_type`, `query_shape`, `special_types`, `query_components`
- `complexity_level`, `ambiguity_risk`, `lexical_gap_risk`, `hallucination_risk`
- `human_or_generated`, `review_status`, `gold_status`
- `previous_split`, `ace_split`

PGMR files add:

- `gold_pgmr_sparql`
- `pgmr_status`
- `pgmr_replaced_terms`
- `pgmr_unmapped_terms`

## Recommended Workflow

1. Start from `sources/` and `expansion/`.
2. Review and consolidate candidates.
3. Move active merged data into `working/`.
4. Generate validation and distribution reports into `reports/`.
5. Export stable splits into `final/`.
6. Transform final files into PGMR-lite under `pgmr/final/` when needed.
7. Move superseded snapshots into `archive/`.

## Important Rules

- Treat `working/` as active and changeable.
- Treat `final/` and `pgmr/final/` as stable experiment inputs.
- Do not put generated prompt outputs or evaluation runs here.
- Do not use raw expansion candidates directly for benchmark evaluation; review and validate them first.
