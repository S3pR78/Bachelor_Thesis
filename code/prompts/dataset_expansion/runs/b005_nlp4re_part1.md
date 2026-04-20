# Run Prompt — B005 NLP4RE Part 1

Generate exactly 5 candidate dataset entries.

Selected family: `nlp4re`
Selected source_dataset: `Hybrid_NLP4RE`

Use these id values exactly:
- `b005_nlp4re_001`
- `b005_nlp4re_002`
- `b005_nlp4re_003`
- `b005_nlp4re_004`
- `b005_nlp4re_005`

Use these source_id values exactly:
- `gen_b005_nlp4re_001`
- `gen_b005_nlp4re_002`
- `gen_b005_nlp4re_003`
- `gen_b005_nlp4re_004`
- `gen_b005_nlp4re_005`

Focus:
- difficult but valid questions
- ranking
- comparison
- multi_intent

Prefer:
- 1 factoid
- 4 non_factoid
- high complexity emphasis

Return valid JSON only.



Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.