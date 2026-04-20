# Run Prompt — B001 Empirical Part 1

Generate exactly 5 candidate dataset entries.

Selected family: `empirical_research_practice`

Use these id values exactly:
- `b001_empirical_001`
- `b001_empirical_002`
- `b001_empirical_003`
- `b001_empirical_004`
- `b001_empirical_005`
- `b001_empirical_006`
- `b001_empirical_007`
- `b001_empirical_008`
- `b001_empirical_009`
- `b001_empirical_010`


Target answer_type distribution:
- 3 resource
- 3 string
- 2 number
- 2 date

Prefer:
- 6 factoid
- 4 non_factoid
- mostly medium complexity

Return valid JSON only.

Return only these fields for each item:
- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

Do not include any other metadata fields.