# Final Dataset Expansion Prompts

This directory contains fully assembled, ready-to-use generation prompts for dataset expansion runs.

These prompts are the end products of the modular prompt workflow defined in `code/prompts/dataset_expansion/`.

## Purpose

Use the files in this directory when you want to directly generate candidate dataset entries without manually assembling:

1. family base prompt
2. batch wrapper prompt
3. run-specific instruction block

## Available final prompts

- `benchmark_b001_nlp4re_full_prompt.md`
- `benchmark_b001_empirical_full_prompt.md`

## What these files already include

Each final prompt already combines:

- family-specific schema grounding
- batch-specific generation objective
- run-specific constraints
- metadata requirements
- output formatting rules

## Recommended usage

Use one final prompt at a time.

Expected output:
- one JSON array
- one candidate batch
- ready to save under `code/data/dataset/expansion/candidates/`

## Recommended output files

For the current b001 batch:

- `code/data/dataset/expansion/candidates/benchmark_b001_nlp4re_candidates.json`
- `code/data/dataset/expansion/candidates/benchmark_b001_empirical_candidates.json`

## Relationship to the modular workflow

The modular source files remain useful for maintenance and future batch creation:

- base prompts: `code/prompts/empire_compass/generated/rendered/`
- batch wrappers: `code/prompts/dataset_expansion/`
- run files: `code/prompts/dataset_expansion/runs/`

The files in this `final/` directory are the execution-ready versions.

## Naming convention

Use the pattern:

`<batch_id>_<family>_full_prompt.md`

Examples:
- `benchmark_b001_nlp4re_full_prompt.md`
- `benchmark_b001_empirical_full_prompt.md`

## Important note

Outputs generated with these prompts are still candidate data.
They must not be treated as final benchmark gold data before validation and review.