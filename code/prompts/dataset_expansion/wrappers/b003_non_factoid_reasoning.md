# Wrapper Prompt — B003 Non-Factoid Reasoning

## Purpose
Generate candidate dataset entries with stronger non-factoid and reasoning-heavy behavior.

Primary target special types:
- comparison
- temporal
- multi_intent
- negation
- missing_info

## Use rule
This wrapper must be combined with exactly one family-specific base prompt from the repository.

## Hard constraints
1. Do not invent predicates, classes, template fields, or schema paths.
2. Use only schema-valid paths for the selected family.
3. Generate only English questions.
4. Avoid duplicates and near-duplicates.
5. Do not create fake complexity unsupported by the family template.

## Desired behavior
- prefer non-factoid questions
- include comparison or contrastive wording
- include temporal conditions where meaningful
- include some questions that require missing-info or negation logic
- prefer medium-to-high complexity

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