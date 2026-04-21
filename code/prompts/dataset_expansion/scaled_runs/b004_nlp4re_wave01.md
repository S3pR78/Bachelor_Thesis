# Scaled Run Prompt — B004 NLP4RE Wave 01

Generate exactly 50 candidate dataset entries.

Selected family: `nlp4re`

For every item, set:
- `family` = `nlp4re`

Do not generate an `id` field.
IDs will be assigned later in a deterministic post-processing step.

Primary batch purpose:
- expand NLP4RE-specific coverage without drifting into generic scholarly metadata questions
- generate template-anchored candidate questions with strong family grounding
- increase coverage of useful NLP4RE-specific template paths

Preferred focus:
- NLP task
- NLP task type
- NLP task output
- output type
- dataset
- data source
- data source type
- data source domain
- number of data sources
- data abstraction level
- data type
- data format
- natural language
- public availability
- license type
- dataset location
- annotation process
- agreement / annotator-related information

Preferred difficulty:
- mostly medium complexity
- some medium-to-high complexity
- avoid artificial complexity
- keep template specificity more important than superficial diversity

Target answer_type distribution:
- around 14 `resource`
- around 14 `string`
- around 12 `number`
- around 10 `date`

Avoid overlap with:
- seed benchmark entries
- previously accepted or retained `b004_nlp4re` candidates
- earlier generated candidates in the same family
- simple paraphrases of already generated questions

Prefer:
- new combinations of template constraints
- clearly NLP4RE-specific template content
- schema-faithful variety over generic paper metadata variation

Do not generate generic bibliographic-only questions based only on title, year, venue, or generic paper metadata.

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