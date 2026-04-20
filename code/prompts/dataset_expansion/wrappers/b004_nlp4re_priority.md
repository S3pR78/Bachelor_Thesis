# Wrapper Prompt — B004 NLP4RE Priority

## Purpose
Generate additional candidate dataset entries specifically for NLP4RE.

This batch exists to expand NLP4RE coverage without forcing equality with empirical_research_practice.

## Use rule
This wrapper must only be used with the NLP4RE family base prompt.

## Hard constraints
1. Do not invent predicates, classes, template fields, or schema paths.
2. Use only schema-valid NLP4RE paths.
3. Generate only English questions.
4. Avoid duplicates and near-duplicates.
5. Keep the questions realistic and relevant to the NLP4RE template.

## Desired behavior
- cover a useful mix of factoid and non-factoid questions
- include direct lookup, constrained lookup, comparison, and temporal questions
- keep schema faithfulness more important than diversity for its own sake
- prefer medium complexity, with some higher-complexity cases

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