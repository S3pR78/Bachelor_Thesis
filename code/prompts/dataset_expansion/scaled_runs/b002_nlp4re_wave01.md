# Scaled Run Prompt — B002 NLP4RE Wave 01

Generate exactly 50 candidate dataset entries.

Selected family: `nlp4re`

For every item, set:
- `family` = `nlp4re`

Do not generate an `id` field.
IDs will be assigned later in a deterministic post-processing step.

Primary batch purpose:
- expand coverage of important query components for NLP4RE
- generate schema-faithful questions that naturally require component-sensitive SPARQL patterns
- increase coverage of useful operator and constraint combinations

Preferred focus:
- REGEX or string-based filtering where semantically justified
- LIMIT where the question naturally asks for a top result or restricted result set
- MIN / MAX / AVG where aggregation is clearly motivated
- NOT EXISTS where missing-information logic is natural
- comparison and constrained retrieval
- moderate multi-hop behavior

Preferred difficulty:
- mostly medium complexity
- some medium-to-high complexity
- avoid artificial complexity
- avoid operator use for its own sake

Important alignment rules:
- If a query returns a ranked or top-k list, phrase the question accordingly.
- Do not phrase a top-k query as if it returned a single strict maximum unless the query really enforces that.
- Use REGEX, LIMIT, MIN, AVG, MAX, or NOT EXISTS only when genuinely motivated by the question.
- Do not create artificial operator-driven questions just to satisfy the batch purpose.

Target answer_type distribution:
- around 14 `resource`
- around 14 `string`
- around 12 `number`
- around 10 `date`

Avoid overlap with:
- seed benchmark entries
- previously accepted or retained `b002_nlp4re` candidates
- earlier generated candidates in the same family
- simple paraphrases of already generated questions

Prefer:
- new combinations of constraints
- new component-sensitive reasoning patterns
- schema-faithful variety over superficial wording changes

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