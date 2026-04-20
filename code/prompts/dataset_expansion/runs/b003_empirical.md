# Run Prompt — B003 Empirical

Generate exactly 10 candidate dataset entries.

Selected family: `empirical_research_practice`

Use these id values exactly:
- `b003_empirical_001`
- `b003_empirical_002`
- `b003_empirical_003`
- `b003_empirical_004`
- `b003_empirical_005`
- `b003_empirical_006`
- `b003_empirical_007`
- `b003_empirical_008`
- `b003_empirical_009`
- `b003_empirical_010`


Required special type focus:
- comparison
- temporal
- multi_intent
- negation
- missing_info
- multi_intent

Prefer:
- 3 factoid
- 7 non_factoid
- medium to high complexity

Return valid JSON only.


Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.