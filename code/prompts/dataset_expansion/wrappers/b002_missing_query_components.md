# Wrapper Prompt — B002 Missing Query Components

## Purpose
Generate candidate dataset entries that increase coverage of missing or weak query components.

Primary target components:
- REGEX
- LIMIT
- MIN
- AVG

Secondary optional targets:
- BIND
- UNION
- NOT_EXISTS

## Use rule
This wrapper must be combined with exactly one family-specific base prompt from the repository.

## Hard constraints
1. Do not invent predicates, classes, template fields, or schema paths.
2. Only use query components when they are semantically justified.
3. Do not force artificial complexity just to include an operator.
4. Generate only English questions.
5. Avoid duplicates and near-duplicates.
6. Keep question wording natural and academically plausible.
7. Every query must use at least one family-specific template predicate or template path from the selected family prompt.
8. Do not generate generic bibliographic-only queries based only on title, year, or generic paper metadata.
9. Use REGEX, LIMIT, MIN, AVG, BIND, UNION, or NOT_EXISTS only when semantically justified.
10. Do not insert a target component artificially if it makes the question unnatural.
11. `answer_type` must be one of:
   - `resource`
   - `string`
   - `number`
   - `date`

   Do not use values such as:
   - `factoid`
   - `non_factoid`

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
6. Use the family anchor pattern consistently. For NLP4RE, prefer the family grounding structure where the paper links to a contribution and the contribution carries the template class. Do not assign the template class directly to the paper unless the family schema explicitly requires it.


Prefer projecting only the minimal variables needed to answer the question.
Do not include `?paper` or `?paperLabel` unless the question explicitly asks for papers.

## Desired behavior
- include comparison, temporal, and ranking-style questions where helpful
- prefer medium-to-high complexity overall
- ensure metadata reflects the actual query behavior
- `query_components` must match the SPARQL query exactly

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