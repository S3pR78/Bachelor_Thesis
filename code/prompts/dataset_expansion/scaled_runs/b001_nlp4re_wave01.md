# Scaled Run Prompt — B001 NLP4RE Wave 01

Generate exactly 50 candidate dataset entries.

Selected family: `nlp4re`

For every item, set:
- `family` = `nlp4re`

Do not generate an `id` field.
IDs will be assigned later in a deterministic post-processing step.

Primary batch purpose:
- expand answer-type coverage for NLP4RE
- generate broadly useful candidate questions
- maintain strong schema grounding

Target answer_type distribution:
- around 14 `resource`
- around 14 `string`
- around 12 `number`
- around 10 `date`

Preferred question styles:
- direct lookup
- constrained lookup
- temporal
- light comparison
- moderate multi-hop

Preferred difficulty:
- mostly medium complexity
- some low complexity
- a few higher-complexity but still natural cases

Avoid overlap with:
- seed benchmark entries
- previously accepted or retained `b001_nlp4re` candidates
- earlier generated candidates in the same family
- simple paraphrases of already generated questions

Prefer:
- new combinations of constraints
- new answer targets
- new template-path combinations
- schema-faithful variety over superficial wording changes

Keep the same grounding quality as in the stronger accepted NLP4RE batches.

Return only these fields for each item:
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.

`answer_type` must be one of:
- `resource`
- `string`
- `number`
- `date`

Do not use values such as:
- `factoid`
- `non_factoid`

Return valid JSON only.
Return a JSON object with key `"items"`.