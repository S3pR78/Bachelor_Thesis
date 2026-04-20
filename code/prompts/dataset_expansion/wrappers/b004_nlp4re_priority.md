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
6. Keep question wording natural and academically plausible.
7. Every query must use at least one family-specific template predicate or template path from the selected family prompt.
8. Do not generate generic bibliographic-only queries based only on title, year, or generic paper metadata.
9. Every query must be strongly anchored in the NLP4RE family template.
Do not generate generic ORKG paper metadata questions.

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
- cover a useful mix of factoid and non-factoid questions
- include direct lookup, constrained lookup, comparison, and temporal questions
- keep schema faithfulness more important than diversity for its own sake
- prefer medium complexity, with some higher-complexity cases


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
Return a JSON object with key `"items"`..