# Final Prompt Template

Each final dataset expansion prompt should follow this structure.

---

## 1. Task introduction

You are generating candidate dataset entries for a Text-to-SPARQL system over the Open Research Knowledge Graph (ORKG).

Your task is to generate high-quality candidate question–SPARQL pairs for the selected family, using the correct family template faithfully and without inventing schema elements.

---

## 2. Schema source in repo

The family schema grounding for this prompt comes from the repository files below.

Primary readable schema prompt:
- family-specific rendered prompt file

Family-to-template mapping:
- `code/prompts/empire_compass/config/prompt_runner_config.json`

Underlying template source:
- family-specific template JSON file

Use the rendered family prompt as the main schema-grounding source.
Use the config and template files only as supporting references for consistency.

---

## 3. Hard constraints

1. Do not invent predicates, classes, template fields, nested substructures, or schema paths.
2. Use only schema-valid ORKG paths for the selected family.
3. Generate only English questions.
4. Return candidate data only, not final benchmark gold data.
5. Avoid duplicates and near-duplicates.
6. Keep wording natural and academically plausible.
7. Ensure that `query_components` match the actual SPARQL query.
8. Ensure that `special_types` match actual reasoning behavior.
9. Ensure that `answer_type` matches the expected answer shape.

---

## 4. Batch objective

Insert the batch-specific goal from the wrapper file.

---

## 5. Run-specific instructions

Insert:
- selected family
- selected source_dataset
- exact number of entries
- exact id list
- exact source_id list
- target distribution
- special focus constraints
- overlap avoidance rule

---

## 6. Metadata rules

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

---

## 7. Output format

Return only valid JSON.

Return either:
- a JSON object with key `"items"` containing the array
or
- a plain JSON array

No markdown fences.
No explanation text.
No commentary before or after the JSON.