# Final Generation Prompt — benchmark_b001_empirical

You are generating candidate benchmark dataset entries for a Text-to-SPARQL system over the Open Research Knowledge Graph (ORKG).

Your task is to generate high-quality candidate question–SPARQL pairs for the `empirical_research_practice` family, using the ORKG Empirical Research Practice template faithfully and without inventing schema elements.

---

## Schema source in repo

The family schema grounding for this prompt comes from the repository files below.

Primary readable schema prompt:
- `code/prompts/empire_compass/generated/rendered/empirical_research_prompt.txt`

Family-to-template mapping:
- `code/prompts/empire_compass/config/prompt_runner_config.json`

Underlying template source:
- `code/prompts/empire_compass/templates/empirical_research_practice.json`

Use the rendered family prompt as the main schema-grounding source.
Use the config and template files only as supporting references for consistency.

---

## ORKG / Family grounding

You are working on the family:

- `family = "empirical_research_practice"`
- `source_dataset = "Hybrid_Empirical_Research"`

You must follow the ORKG Empirical Research Practice template and only use classes, predicates, nesting patterns, and schema paths that are valid for this family.

Do not invent:
- predicates
- classes
- template fields
- nested substructures
- unsupported schema shortcuts

Every generated SPARQL query must be consistent with the template-specific ORKG structure.

Use the required ORKG prefixes in every query.

---

## Batch purpose

This batch is designed to close answer-type coverage gaps in the benchmark candidate pool.

Generate exactly 10 candidate entries.

Required `answer_type` distribution:
- 3 entries with `"resource"`
- 3 entries with `"string"`
- 2 entries with `"number"`
- 2 entries with `"date"`

---

## Quality and diversity goals

The generated questions must:

- be written in English
- sound natural and academically plausible
- reflect realistic scholarly information needs
- not be near-duplicates of each other
- not copy known example questions verbatim
- vary in wording and structure
- remain answerable by the generated SPARQL query

Include diversity across:
- direct lookup questions
- typed lookup questions
- multi-hop questions
- temporal questions
- string-oriented questions

Try to include:
- 6 factoid questions
- 4 non-factoid questions

Try to include:
- 2 low complexity entries
- 5 medium complexity entries
- 3 high complexity entries

Include at least:
- 3 questions with explicit constraints such as year, venue, method type, contribution detail, comparison target, or nested template property
- 2 questions with clear temporal intent
- 2 questions with string-oriented intent
- 2 questions whose expected answer is numeric

---

## Query construction constraints

Every SPARQL query must:
- be faithful to the Empirical Research Practice family template
- be executable in principle
- match the question semantics
- use only valid ORKG schema elements for this family
- include the ORKG prefixes
- avoid unnecessary complexity

Across the 10 entries, include at least:
- 1 query using `STR`
- 4 queries using `FILTER`
- 4 queries using `OPTIONAL`
- 3 queries using `ORDER_BY`

If appropriate, use:
- `SELECT`
- `FILTER`
- `OPTIONAL`
- `STR`
- `ORDER_BY`

Do not force rare query shapes artificially.

---

## Metadata requirements

Each output entry must contain all of the following fields:

- `id`
- `source_id`
- `question`
- `gold_sparql`
- `family`
- `source_dataset`
- `language`
- `query_type`
- `query_shape`
- `answer_type`
- `complexity_level`
- `ambiguity_risk`
- `lexical_gap_risk`
- `hallucination_risk`
- `query_components`
- `special_types`
- `number_of_patterns`
- `human_or_generated`
- `gold_status`
- `review_status`
- `split`

Use these fixed metadata values:
- `family = "empirical_research_practice"`
- `source_dataset = "Hybrid_Empirical_Research"`
- `language = "en"`
- `human_or_generated = "generated"`
- `gold_status = "draft"`
- `review_status = "unreviewed"`
- `split = "train"`

Use these IDs exactly:

### id values
- `benchmark_b001_empirical_001`
- `benchmark_b001_empirical_002`
- `benchmark_b001_empirical_003`
- `benchmark_b001_empirical_004`
- `benchmark_b001_empirical_005`
- `benchmark_b001_empirical_006`
- `benchmark_b001_empirical_007`
- `benchmark_b001_empirical_008`
- `benchmark_b001_empirical_009`
- `benchmark_b001_empirical_010`

### source_id values
- `gen_b001_empirical_001`
- `gen_b001_empirical_002`
- `gen_b001_empirical_003`
- `gen_b001_empirical_004`
- `gen_b001_empirical_005`
- `gen_b001_empirical_006`
- `gen_b001_empirical_007`
- `gen_b001_empirical_008`
- `gen_b001_empirical_009`
- `gen_b001_empirical_010`

---

## Field interpretation rules

- `query_components` must reflect the actual SPARQL query.
- `special_types` must reflect the actual reasoning behavior.
- `query_shape` must be inferred from the actual graph structure.
- `number_of_patterns` should reflect the approximate number of relevant triple-pattern units.
- `complexity_level` must be justified by the actual query structure.
- `answer_type` must match the expected output shape of the query.

---

## Output format

Return only valid JSON.

Return a JSON array with exactly 10 objects.

Do not include:
- markdown fences
- explanations
- comments
- extra text before or after the JSON

---

## Output schema example

[
  {
    "id": "benchmark_b001_empirical_001",
    "source_id": "gen_b001_empirical_001",
    "question": "Which venue is reported for studies that investigate a specific empirical research practice under a given condition?",
    "gold_sparql": "PREFIX orkgr: <http://orkg.org/orkg/resource/> ...",
    "family": "empirical_research_practice",
    "source_dataset": "Hybrid_Empirical_Research",
    "language": "en",
    "query_type": "factoid",
    "query_shape": "tree",
    "answer_type": "resource",
    "complexity_level": "medium",
    "ambiguity_risk": "low",
    "lexical_gap_risk": "medium",
    "hallucination_risk": "medium",
    "query_components": ["SELECT", "FILTER", "OPTIONAL"],
    "special_types": ["typed_lookup", "multi_hop"],
    "number_of_patterns": 6,
    "human_or_generated": "generated",
    "gold_status": "draft",
    "review_status": "unreviewed",
    "split": "train"
  }
]