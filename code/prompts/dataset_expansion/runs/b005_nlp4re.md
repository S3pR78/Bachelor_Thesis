# Run Prompt — B005 NLP4RE

Generate exactly 10 candidate dataset entries.

Selected family: `nlp4re`

For every item, set:
- `family` = `nlp4re`

Use these id values exactly:
- `b005_nlp4re_001`
- `b005_nlp4re_002`
- `b005_nlp4re_003`
- `b005_nlp4re_004`
- `b005_nlp4re_005`
- `b005_nlp4re_006`
- `b005_nlp4re_007`
- `b005_nlp4re_008`
- `b005_nlp4re_009`
- `b005_nlp4re_010`

Use each `id` exactly once.
Do not repeat or reuse any `id`.
The output must contain exactly 10 items with 10 unique ids.

Focus:
- difficult but valid questions
- ranking
- comparison
- multi_intent
- missing_info
- temporal
- negation
- strongly NLP4RE-specific content

Prefer:
- 4 factoid
- 6 non_factoid
- high complexity emphasis
- hard but schema-faithful NLP4RE questions over generic scholarly metadata questions

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