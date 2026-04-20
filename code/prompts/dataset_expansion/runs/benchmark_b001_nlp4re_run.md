# Run File — benchmark_b001_nlp4re

## Use with
- Base prompt: `code/prompts/empire_compass/generated/rendered/nlp4re_prompt.txt`
- Batch wrapper: `code/prompts/dataset_expansion/benchmark_b001_answer_type_gaps_prompt.md`

## Final run instruction block

Generate exactly 10 candidate dataset entries.

Selected family: `nlp4re`
Selected source_dataset: `Hybrid_NLP4RE`

Use these ID values exactly:
- `benchmark_b001_nlp4re_001`
- `benchmark_b001_nlp4re_002`
- `benchmark_b001_nlp4re_003`
- `benchmark_b001_nlp4re_004`
- `benchmark_b001_nlp4re_005`
- `benchmark_b001_nlp4re_006`
- `benchmark_b001_nlp4re_007`
- `benchmark_b001_nlp4re_008`
- `benchmark_b001_nlp4re_009`
- `benchmark_b001_nlp4re_010`

Use these source_id values exactly:
- `gen_b001_nlp4re_001`
- `gen_b001_nlp4re_002`
- `gen_b001_nlp4re_003`
- `gen_b001_nlp4re_004`
- `gen_b001_nlp4re_005`
- `gen_b001_nlp4re_006`
- `gen_b001_nlp4re_007`
- `gen_b001_nlp4re_008`
- `gen_b001_nlp4re_009`
- `gen_b001_nlp4re_010`

Required answer_type distribution:
- 3 entries with `"resource"`
- 3 entries with `"string"`
- 2 entries with `"number"`
- 2 entries with `"date"`

Recommended query_type mix:
- 6 factoid
- 4 non_factoid

Recommended complexity mix:
- 2 low
- 5 medium
- 3 high

Required diversity constraints:
- do not produce near-duplicate questions
- vary wording style across entries
- include at least 3 questions with explicit constraints such as year, venue, source type, output type, dataset property, or nested template detail
- include at least 2 questions with clear temporal intent
- include at least 2 questions with string-oriented intent
- include at least 2 questions whose expected answer is a numeric value
- include at least 1 query using `STR`
- include at least 4 queries using `FILTER`
- include at least 4 queries using `OPTIONAL`
- include at least 3 queries using `ORDER_BY`

Metadata rules:
- `language = "en"`
- `human_or_generated = "generated"`
- `gold_status = "draft"`
- `review_status = "unreviewed"`
- `split = "train"`

Return only a valid JSON array.
Do not include commentary.
Do not include markdown fences.