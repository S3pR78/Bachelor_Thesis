# Scaled Run Prompt — B003 Empirical Wave 01

Generate exactly 50 candidate dataset entries.

Selected family: `empirical_research_practice`

For every item, set:
- `family` = `empirical_research_practice`

Do not generate an `id` field.
IDs will be assigned later in a deterministic post-processing step.

Primary batch purpose:
- expand non-factoid reasoning coverage for empirical_research_practice
- generate schema-faithful questions with stronger reasoning behavior
- increase useful variety beyond simple lookup questions

Preferred focus:
- comparison
- temporal constraints
- negation
- missing_info
- multi_intent
- moderate ranking where natural
- stronger multi-hop behavior

Preferred difficulty:
- mostly medium and medium-to-high complexity
- some high-complexity cases
- avoid artificial complexity

Target answer_type distribution:
- around 14 `resource`
- around 14 `string`
- around 12 `number`
- around 10 `date`

Avoid overlap with:
- seed benchmark entries
- previously accepted or retained `b003_empirical` candidates
- earlier generated candidates in the same family
- simple paraphrases of already generated questions

Prefer:
- new combinations of constraints
- new reasoning paths
- schema-faithful variety over superficial wording changes
- natural but clearly non-trivial questions

Keep the same grounding quality as in the stronger accepted empirical batches.

Return only these fields for each item:
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