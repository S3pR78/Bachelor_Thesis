# Dataset Expansion Candidates

This directory stores generated candidate dataset files before they are reviewed and enriched.

## Current active file format

Each file currently contains a JSON array of candidate entries with only:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Additional metadata is added later in a separate enrichment step.

## Review policy

Generated candidate files in this directory are not final benchmark files.

Before reuse, candidates should be checked for:
- JSON validity
- duplicate questions
- duplicate question-SPARQL pairs
- schema faithfulness
- SPARQL sanity
- suspicious predicates
- answer_type correctness
- question-query alignment

## Naming convention

Use:
`<batch_id>_<family>_candidates.json`

Examples:
- `b001_nlp4re_candidates.json`
- `b003_empirical_candidates.json`