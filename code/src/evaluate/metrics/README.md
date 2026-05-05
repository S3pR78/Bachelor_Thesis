# Evaluation Metrics Documentation

This document describes the evaluation metrics implemented in the Text-to-SPARQL benchmark pipeline for ORKG template questions.

The goal of the evaluation is not only to check whether a model returns a syntactically valid SPARQL query, but also to understand **where** and **why** a prediction fails. Therefore, the metrics are grouped into several complementary categories:

1. output extraction and query form checks
2. query execution checks
3. answer-based metrics
4. relaxed value-only answer metrics
5. query text and structure metrics
6. KG-reference grounding metrics
7. local-memory URI hallucination diagnostics
8. PGMR-lite-specific diagnostics
9. post-hoc LLM judge outputs
10. primary error categorization

The metrics are intentionally modular. Each metric is implemented in its own module under:

```text
code/src/evaluate/metrics/
```

and integrated into the evaluation pipeline through:

```text
code/src/evaluate/metric_runner.py
```

The summary aggregation is implemented in:

```text
code/src/evaluate/summary.py
```

and the interactive viewer is located at:

```text
code/tools/review/benchmark_summary_app.py
```

---

## 1. Design Goals

The evaluation design follows four main goals.

### 1.1 Separate failure modes

A wrong prediction can fail for different reasons:

- the model output does not contain a SPARQL query
- the query form is unsupported or mismatched
- the query cannot be executed
- the query executes but returns the wrong answer
- the query uses wrong ORKG predicates or classes
- the query contains hallucinated ORKG identifiers
- a PGMR-lite mapping leaves placeholders unresolved

The metric suite is designed to make these failure modes visible instead of collapsing everything into one final score.

### 1.2 Distinguish answer correctness from query similarity

Two SPARQL queries can be textually different but return the same answer. Conversely, two queries can look similar but differ in a crucial predicate ID.

Therefore, the pipeline evaluates both:

- executed answers
- query text and structure
- ORKG identifier usage

### 1.3 Support both direct SPARQL and PGMR-lite evaluation

The project evaluates direct SPARQL generation as well as PGMR-lite, where a semantic intermediate representation is mapped to executable SPARQL.

Some metrics are general and apply to both modes. Other metrics, such as `pgmr_unmapped_placeholders`, are only meaningful for PGMR-lite runs.

### 1.4 Keep the implementation modular

Each metric is implemented in a small, testable module. This makes the evaluation easier to maintain, explain, and extend.

---

## 2. Metric Overview

| Group | Metrics |
|---|---|
| Extraction and form | `query_extracted`, `supported_query_form`, `query_form_match` |
| Execution | `prediction_execution_success`, `gold_execution_success` |
| Strict answer-based | `answer_exact_match`, `answer_precision_recall_f1` |
| Value-only answer-based | `answer_value_exact_match`, `answer_value_precision_recall_f1` |
| Query text | `query_normalized_exact_match`, `query_bleu`, `query_rouge1_f1`, `query_rouge2_f1`, `query_rougeL_f1` |
| Query structure | `sparql_structure_match` |
| KG references | `kg_ref_match`, `predicate_ref_match`, `class_ref_match`, `resource_ref_match` |
| Hallucination | `uri_hallucination` |
| PGMR-lite | `pgmr_unmapped_placeholders`, `pgmr_rouge1_f1`, `pgmr_rouge2_f1`, `pgmr_rougeL_f1` |
| Post-hoc semantic judge | `intent_score`, `schema_score`, `projection_score`, `constraint_score`, `aggregation_score`, `overall_score`, `verdict` |
| Diagnostics | `primary_error_category` |

---

## 3. Extraction and Query Form Metrics

### `query_extracted`

Checks whether a SPARQL query could be extracted from the model output.

**Interpretation:**

- `1.0`: a query was extracted
- `0.0`: no query was extracted

This metric separates formatting/extraction failures from later execution and answer failures.

---

### `supported_query_form`

Checks whether the extracted query has a supported SPARQL query form.

Common supported forms are:

- `SELECT`
- `ASK`

Unsupported forms are marked as not comparable for later execution-based metrics.

---

### `query_form_match`

Checks whether the predicted query form matches the gold query form.

Example:

```text
prediction: SELECT
gold:       SELECT
result:     match
```

Example mismatch:

```text
prediction: ASK
gold:       SELECT
result:     mismatch
```

This is a query-level metric and does not depend on endpoint execution.

---

## 4. Execution Metrics

### `prediction_execution_success`

Checks whether the predicted SPARQL query can be executed successfully against the configured ORKG SPARQL endpoint.

**Interpretation:**

- `1.0`: prediction executed successfully
- `0.0`: prediction execution failed
- `None`: not comparable, for example because no endpoint was configured or no supported prediction query exists

This metric is important because many model failures are not answer mismatches but non-executable SPARQL queries.

---

### `gold_execution_success`

Checks whether the gold SPARQL query can be executed successfully.

Gold execution must be monitored because answer-based metrics are only meaningful if the gold query itself can be executed.

---

## 5. Strict Answer-Based Metrics

Strict answer-based metrics compare the **executed query results**, not the raw SPARQL strings.

They are based on:

```text
code/src/evaluate/answer_normalization.py
```

The strict answer normalization has the following behavior for `SELECT` results:

- row order does not matter
- variable order inside a row does not matter
- duplicate rows are collapsed
- variable names are part of the normalized answer
- datatypes and language tags are part of the normalized answer
- numeric typed literals are normalized where possible

### `answer_exact_match`

Compares the normalized predicted answer to the normalized gold answer.

**Interpretation:**

- `1.0`: predicted answer exactly equals the gold answer
- `0.0`: predicted answer differs
- `None`: not comparable, for example if prediction execution failed

For `ASK`, the boolean result is compared directly.

For `SELECT`, the set of normalized result rows is compared.

---

### `answer_precision_recall_f1`

Computes answer-level precision, recall, and F1 over normalized result rows.

For `SELECT` queries:

```text
true positives = predicted rows ∩ gold rows
precision      = true positives / predicted rows
recall         = true positives / gold rows
F1             = 2 * precision * recall / (precision + recall)
```

If both prediction and gold return an empty result set, precision, recall, and F1 are defined as `1.0`.

For `ASK`, the metric behaves like binary exact match.

---

## 6. Value-Only Answer-Based Metrics

Value-only answer metrics are relaxed answer-based metrics. They compare executed answers while ignoring `SELECT` variable names.

This is useful because SPARQL variable names are often arbitrary. For example, these two queries can be answer-equivalent:

```sparql
SELECT ?name WHERE { ... }
```

```sparql
SELECT ?surname WHERE { ... }
```

If the returned values are identical, a value-only metric can count them as equivalent even if the variable names differ.

### `answer_value_exact_match`

Relaxed exact match over executed answers.

Differences from strict `answer_exact_match`:

- `SELECT` variable names are ignored
- returned values are still compared
- datatypes and language tags are still compared
- row content still matters

---

### `answer_value_precision_recall_f1`

Relaxed precision, recall, and F1 over executed answers.

This metric helps distinguish between:

1. wrong answer content
2. correct answer content returned under different variable names

---

## 7. Query Text Metrics

Query text metrics compare the predicted SPARQL query to the gold SPARQL query after lightweight text normalization.

The shared normalization is implemented in:

```text
code/src/evaluate/query_text_normalization.py
```

The normalization performs:

- removal of Markdown code fences
- removal of SPARQL comments outside string literals
- whitespace normalization
- normalization and sorting of `PREFIX` declarations
- normalization of `BASE` declarations
- preservation of query body order

These metrics are query-based and do not require endpoint execution.

---

### `query_normalized_exact_match`

Compares the normalized predicted query string to the normalized gold query string.

**Interpretation:**

- `1.0`: normalized query text is identical
- `0.0`: normalized query text differs
- `None`: not comparable

This is stricter than answer-based evaluation because semantically equivalent queries may still differ textually.

---

### `query_bleu`

Computes a lightweight BLEU score over normalized SPARQL tokens.

BLEU is useful as a secondary query-text similarity score, but it should not be interpreted as semantic correctness.

Limitations:

- a query can have high BLEU but contain a wrong predicate ID
- a query can have low BLEU but return the correct answer
- BLEU is sensitive to token overlap and does not understand SPARQL semantics

Therefore, BLEU is included as a supporting metric, not as the primary correctness criterion.

---

### `query_rouge1_f1`, `query_rouge2_f1`, `query_rougeL_f1`

ROUGE query metrics compare the predicted SPARQL query against the gold SPARQL query after lightweight query normalization.

They are implemented in:

```text
code/src/evaluate/metrics/query_rouge.py
```

Normalization for ROUGE:

- removes Markdown code fences
- removes SPARQL comments
- removes or normalizes prefix/base declarations
- normalizes whitespace
- tokenizes SPARQL in a stable way
- preserves query body order and does not reorder triples

Metric variants:

- `query_rouge1_f1`: unigram overlap F1
- `query_rouge2_f1`: bigram overlap F1
- `query_rougeL_f1`: longest common subsequence F1

These are auxiliary textual similarity metrics. They help diagnose whether a generated query is close to the reference text, but they do not prove semantic correctness.

Important interpretation notes:

- high ROUGE can still hide a wrong predicate, filter, join, or aggregation
- low ROUGE can still be acceptable if the query is semantically equivalent and answer-correct
- answer-based metrics remain the primary correctness signal

---

## 8. Query Structure Metric: SQM-Lite

### `sparql_structure_match`

This metric is a lightweight structural query similarity metric, referred to as SQM-lite.

It does not implement full SPARQL algebra equivalence. Instead, it:

- extracts the outer `WHERE` body
- extracts statement-like structural patterns
- normalizes whitespace
- ignores the order of extracted patterns
- computes precision, recall, and F1 over pattern overlap

Example output fields:

```text
precision
recall
f1
matched_pattern_count
prediction_pattern_count
gold_pattern_count
missing_gold_patterns
extra_predicted_patterns
matched_patterns
```

This metric is useful because it is less sensitive to pattern order than raw query string matching, but still stricter than answer-based metrics.

---

## 9. KG Reference Metrics

KG reference metrics compare ORKG identifiers in the predicted SPARQL query against those in the gold query.

The extraction is implemented in:

```text
code/src/evaluate/query_elements.py
```

It extracts canonical ORKG references such as:

```text
orkgp:P181003
orkgc:C121001
orkgr:R1544125
```

and canonicalizes full ORKG IRIs such as:

```text
http://orkg.org/orkg/predicate/P181003
```

to:

```text
orkgp:P181003
```

### `kg_ref_match`

Compares all extracted ORKG references together:

- predicates: `orkgp:*`
- classes: `orkgc:*`
- resources: `orkgr:*`

It reports precision, recall, F1, matched references, missing gold references, and extra predicted references.

---

### `predicate_ref_match`

Compares only `orkgp:*` references.

This is one of the most important metrics for ORKG template questions because the semantic meaning of a query often depends on choosing the correct property ID.

Examples:

```text
orkgp:P181003  NLP task
orkgp:P181004  NLP task type
orkgp:P181011  NLP dataset
orkgp:P29      publication year
```

A query can be syntactically valid but semantically wrong if it uses the wrong predicate.

---

### `class_ref_match`

Compares only `orkgc:*` references.

This is useful for checking whether the model selected the correct template family/class.

Important examples:

```text
orkgc:C121001  NLP4RE contribution
orkgc:C27001   Empirical Research Practice contribution
```

---

### `resource_ref_match`

Compares only `orkgr:*` references.

This is useful when questions involve concrete ORKG resources such as papers, datasets, venues, or templates.

---

## 10. URI Hallucination Metric

### `uri_hallucination`

Checks whether the predicted query contains ORKG references that are unknown to the configured local ORKG/PGMR memory.

The memory loader is implemented in:

```text
code/src/evaluate/kg_memory.py
```

The metric checks the prediction against a local memory such as:

```text
code/data/orkg_memory/templates/
```

By default, it checks:

```text
predicate
class
```

Resource references are ignored by default because concrete `orkgr:*` resources can be open-ended and may not be fully listed in the local template memory.

Important interpretation note:

This is a **local-memory hallucination check**. It does not prove that a reference does not exist anywhere in ORKG. It only indicates that the predicted reference is not present in the configured local memory.

**Value semantics:**

- `0.0`: no hallucinated reference detected
- `1.0`: at least one hallucinated reference detected
- `None`: not comparable

Additional fields include:

```text
has_hallucination
hallucinated_ref_rate
hallucinated_ref_count
hallucinated_refs
checked_prediction_refs
```

Example:

```text
orkgp:P999999999
```

is considered hallucinated if it is not present in the local allowed reference memory.

---

## 11. PGMR-Lite-Specific Metric

### `pgmr_unmapped_placeholders`

Detects unresolved PGMR-lite placeholders in the final predicted query.

This metric is only meaningful for PGMR-lite runs.

For normal direct SPARQL runs, it is marked as not applicable:

```text
comparable = false
reason = not_pgmr_mode
```

It detects patterns such as:

```text
{{NLP_TASK_PROPERTY}}
<NLP_TASK>
[UNMAPPED]
PGMR_UNKNOWN_PROPERTY
UNMAPPED_PREDICATE
__UNMAPPED__
```

**Value semantics for PGMR-lite runs:**

- `0.0`: no unmapped placeholders detected
- `1.0`: at least one unmapped placeholder detected
- `None`: not comparable

This metric distinguishes PGMR mapping failures from ordinary SPARQL generation errors.

---

### `pgmr_rouge1_f1`, `pgmr_rouge2_f1`, `pgmr_rougeL_f1`

PGMR ROUGE metrics are computed only when a gold PGMR query field is available, such as `gold_pgmr_sparql`.

They compare the PGMR-stage prediction against the gold PGMR query and use the same ROUGE variants as the direct query metrics:

- `pgmr_rouge1_f1`
- `pgmr_rouge2_f1`
- `pgmr_rougeL_f1`

These metrics are useful for debugging PGMR-lite generation before final ORKG-SPARQL restoration.

---

## 12. Post-Hoc LLM Judge

The LLM judge is not part of the deterministic evaluation loop. It is a post-hoc tool located at:

```text
code/tools/evaluate/run_llm_judge.py
```

It reads an existing `benchmark_raw.json` and writes:

```text
llm_judge_raw.json
llm_judge_summary.json
benchmark_summary_with_llm_judge.json
```

The judge receives only:

- question
- family
- gold ORKG SPARQL
- predicted/restored ORKG SPARQL

It does not receive execution result tables.

Item-level scores:

- `intent_score`: `0-2`
- `schema_score`: `0-2`
- `projection_score`: `0-2`
- `constraint_score`: `0-2`
- `aggregation_score`: `0-2`
- `overall_score`: `0-10`
- `verdict`: `correct`, `partially_correct`, or `incorrect`

Skipped items are scored as zero-score failures with `verdict = incorrect`. The summary means include skipped records as zeros, while `skip_reason_counts` and `zero_score_reason_counts` preserve why they were zero-scored.

---

## 13. Primary Error Category

### `primary_error_category`

Assigns one primary diagnostic category to each evaluated item.

Typical categories include:

```text
success
extraction_failure
unsupported_query_form
query_form_mismatch
prediction_execution_error
gold_execution_error
answer_mismatch
not_evaluated_no_endpoint
```

This metric is designed for high-level error analysis and summary plots.

---

## 14. Summary Aggregation

The summary file aggregates all per-item validation metrics into:

```text
benchmark_summary.json
```

The summary contains:

- total item count
- metric means
- comparable and non-comparable counts
- success and failure counts where applicable
- slice-level summaries
- error category counts
- response time statistics
- cost statistics for OpenAI runs
- diagnostic summaries for URI hallucination and PGMR unmapped placeholders
- ROUGE query similarity summaries
- optional post-hoc LLM judge summaries in `benchmark_summary_with_llm_judge.json`

The interactive viewer can display and compare multiple `benchmark_summary.json` files.

---

## 15. Interpretation Guide

### Answer-based vs. query-based metrics

Answer-based metrics evaluate the results returned by executing a query.

Query-based metrics evaluate the query itself.

Both are needed because:

- a query can be textually different but answer-equivalent
- a query can look similar but use a wrong predicate
- a query can execute successfully but return the wrong answer
- a query can use correct ORKG identifiers but have wrong joins or filters

---

### Strict answer metrics vs. value-only answer metrics

Strict answer metrics include variable names.

Value-only metrics ignore variable names.

This helps identify whether a failure is due to different variable naming or truly different answer content.

---

### KG reference match vs. URI hallucination

KG reference metrics compare prediction against gold.

URI hallucination compares prediction against local memory.

An extra predicted reference is not automatically hallucinated.

Example:

```text
Prediction has orkgp:P181004
Gold expects orkgp:P181003
```

This is an extra or wrong predicate, but not necessarily a hallucination if `orkgp:P181004` exists in memory.

Example:

```text
Prediction has orkgp:P999999999
```

This is hallucinated if it is absent from the local memory.

---

### PGMR unmapped placeholders vs. URI hallucination

These are different failure modes.

URI hallucination means the model produced an unknown ORKG identifier.

PGMR unmapped placeholders mean the mapping process did not fully ground a semantic placeholder into a final ORKG identifier.

This distinction is important for comparing direct SPARQL generation and PGMR-lite.

---

## 16. Recommended Reporting

For thesis reporting, the following metric groups are recommended:

1. extraction and execution metrics
2. strict answer-based EM/F1
3. value-only answer-based EM/F1
4. query normalized exact match, BLEU, ROUGE, and SQM-lite
5. predicate/class/resource reference F1
6. URI hallucination rate
7. PGMR unmapped placeholder rate for PGMR-lite runs
8. optional post-hoc LLM judge scores for semantic diagnosis
9. primary error category distribution

This combination provides a balanced evaluation of:

- output format quality
- executability
- answer correctness
- query similarity
- structural similarity
- ORKG grounding quality
- hallucination behavior
- PGMR mapping completeness
