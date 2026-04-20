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
6. Keep question wording natural and academically plausible.
7. Every query must use at least one family-specific template predicate or template path from the selected family prompt.
8. Do not generate generic bibliographic-only queries based only on title, year, or generic paper metadata.
9. If a target component such as REGEX, LIMIT, MIN, AVG, BIND, UNION, or NOT_EXISTS is requested, use it only when it is semantically justified by the question.
10. Harder questions must still remain natural, answerable, and family-specific.
Do not increase difficulty by making the question underspecified.

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
- prefer medium-to-high and high complexity
- include difficult but still answerable questions
- include comparison, ranking, multi_intent, missing_info, or temporal logic where appropriate
- ensure metadata truthfully reflects query behavior

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