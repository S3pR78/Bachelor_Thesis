# Wrapper Prompt — B002 Missing Query Components

## Purpose
Generate candidate dataset entries that increase coverage of missing or weak query components.

Primary target components:
- REGEX
- LIMIT
- MIN
- AVG

Secondary optional targets:
- BIND
- UNION
- NOT_EXISTS

## Use rule
This wrapper must be combined with exactly one family-specific base prompt from the repository.

## Hard constraints
1. Do not invent predicates, classes, template fields, or schema paths.
2. Only use query components when they are semantically justified.
3. Do not force artificial complexity just to include an operator.
4. Generate only English questions.
5. Avoid duplicates and near-duplicates.

## Desired behavior
- include comparison, temporal, and ranking-style questions where helpful
- prefer medium-to-high complexity overall
- ensure metadata reflects the actual query behavior
- `query_components` must match the SPARQL query exactly

## Required metadata behavior
Each item must contain full metadata.

Default generated metadata:
- `language = "en"`
- `human_or_generated = "generated"`
- `gold_status = "draft"`
- `review_status = "unreviewed"`
- `split = "train"`

## Output requirement
Return valid JSON only.