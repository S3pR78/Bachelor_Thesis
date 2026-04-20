# Final Prompt — B001 Empirical Part 2

You are generating candidate dataset entries for a Text-to-SPARQL system over the Open Research Knowledge Graph (ORKG).

Your task is to generate high-quality candidate question–SPARQL pairs for the `empirical_research_practice` family, using the correct family template faithfully and without inventing schema elements.

## Schema source in repo

Primary readable schema prompt:
- `code/prompts/empire_compass/generated/rendered/empirical_research_prompt.txt`

Family-to-template mapping:
- `code/prompts/empire_compass/config/prompt_runner_config.json`

Underlying template source:
- `code/prompts/empire_compass/templates/empirical_research_practice.json`

Use the rendered family prompt as the main schema-grounding source.
Use the config and template files only as supporting references for consistency.

## Hard constraints

1. Do not invent predicates, classes, template fields, nested substructures, or schema paths.
2. Use only schema-valid ORKG paths for empirical_research_practice.
3. Generate only English questions.
4. Return candidate data only, not final benchmark gold data.
5. Avoid duplicates and near-duplicates.
6. Keep wording natural and academically plausible.
7. Ensure that `query_components` match the actual SPARQL query.
8. Ensure that `special_types` match actual reasoning behavior.
9. Ensure that `answer_type` matches the expected answer shape.

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

Selected family: `empirical_research_practice`
Selected source_dataset: `Hybrid_Empirical_Research`

Use these id values exactly:
- `b001_empirical_006`
- `b001_empirical_007`
- `b001_empirical_008`
- `b001_empirical_009`
- `b001_empirical_010`

Use these source_id values exactly:
- `gen_b001_empirical_006`
- `gen_b001_empirical_007`
- `gen_b001_empirical_008`
- `gen_b001_empirical_009`
- `gen_b001_empirical_010`

Target answer_type distribution:
- 1 resource
- 2 string
- 1 number
- 1 date

Prefer:
- 3 factoid
- 2 non_factoid
- mostly medium complexity

Avoid overlap with:
- benchmark seed data
- b001_empirical_part1 outputs
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