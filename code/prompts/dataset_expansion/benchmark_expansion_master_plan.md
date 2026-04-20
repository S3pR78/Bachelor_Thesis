# Benchmark Expansion Master Plan

## Goal

Build a controlled dataset expansion workflow for benchmark and fine-tuning candidate generation.

The expansion should:
- preserve natural dataset skew where justified
- close important coverage gaps
- keep generated candidate data separate from reviewed benchmark data
- stay grounded in the family-specific ORKG prompts already available in the repository

## Family grounding sources

Use these existing family prompts as the schema-grounding base:

- `code/prompts/empire_compass/generated/rendered/nlp4re_prompt.txt`
- `code/prompts/empire_compass/generated/rendered/empirical_research_prompt.txt`

Supporting schema sources:
- `code/prompts/empire_compass/config/prompt_runner_config.json`
- `code/prompts/empire_compass/templates/nlp4re-template.json`
- `code/prompts/empire_compass/templates/empirical_research_practice.json`

## Prompt workflow

The prompt system is split into three layers:

1. Wrapper prompt
   - defines the batch objective
   - defines quality constraints
   - defines metadata expectations

2. Run prompt
   - defines family
   - defines part1/part2 split
   - defines exact ids and source_ids
   - defines count and local distribution

3. Final prompt
   - ready-to-run assembled prompt used by the generation runner

## Candidate output location

Generated files must be written to:

- `code/data/dataset/expansion/candidates/`

Generated files are candidate data only and must not be treated as final benchmark gold data before review.


## Two-layer expansion strategy

The expansion workflow is divided into two layers.

### Layer A — Core benchmark expansion
Purpose:
- create a controlled, high-quality core set
- close the most important coverage gaps
- validate prompt behavior and schema faithfulness
- generate a manageable number of reviewable candidates

This layer uses:
- `part1`
- `part2`

Expected size:
- about 90 to 150 candidate entries across all defined core runs

### Layer B — Scaled fine-tuning expansion
Purpose:
- generate a much larger candidate pool for fine-tuning
- reuse the validated batch logic from the core layer
- scale generation through repeated waves with controlled variation

This layer uses:
- `wave01`
- `wave02`
- `wave03`
- and later additional waves as needed

Expected size:
- about 500 to 1500 candidate entries depending on the number of waves

## Interpretation of current run files

The current `part1` and `part2` files are core runs only.
They are not intended to be the full expansion volume.

They serve as:
- controlled benchmark-oriented expansion
- validation of batch logic
- seed generation patterns for later scaling

## Scaled run naming convention

Pattern:
- `<batch>_<family>_waveXX.md`

Examples:
- `b001_nlp4re_wave01.md`
- `b001_empirical_wave03.md`
- `b004_nlp4re_wave05.md`

## Scaled final prompt naming convention

Pattern:
- `<batch>_<family>_waveXX_full_prompt.md`

Examples:
- `b002_nlp4re_wave02_full_prompt.md`
- `b005_empirical_wave04_full_prompt.md`

## Scaled candidate output naming convention

Pattern:
- `<batch>_<family>_waveXX_candidates.json`

Examples:
- `b003_nlp4re_wave01_candidates.json`
- `b004_nlp4re_wave06_candidates.json`

## Scaling principle

Scale waves must:
- preserve the family-specific schema grounding
- preserve the batch objective
- vary question wording and constraints
- avoid duplicates against benchmark seed, core runs, and prior waves
- remain candidate data until validation

## Practical scaling plan

Suggested first target:
- finish all core runs first
- then add wave01 to wave03 for B001, B002, B003, and B005
- then add more NLP4RE-focused waves for B004

This already produces several hundred candidates while preserving structure.


## Batch overview

### B001 — Answer type gaps
Purpose:
- add missing or underrepresented answer types
- focus on `resource`, `string`, `number`, `date`

Families:
- nlp4re
- empirical_research_practice

Split:
- part1
- part2

### B002 — Missing query components
Purpose:
- increase usage of currently missing or weak query components
- focus on `REGEX`, `LIMIT`, `MIN`, `AVG`
- optionally increase `BIND`, `UNION`, `NOT_EXISTS`

Families:
- nlp4re
- empirical_research_practice

Split:
- part1
- part2

### B003 — Non-factoid reasoning
Purpose:
- increase reasoning-heavy and non-factoid questions
- focus on `comparison`, `temporal`, `multi_intent`, `negation`, `missing_info`

Families:
- nlp4re
- empirical_research_practice

Split:
- part1
- part2

### B004 — NLP4RE priority
Purpose:
- expand NLP4RE specifically without forcing equality with empirical research
- keep focus on schema-faithful NLP4RE coverage growth

Families:
- nlp4re only

Split:
- part1
- part2

### B005 — Hard case buffer
Purpose:
- generate difficult benchmark candidates
- create a reserve pool of harder questions for later review and selection

Families:
- nlp4re
- empirical_research_practice


## Required prompt files

### Wrappers
- `code/prompts/dataset_expansion/wrappers/b001_answer_type_gaps.md`
- `code/prompts/dataset_expansion/wrappers/b002_missing_query_components.md`
- `code/prompts/dataset_expansion/wrappers/b003_non_factoid_reasoning.md`
- `code/prompts/dataset_expansion/wrappers/b004_nlp4re_priority.md`
- `code/prompts/dataset_expansion/wrappers/b005_hard_case_buffer.md`

### Run prompts
- one run prompt per batch/family/part

### Final prompts
- one final prompt per batch/family/part
- each final prompt is the execution-ready version

## Naming convention

### Run prompts
Pattern:
- `<batch>_<family>_<part>.md`

Examples:
- `b001_nlp4re_part1.md`
- `b001_empirical_part2.md`

### Final prompts
Pattern:
- `<batch>_<family>_<part>_full_prompt.md`

Examples:
- `b001_nlp4re_part1_full_prompt.md`
- `b003_empirical_part2_full_prompt.md`

### Candidate outputs
Pattern:
- `<batch>_<family>_<part>_candidates.json`

Examples:
- `b001_nlp4re_part1_candidates.json`
- `b005_empirical_part2_candidates.json`

## Execution order

Recommended order:

1. b001_nlp4re_part1
2. b001_nlp4re_part2
3. b001_empirical_part1
4. b001_empirical_part2
5. b002_nlp4re_part1
6. b002_nlp4re_part2
7. b002_empirical_part1
8. b002_empirical_part2
9. b003_nlp4re_part1
10. b003_nlp4re_part2
11. b003_empirical_part1
12. b003_empirical_part2
13. b004_nlp4re_part1
14. b004_nlp4re_part2
15. b005_nlp4re_part1
16. b005_nlp4re_part2
17. b005_empirical_part1
18. b005_empirical_part2

## Validation rule

After every generated candidate file:

1. run duplicate checking
2. inspect schema warnings
3. inspect suspicious predicates
4. review at least a sample manually
5. only then continue to the next batch


## Current active generation format

The model must currently generate only:
- id
- question
- gold_sparql
- family
- answer_type

All remaining metadata is added later in a separate enrichment step.

## Important note

The family prompts are the schema-grounding source.
The wrapper prompts do not replace them.
The run prompts do not replace them.
The final prompt combines the family grounding with batch and run constraints.

## Current active prompt path

Use:
- family base prompts
- wrappers
- runs / scaled_runs
- assembly tool

Do not rely on hand-maintained final prompt files as the primary workflow.


