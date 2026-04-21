# Dataset Expansion Methodology

## Goal

The goal of this workflow is to expand the existing benchmark and fine-tuning candidate pool for Text-to-SPARQL generation over ORKG template families.

The current focus is on:
- `nlp4re`
- `empirical_research_practice`

## Why the workflow was simplified

Earlier prompt versions tried to generate full metadata together with each candidate.
This produced unstable outputs, especially for fields such as:
- query_shape
- query_components
- special_types
- review metadata

To improve stability, the workflow was changed to a minimal generation format.

## Current generation format

Each generated candidate currently contains only:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

All remaining metadata is added later in a separate enrichment step.

## Prompt architecture

Each generation prompt is assembled from three parts:

1. family-specific base prompt  
2. batch-specific wrapper  
3. run-specific instruction file

This keeps:
- schema grounding in the family prompt
- generation control in a small wrapper
- batch-specific variation in the run file

## Batch strategy

The workflow uses multiple batch types with different purposes, such as:
- answer-type coverage
- missing query component coverage
- non-factoid reasoning
- NLP4RE-focused expansion
- hard-case reserve generation

## Review strategy

The review process has two layers.

### 1. Structural and manual review
Generated batches are reviewed for:
- duplicates
- suspicious predicates
- question–query alignment
- logic issues
- repair candidates

### 2. Lightweight execution review
Queries are also executed against the ORKG triplestore.
The execution review stores only lightweight diagnostics, such as:
- execution status
- query type
- result cardinality
- small preview values

Full result sets are not stored for routine review.

## Repair strategy

Repair is review-first and conservative.

Current repair focus:
- repeated suspicious predicate patterns
- logic mismatches
- ranking/top-k phrasing mismatches

Repair dictionaries are maintained separately for each family.

## Current scaling strategy

Initial pilot batches were reviewed closely in small groups.

After stabilizing the prompts and output format, the workflow shifts to:
- larger generation waves
- automated execution review
- manual review only for flagged candidates

## Final selection

Generated candidates are not treated as final benchmark items immediately.

Before final reuse, candidates should pass:
- schema review
- logic review
- execution sanity checks
- enrichment
- final selection for benchmark or fine-tuning use