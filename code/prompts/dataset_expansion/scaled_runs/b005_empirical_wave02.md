# Scaled Run Prompt — B005 Empirical Wave 02

Generate exactly 50 candidate dataset entries.

Selected family: `empirical_research_practice`

For every item, set:
- `family` = `empirical_research_practice`

Do not generate an `id` field.
IDs will be assigned later in a deterministic post-processing step.

Primary batch purpose:
- generate difficult reserve-pool candidates for empirical_research_practice
- focus on high-value hard cases that remain schema-faithful
- increase coverage of complex reasoning patterns

Preferred focus:
- comparison
- ranking
- temporal logic
- negation
- missing_info
- multi_intent
- stronger multi-hop behavior

Preferred difficulty:
- mostly medium-to-high and high complexity
- a few medium-complexity stabilizing cases
- no artificial complexity for its own sake

Target answer_type distribution:
- around 14 `resource`
- around 14 `string`
- around 12 `number`
- around 10 `date`

Avoid overlap with:
- seed benchmark entries
- previously accepted or retained `b005_empirical` candidates
- earlier generated candidates in the same family
- candidates from `b005_empirical_wave01`
- simple paraphrases of already generated questions

Prefer:
- new combinations of constraints
- harder but still natural question formulations
- genuinely different reasoning paths
- schema-faithful diversity over superficial lexical variation

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