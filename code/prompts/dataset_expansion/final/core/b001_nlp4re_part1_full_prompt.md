# Final Prompt — B001 NLP4RE Part 1

You are generating candidate dataset entries for a Text-to-SPARQL system over the Open Research Knowledge Graph (ORKG).

Your task is to generate high-quality candidate question–SPARQL pairs for the `nlp4re` family, using the correct family template faithfully and without inventing schema elements.

## Schema source in repo

Primary readable schema prompt:
- `code/prompts/empire_compass/generated/rendered/nlp4re_prompt.txt`

Family-to-template mapping:
- `code/prompts/empire_compass/config/prompt_runner_config.json`

Underlying template source:
- `code/prompts/empire_compass/templates/nlp4re-template.json`

Use the rendered family prompt as the main schema-grounding source.
Use the config and template files only as supporting references for consistency.

## Hard constraints

1. Do not invent predicates, classes, template fields, nested substructures, or schema paths.
2. Use only schema-valid ORKG paths for NLP4RE.
3. Generate only English questions.
4. Return candidate data only, not final benchmark gold data.
5. Avoid duplicates and near-duplicates.
6. Keep wording natural and academically plausible.
7. Ensure that `query_components` match the actual SPARQL query.
8. Ensure that `special_types` match actual reasoning behavior.
9. Ensure that `answer_type` matches the expected answer shape.

## Critical family-specific constraints

1. Every query must be clearly anchored in the NLP4RE family structure.
2. Every query must use at least one NLP4RE-specific template predicate or nested template path from the family grounding prompt.
3. Do not generate generic bibliographic-only queries.
4. Do not generate queries whose main logic is only based on:
   - `orkg:Paper`
   - `dcterms:title`
   - `dcterms:issued`
   - generic paper metadata without NLP4RE template grounding
5. “NLP4RE” must not appear only in the natural-language question. It must be reflected in the SPARQL structure.
6. Prefer questions about NLP4RE-specific aspects such as:
   - NLP task
   - NLP task type
   - NLP task output
   - output type
   - dataset
   - data source
   - data source type
   - number of data sources
   - data domain
   - data abstraction level
   - data type
   - data format
   - natural language
   - public availability
   - license type
   - dataset location
7. Prefer queries that connect the paper/contribution to template-specific properties instead of using title-keyword search as the main semantics.
8. Title or publication year filters may be used only as secondary constraints, not as the core meaning of the query.
9. At least one family-specific predicate path must be central to the answer.

## Dataset metadata vocabulary constraints

Use only the dataset vocabulary below.

### Allowed `query_shape` values
- `edge`
- `chain`
- `star`
- `tree`
- `cycle`
- `forest`
- `other`

Do not use values like:
- `conjunctive`
- `aggregation`

### Allowed `query_components` values
- `SELECT`
- `ASK`
- `COUNT`
- `FILTER`
- `REGEX`
- `STR`
- `ORDER_BY`
- `GROUP_BY`
- `HAVING`
- `LIMIT`
- `OPTIONAL`
- `UNION`
- `NOT_EXISTS`
- `MIN`
- `MAX`
- `AVG`
- `IF`
- `BIND`

Do not invent custom labels such as:
- `paper_entity`
- `title_literal`
- `keyword_filter`
- `resource_projection`

### Allowed `special_types` values
- `lookup`
- `typed_lookup`
- `multi_hop`
- `count`
- `aggregation`
- `ranking`
- `superlative`
- `temporal`
- `boolean`
- `negation`
- `missing_info`
- `comparison`
- `multi_intent`
- `string_operation`

Do not invent custom labels such as:
- `keyword_filter`
- `temporal_filter`
- `constraint_filter`
- `ordering`

## Batch objective

Generate candidate dataset entries that close answer-type coverage gaps.

Primary target answer types:
- resource
- string
- number
- date

Include a mix of factoid and non-factoid questions.
Prefer medium complexity overall.
Include direct and constrained questions where appropriate.

## Run-specific instructions

Generate exactly 5 candidate dataset entries.

Selected family: `nlp4re`
Selected source_dataset: `Hybrid_NLP4RE`

Use these id values exactly:
- `b001_nlp4re_001`
- `b001_nlp4re_002`
- `b001_nlp4re_003`
- `b001_nlp4re_004`
- `b001_nlp4re_005`

Use these source_id values exactly:
- `gen_b001_nlp4re_001`
- `gen_b001_nlp4re_002`
- `gen_b001_nlp4re_003`
- `gen_b001_nlp4re_004`
- `gen_b001_nlp4re_005`

Target answer_type distribution:
- 2 resource
- 1 string
- 1 number
- 1 date

Prefer:
- 3 factoid
- 2 non_factoid
- mostly medium complexity

Additional run requirements:
- at least 4 of the 5 questions must use clearly template-specific NLP4RE properties
- at most 1 question may use paper-level metadata such as title or year as a secondary filter
- at least 2 questions should involve a dataset-related NLP4RE property
- at least 2 questions should involve an NLP task, output type, or source-related property
- at least 1 question should involve a string-oriented answer or string operation without becoming a pure title lookup

Avoid overlap with:
- benchmark seed data
- existing generated candidate files

## Metadata rules

Use:
- `language = "en"`
- `human_or_generated = "generated"`
- `gold_status = "draft"`
- `review_status = "unreviewed"`
- `split = "train"`

Each entry must contain:
- `id`
- `source_id`
- `question`
- `gold_sparql`
- `family`
- `source_dataset`
- `language`
- `query_type`
- `query_shape`
- `answer_type`
- `complexity_level`
- `ambiguity_risk`
- `lexical_gap_risk`
- `hallucination_risk`
- `query_components`
- `special_types`
- `number_of_patterns`
- `human_or_generated`
- `gold_status`
- `review_status`
- `split`

## Output format

Return valid JSON only.
Return a JSON object with key `"items"` containing exactly 5 entries.
No markdown fences.
No explanation text.