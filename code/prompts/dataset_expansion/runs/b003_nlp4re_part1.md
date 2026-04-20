# Run Prompt — B003 NLP4RE Part 1

Generate exactly 5 candidate dataset entries.

Selected family: `nlp4re`
Selected source_dataset: `Hybrid_NLP4RE`

Use these id values exactly:
- `b003_nlp4re_001`
- `b003_nlp4re_002`
- `b003_nlp4re_003`
- `b003_nlp4re_004`
- `b003_nlp4re_005`

Use these source_id values exactly:
- `gen_b003_nlp4re_001`
- `gen_b003_nlp4re_002`
- `gen_b003_nlp4re_003`
- `gen_b003_nlp4re_004`
- `gen_b003_nlp4re_005`

Required special type focus:
- comparison
- temporal
- multi_intent

Prefer:
- 1 factoid
- 4 non_factoid
- medium to high complexity

Return valid JSON only.



Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.