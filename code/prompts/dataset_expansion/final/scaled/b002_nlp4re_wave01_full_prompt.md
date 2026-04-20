# Final Prompt — B002 NLP4RE Wave 01

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

## Batch objective

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

Only use query components when they are semantically justified.
Prefer medium-to-high complexity overall.

## Run-specific instructions

Generate exactly 10 candidate dataset entries.

Selected family: `nlp4re`
Selected source_dataset: `Hybrid_NLP4RE`

Wave id: `wave01`

Use these id values exactly:
- `b002_nlp4re_w01_001`
- `b002_nlp4re_w01_002`
- `b002_nlp4re_w01_003`
- `b002_nlp4re_w01_004`
- `b002_nlp4re_w01_005`
- `b002_nlp4re_w01_006`
- `b002_nlp4re_w01_007`
- `b002_nlp4re_w01_008`
- `b002_nlp4re_w01_009`
- `b002_nlp4re_w01_010`

Use these source_id values exactly:
- `gen_b002_nlp4re_w01_001`
- `gen_b002_nlp4re_w01_002`
- `gen_b002_nlp4re_w01_003`
- `gen_b002_nlp4re_w01_004`
- `gen_b002_nlp4re_w01_005`
- `gen_b002_nlp4re_w01_006`
- `gen_b002_nlp4re_w01_007`
- `gen_b002_nlp4re_w01_008`
- `gen_b002_nlp4re_w01_009`
- `gen_b002_nlp4re_w01_010`

Required component focus:
- at least 2 REGEX
- at least 2 LIMIT
- at least 2 MIN or AVG combined
- optionally BIND, UNION, or NOT_EXISTS

Prefer:
- 3 factoid
- 7 non_factoid
- medium to high complexity

Avoid overlap with:
- benchmark seed data
- b002 core runs
- previously generated candidate files

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
Return a JSON object with key `"items"` containing exactly 10 entries.
No markdown fences.
No explanation text.