# Run Prompt — B004 NLP4RE

Generate exactly 10 candidate dataset entries.

Selected family: `nlp4re`

For every item, set:
- `family` = `nlp4re`

Use these id values exactly:
- `b004_nlp4re_001`
- `b004_nlp4re_002`
- `b004_nlp4re_003`
- `b004_nlp4re_004`
- `b004_nlp4re_005`
- `b004_nlp4re_006`
- `b004_nlp4re_007`
- `b004_nlp4re_008`
- `b004_nlp4re_009`
- `b004_nlp4re_010`

Use each `id` exactly once.
Do not repeat or reuse any `id`.
The output must contain exactly 10 items with 10 unique ids.

Focus:
- direct lookup
- constrained lookup
- temporal
- comparison
- stronger multi-hop
- multi_intent
- clearly NLP4RE-specific template content

Prefer:
- 6 factoid
- 4 non_factoid
- mostly medium complexity
- a few higher-complexity cases
- genuinely template-anchored NLP4RE questions over generic scholarly metadata questions

Return only these fields for each item:
- `id`
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