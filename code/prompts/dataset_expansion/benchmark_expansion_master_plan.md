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

Split:
- part1
- part2

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

## Metadata rule for generated candidates

Generated candidates should start with:

- `human_or_generated = "generated"`
- `gold_status = "draft"`
- `review_status = "unreviewed"`
- `split = "train"`

## Important note

The family prompts are the schema-grounding source.
The wrapper prompts do not replace them.
The run prompts do not replace them.
The final prompt combines the family grounding with batch and run constraints.