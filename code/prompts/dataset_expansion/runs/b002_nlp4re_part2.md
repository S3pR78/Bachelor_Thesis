# Run Prompt — B002 NLP4RE Part 2

Generate exactly 5 candidate dataset entries.

Selected family: `nlp4re`
Selected source_dataset: `Hybrid_NLP4RE`

Use these id values exactly:
- `b002_nlp4re_006`
- `b002_nlp4re_007`
- `b002_nlp4re_008`
- `b002_nlp4re_009`
- `b002_nlp4re_010`

Use these source_id values exactly:
- `gen_b002_nlp4re_006`
- `gen_b002_nlp4re_007`
- `gen_b002_nlp4re_008`
- `gen_b002_nlp4re_009`
- `gen_b002_nlp4re_010`

Required component focus:
- at least 1 REGEX
- at least 1 LIMIT
- at least 1 MIN
- at least 1 AVG
- optionally BIND or NOT_EXISTS

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