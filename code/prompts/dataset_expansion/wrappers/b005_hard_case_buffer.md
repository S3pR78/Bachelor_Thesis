# Wrapper Prompt — B005 Hard Case Buffer

## Purpose
Generate difficult benchmark candidate entries that can serve as a reserve pool for later selection.

Primary focus:
- harder reasoning
- higher ambiguity risk
- more constrained or nested question structures
- stronger multi-hop behavior

## Use rule
This wrapper must be combined with exactly one family-specific base prompt from the repository.

## Hard constraints
1. Do not invent predicates, classes, template fields, or schema paths.
2. Use only schema-valid paths for the selected family.
3. Generate only English questions.
4. Avoid duplicates and near-duplicates.
5. Harder does not mean invalid or unnatural.

## Desired behavior
- prefer medium-to-high and high complexity
- include difficult but still answerable questions
- include comparison, ranking, multi_intent, missing_info, or temporal logic where appropriate
- ensure metadata truthfully reflects query behavior

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