# Prompt Assembly Template

Use the following structure to assemble a final generation prompt.

---

## Part 1 — Family base prompt

Paste exactly one of:

- `code/prompts/empire_compass/generated/rendered/nlp4re_prompt.txt`
- `code/prompts/empire_compass/generated/rendered/empirical_research_prompt.txt`

---

## Part 2 — Batch wrapper prompt

Paste one batch wrapper from this directory, for example:

- `benchmark_b001_answer_type_gaps_prompt.md`

---

## Part 3 — Run-specific instruction block

Append a final short control block like this:

Generate exactly 10 candidate dataset entries.

Selected family: `nlp4re`
Selected source_dataset: `Hybrid_NLP4RE`

Use these ID patterns:
- `id`: `benchmark_b001_nlp4re_001` to `benchmark_b001_nlp4re_010`
- `source_id`: `gen_b001_nlp4re_001` to `gen_b001_nlp4re_010`

Additional run constraints:
- keep questions semantically diverse
- avoid near-duplicate wording
- prefer medium complexity overall
- include at least 3 clearly constrained questions
- return only valid JSON array output

---

## Example family switch

For empirical research practice, change the final run block to:

Selected family: `empirical_research_practice`
Selected source_dataset: `Hybrid_Empirical_Research`

Use these ID patterns:
- `id`: `benchmark_b001_empirical_001` to `benchmark_b001_empirical_010`
- `source_id`: `gen_b001_empirical_001` to `gen_b001_empirical_010`