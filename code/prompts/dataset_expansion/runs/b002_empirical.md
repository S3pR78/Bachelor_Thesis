# Run Prompt — B002 Empirical

Generate exactly 10 candidate dataset entries.

Selected family: `empirical_research_practice`

Use these id values exactly:
- `b002_empirical_001`
- `b002_empirical_002`
- `b002_empirical_003`
- `b002_empirical_004`
- `b002_empirical_005`
- `b002_empirical_006`
- `b002_empirical_007`
- `b002_empirical_008`
- `b002_empirical_009`
- `b002_empirical_010`


Required component focus:
- at least 3 REGEX
- at least 3 LIMIT
- at least 2 MIN or AVG
- at least 2 UNION or NOT_EXISTS

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