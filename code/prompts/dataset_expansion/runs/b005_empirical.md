# Run Prompt — B005 Empirical

Generate exactly 10 candidate dataset entries.

Selected family: `empirical_research_practice`

Use these id values exactly:
- `b005_empirical_001`
- `b005_empirical_002`
- `b005_empirical_003`
- `b005_empirical_004`
- `b005_empirical_005`
- `b005_empirical_006`
- `b005_empirical_007`
- `b005_empirical_008`
- `b005_empirical_009`
- `b005_empirical_010`


Focus:
- difficult but valid questions
- ranking
- comparison
- multi_intent
- missing_info
- temporal
- ranking
- negation

Prefer:
- 3 factoid
- 7 non_factoid
- high complexity emphasis

Return valid JSON only.


Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.