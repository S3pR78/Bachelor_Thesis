# Dataset Expansion Candidates

This directory stores generated candidate dataset files before they are reviewed and merged into benchmark or fine-tuning datasets.

## Purpose
Keep generated candidate data separate from:
- the current benchmark seed dataset
- reviewed benchmark additions
- future fine-tuning training splits

This prevents accidental mixing of unreviewed generated data with approved benchmark data.

## File naming convention

Use the following naming pattern:

`<batch_id>_<family>_candidates.json`

Examples:
- `benchmark_b001_nlp4re_candidates.json`
- `benchmark_b001_empirical_candidates.json`

## Expected file contents

Each file should contain a JSON array of candidate dataset entries.

Each entry should already contain full metadata, including:
- `id`
- `source_id`
- `question`
- `gold_sparql`
- `family`
- `source_dataset`
- `language`
- `query_type`
- `query_shape`
- `answer_type`
- `complexity_level`
- `ambiguity_risk`
- `lexical_gap_risk`
- `hallucination_risk`
- `query_components`
- `special_types`
- `number_of_patterns`
- `human_or_generated`
- `gold_status`
- `review_status`
- `split`

## Required initial metadata for generated candidates

Unless a later review process changes them, generated candidate entries should start with:

- `human_or_generated = "generated"`
- `gold_status = "draft"`
- `review_status = "unreviewed"`
- `split = "train"`

## Review policy

Generated candidate files in this directory are not final benchmark files.

Before reuse, candidates should be checked for:
- JSON validity
- duplicate questions
- duplicate question-SPARQL pairs
- schema faithfulness
- SPARQL sanity
- metadata consistency
- answer_type correctness
- query_components correctness

## Recommended follow-up locations

After review, accepted data can be moved or copied into more specific locations such as:
- benchmark addition candidates
- fine-tuning pool
- reviewed merged datasets