# Run Prompt — B002 NLP4RE 

Generate exactly 10 candidate dataset entries.

Selected family: `nlp4re`

Use these id values exactly:
- `b002_nlp4re_001`
- `b002_nlp4re_002`
- `b002_nlp4re_003`
- `b002_nlp4re_004`
- `b002_nlp4re_005`
- `b002_nlp4re_006`
- `b002_nlp4re_007`
- `b002_nlp4re_008`
- `b002_nlp4re_009`
- `b002_nlp4re_010`


Required component focus:
- at least 3 REGEX
- at least 3 LIMIT
- at least 3 MIN or AVG
- at least 1 BIND or NOT_EXISTS

Prefer:
- 4 factoid
- 6 non_factoid
- medium to high complexity

Return valid JSON only.

Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.