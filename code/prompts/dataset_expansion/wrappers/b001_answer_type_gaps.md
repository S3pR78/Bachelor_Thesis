# Wrapper Prompt — B001 Answer Type Gaps

## Purpose
Generate candidate dataset entries that close answer-type coverage gaps.

Primary target answer types:
- resource
- string
- number
- date

## Use rule
This wrapper must be combined with exactly one family-specific base prompt from the repository.

## Hard constraints
1. Do not invent predicates, classes, template fields, or schema paths.
2. Use only the schema that is valid for the selected family.
3. Generate only English questions.
4. Return only candidate data, not final benchmark gold data.
5. Avoid duplicates and near-duplicates.
6. Keep question wording natural and academically plausible.

## Desired behavior
- include a mix of factoid and non-factoid questions
- include direct and constrained questions
- include a few temporal or string-focused cases where appropriate
- prefer medium complexity overall

## Required metadata behavior
Each item must contain full metadata.

Default generated metadata:
- `language = "en"`
- `human_or_generated = "generated"`
- `gold_status = "draft"`
- `review_status = "unreviewed"`
- `split = "train"`

## Output requirement
Return valid JSON only.