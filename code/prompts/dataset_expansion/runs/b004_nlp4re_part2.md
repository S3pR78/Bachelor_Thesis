# Run Prompt — B004 NLP4RE Part 2

Generate exactly 5 candidate dataset entries.

Selected family: `nlp4re`
Selected source_dataset: `Hybrid_NLP4RE`

Use these id values exactly:
- `b004_nlp4re_006`
- `b004_nlp4re_007`
- `b004_nlp4re_008`
- `b004_nlp4re_009`
- `b004_nlp4re_010`

Use these source_id values exactly:
- `gen_b004_nlp4re_006`
- `gen_b004_nlp4re_007`
- `gen_b004_nlp4re_008`
- `gen_b004_nlp4re_009`
- `gen_b004_nlp4re_010`

Focus:
- stronger multi-hop
- comparison
- temporal
- multi_intent

Prefer:
- 2 factoid
- 3 non_factoid
- medium to high complexity

Return valid JSON only.


Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.