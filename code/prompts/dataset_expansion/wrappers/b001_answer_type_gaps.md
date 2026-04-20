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

## Output fields

Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not generate any other metadata fields.
Additional metadata will be added later in a separate enrichment step.

## Output requirement
Return valid JSON only.
Return a JSON object with key `"items"`.