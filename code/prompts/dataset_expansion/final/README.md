# Final Dataset Expansion Prompts

This directory contains execution-ready prompts for dataset expansion.

These files are the final prompts used by the OpenAI generation runner.

## Directory structure

- `core/`
  - controlled benchmark-oriented expansion runs
  - small, reviewable runs
  - usually `part1` and `part2`

- `scaled/`
  - larger wave-based candidate generation
  - intended for broader fine-tuning candidate expansion
  - usually `wave01`, `wave02`, and later waves

## Purpose of the two layers

### Core
Use core prompts when you want:
- tightly controlled batches
- smaller reviewable candidate sets
- initial validation of prompt behavior
- benchmark-oriented expansion

### Scaled
Use scaled prompts when you want:
- larger candidate generation
- repeated wave-based growth
- fine-tuning candidate pool expansion
- reuse of already validated batch logic

## Available core prompts

### B001
- `core/b001_nlp4re_part1_full_prompt.md`
- `core/b001_nlp4re_part2_full_prompt.md`
- `core/b001_empirical_part1_full_prompt.md`
- `core/b001_empirical_part2_full_prompt.md`

## Available scaled prompts

### B001
- `scaled/b001_nlp4re_wave01_full_prompt.md`
- `scaled/b001_empirical_wave01_full_prompt.md`

### B002
- `scaled/b002_nlp4re_wave01_full_prompt.md`
- `scaled/b002_empirical_wave01_full_prompt.md`

### B003
- `scaled/b003_nlp4re_wave01_full_prompt.md`
- `scaled/b003_empirical_wave01_full_prompt.md`

### B004
- `scaled/b004_nlp4re_wave01_full_prompt.md`

### B005
- `scaled/b005_nlp4re_wave01_full_prompt.md`
- `scaled/b005_empirical_wave01_full_prompt.md`

## Recommended execution order

### First practical runs
1. `core/b001_nlp4re_part1_full_prompt.md`
2. `core/b001_nlp4re_part2_full_prompt.md`
3. `core/b001_empirical_part1_full_prompt.md`
4. `core/b001_empirical_part2_full_prompt.md`

### Then scaled runs
5. `scaled/b001_nlp4re_wave01_full_prompt.md`
6. `scaled/b001_empirical_wave01_full_prompt.md`
7. `scaled/b002_nlp4re_wave01_full_prompt.md`
8. `scaled/b002_empirical_wave01_full_prompt.md`

### Then harder reasoning and hard-case waves
9. `scaled/b003_nlp4re_wave01_full_prompt.md`
10. `scaled/b003_empirical_wave01_full_prompt.md`
11. `scaled/b004_nlp4re_wave01_full_prompt.md`
12. `scaled/b005_nlp4re_wave01_full_prompt.md`
13. `scaled/b005_empirical_wave01_full_prompt.md`

## Output handling

Generated outputs should be written to:

- `code/data/dataset/expansion/candidates/`

These outputs are candidate data only.
They must not be treated as final benchmark gold data before review and validation.

## Validation rule

After each generated candidate file:

1. run duplicate checking
2. inspect schema warnings
3. inspect suspicious predicates
4. manually inspect at least a sample
5. only then continue

## Naming conventions

### Core prompt files
Pattern:
- `<batch>_<family>_<part>_full_prompt.md`

Examples:
- `b001_nlp4re_part1_full_prompt.md`
- `b001_empirical_part2_full_prompt.md`

### Scaled prompt files
Pattern:
- `<batch>_<family>_waveXX_full_prompt.md`

Examples:
- `b002_nlp4re_wave01_full_prompt.md`
- `b005_empirical_wave01_full_prompt.md`

### Candidate output files
Pattern:
- `<batch>_<family>_<part_or_wave>_candidates.json`

Examples:
- `b001_nlp4re_part1_candidates.json`
- `b002_empirical_wave01_candidates.json`

## Important note

The files in this directory are already execution-ready.

You do not need to manually assemble:
- family base prompt
- wrapper prompt
- run prompt

That assembly has already been captured in the final prompt files.