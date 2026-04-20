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
7. Every query must use at least one family-specific template predicate or template path from the selected family prompt.
8. Do not generate generic bibliographic-only queries based only on title, year, or generic paper metadata.

### Question-answer alignment rules

1. The natural-language question must match the projected variables in the SPARQL query.
2. If the query returns both `?paper` and an answer variable, the question must explicitly ask for the paper together with the answer.
3. If the question asks only for the answer value, do not project `?paper` unless it is required by the question.
4. Avoid underspecified wording such as:
   - "the study"
   - "the dataset"
   - "the paper"
   unless the question includes a clear identifying constraint.
5. Prefer formulations such as:
   - "Which papers ..."
   - "For which papers ..."
   - "Which datasets ..."
   - "Which natural languages are reported for datasets ..."

Prefer projecting only the minimal variables needed to answer the question.
Do not include `?paper` or `?paperLabel` unless the question explicitly asks for papers.

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

### Answer type rule

`answer_type` must reflect the actual expected answer shape:
- `resource` if the query returns ORKG resources/entities
- `string` if the query returns labels or text values
- `number` if the query returns counts or numeric literals
- `date` if the query returns dates or year-like temporal values

## Output requirement
Return valid JSON only.
Return a JSON object with key `"items"`.