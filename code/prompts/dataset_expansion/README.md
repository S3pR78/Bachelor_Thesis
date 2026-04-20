# Dataset Expansion Prompt Workflow

This directory contains prompt wrappers for controlled dataset expansion.

## Goal
Reuse the existing family-specific ORKG/SPARQL prompts from the repository and combine them with batch-specific dataset-expansion wrappers.

This keeps:
- schema grounding in the original family prompt
- generation control in a small batch wrapper

## Base family prompts

Use exactly one of these as the schema-grounding base:

- `code/prompts/empire_compass/generated/rendered/nlp4re_prompt.txt`
- `code/prompts/empire_compass/generated/rendered/empirical_research_prompt.txt`

## Current batch wrappers

- `benchmark_b001_answer_type_gaps_prompt.md`

## Assembly rule

A final generation prompt should be assembled in this order:

1. Family-specific base prompt
2. Batch-specific wrapper prompt
3. Optional run-specific instruction block

## Recommended run-specific instruction block

You can append a small run-specific block like this:

- selected family
- number of candidates to generate
- target IDs
- extra diversity notes
- duplicate-avoidance hints

Example:
- family: `nlp4re`
- generate: `10 candidates`
- batch prefix: `benchmark_b001_nlp4re`
- avoid copying prior examples
- prefer medium complexity with some variation

## Output handling

Generated items should first be treated as candidate data, not as final benchmark gold data.

Recommended initial metadata:
- `human_or_generated = "generated"`
- `gold_status = "draft"`
- `review_status = "unreviewed"`
- `split = "train"`

Only after validation and review should items be promoted for benchmark use.

## Suggested output location for generated candidates

Store generated candidate files under:

- `code/data/dataset/expansion/candidates/`

Examples:
- `code/data/dataset/expansion/candidates/benchmark_b001_nlp4re_candidates.json`
- `code/data/dataset/expansion/candidates/benchmark_b001_empirical_candidates.json`

## Validation reminder

Before adding generated data to benchmark or fine-tuning pools, check:

- JSON validity
- metadata completeness
- SPARQL syntax sanity
- schema faithfulness
- duplicate questions
- duplicate question-SPARQL pairs
- answer_type correctness
- query_components correctness