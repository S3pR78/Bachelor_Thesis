# Evaluation Metrics

## Purpose of the Evaluation

The goal of the evaluation is to assess practical approaches for improving open-source language models for Text-to-SPARQL generation over ORKG template questions. The task is challenging because a correct prediction must satisfy several requirements at the same time: the model must produce a valid SPARQL query, use the correct ORKG classes and predicates, execute successfully against the ORKG endpoint, and return the same answer as the gold query.

For this reason, the evaluation does not rely on a single metric. Instead, it uses a set of complementary metrics that measure different aspects of prediction quality. This makes it possible to distinguish between extraction failures, execution failures, wrong answers, wrong ORKG identifiers, hallucinated identifiers, and PGMR-lite mapping failures.

The metrics are grouped into the following categories:

1. extraction and query form metrics
2. execution metrics
3. answer-based metrics
4. relaxed value-only answer metrics
5. query text and structure metrics
6. knowledge-graph reference metrics
7. URI hallucination diagnostics
8. PGMR-lite-specific diagnostics
9. primary error categories

This section describes the motivation, definition, and interpretation of each metric group.

---

## Extraction and Query Form Metrics

### Query Extraction

The first step checks whether a SPARQL query can be extracted from the model output. This is necessary because language models may return explanations, Markdown code blocks, incomplete text, or no query at all.

The metric `query_extracted` is defined as:

```text
1.0 if a SPARQL query was extracted
0.0 otherwise
```

This metric separates output-format failures from later SPARQL-specific failures. If no query is extracted, execution-based and answer-based metrics are usually not comparable.

---

### Supported Query Form

The metric `supported_query_form` checks whether the extracted query has a query form supported by the evaluation pipeline. In this project, the relevant query forms are mainly `SELECT` and `ASK`.

Unsupported query forms are marked as not comparable for execution and answer evaluation. This prevents unsupported predictions from being incorrectly evaluated as answer mismatches.

---

### Query Form Match

The metric `query_form_match` checks whether the predicted query form matches the gold query form. For example, a predicted `SELECT` query matches a gold `SELECT` query, while a predicted `ASK` query does not match a gold `SELECT` query.

This is a query-level metric. It does not require endpoint execution and does not evaluate the returned answer.

---

## Execution Metrics

### Prediction Execution Success

A generated SPARQL query is only useful if it can be executed. The metric `prediction_execution_success` checks whether the predicted query runs successfully against the configured ORKG SPARQL endpoint.

It is defined as:

```text
1.0 if the prediction executes successfully
0.0 if execution fails
None if the metric is not comparable
```

This metric captures syntax errors, malformed queries, unsupported query forms, endpoint errors, and truncated queries. It is particularly important because many Text-to-SPARQL failures are not wrong answers but non-executable queries.

---

### Gold Execution Success

The metric `gold_execution_success` checks whether the gold query itself can be executed. This is important because answer-based metrics are only meaningful if the gold query produces a valid reference answer.

If the gold query fails, answer comparison cannot be interpreted reliably.

---

## Strict Answer-Based Metrics

Answer-based metrics compare the results obtained by executing the predicted and gold SPARQL queries. They do not directly compare the SPARQL strings.

The strict answer normalization has the following properties:

- result row order is ignored
- variable order within a row is ignored
- duplicate rows are collapsed
- variable names are part of the normalized answer
- literal datatypes and language tags are part of the normalized answer
- numeric typed literals are normalized where possible

This strict mode is useful when the structure of the returned answer matters, including the selected variable names.

---

### Answer Exact Match

The metric `answer_exact_match` checks whether the normalized predicted answer is exactly equal to the normalized gold answer.

For `ASK` queries, the boolean values are compared.

For `SELECT` queries, the normalized sets of result rows are compared.

The metric is defined as:

```text
1.0 if the normalized predicted answer equals the normalized gold answer
0.0 if the answers differ
None if the comparison is not possible
```

This is a strict answer-level correctness metric.

---

### Answer Precision, Recall, and F1

The metric `answer_precision_recall_f1` compares predicted and gold result rows using set overlap.

For `SELECT` queries:

```text
true positives = predicted rows ∩ gold rows
precision      = true positives / predicted rows
recall         = true positives / gold rows
F1             = 2 * precision * recall / (precision + recall)
```

If both the prediction and the gold query return an empty result set, precision, recall, and F1 are defined as `1.0`.

For `ASK` queries, the metric behaves like binary exact match: equal boolean values receive `1.0`, different values receive `0.0`.

This metric is useful when a prediction returns a partially correct result set.

---

## Value-Only Answer-Based Metrics

Strict answer metrics include variable names. However, SPARQL variable names are often arbitrary. Two queries can return the same content under different variable names.

For example:

```sparql
SELECT ?name WHERE { ... }
```

and

```sparql
SELECT ?surname WHERE { ... }
```

can be answer-equivalent if the returned values are the same.

Therefore, the evaluation also includes relaxed value-only answer metrics. These ignore `SELECT` variable names while still comparing returned values, datatypes, and language tags.

---

### Value-Only Exact Match

The metric `answer_value_exact_match` checks whether the predicted and gold answers are equal after ignoring `SELECT` variable names.

This metric helps identify cases where the model produced the correct answer content but used different variable names.

---

### Value-Only Precision, Recall, and F1

The metric `answer_value_precision_recall_f1` computes precision, recall, and F1 over value-only normalized result rows.

It is useful for distinguishing:

1. predictions with wrong answer content
2. predictions with correct answer content but different variable naming

This distinction is important because variable names usually do not affect the semantic answer to a question.

---

## Query Text Metrics

Answer-based metrics alone are not sufficient because a query may return the correct answer accidentally or may be textually close to the gold query while still containing a critical semantic error. Therefore, query text metrics are included as supporting metrics.

All query text metrics use lightweight normalization:

- Markdown code fences are removed
- comments outside string literals are removed
- whitespace is normalized
- `PREFIX` declarations are normalized and sorted
- `BASE` declarations are normalized
- query body order is preserved

---

### Normalized Query Exact Match

The metric `query_normalized_exact_match` compares the normalized predicted query string with the normalized gold query string.

It is defined as:

```text
1.0 if the normalized query texts are identical
0.0 otherwise
```

This metric is stricter than answer-based metrics because semantically equivalent queries can still differ textually. It is useful as a query-string-level exact match criterion.

---

### Query BLEU

The metric `query_bleu` computes a BLEU score over normalized SPARQL tokens.

BLEU is included because it is commonly used as a text-similarity metric in sequence generation tasks. However, it is treated as a supporting metric rather than a primary correctness metric.

A high BLEU score does not guarantee that the query is semantically correct. A query can have high token overlap with the gold query but use a wrong predicate ID. Conversely, a query can have lower BLEU but still return the correct answer.

Therefore, BLEU is interpreted together with answer-based, structural, and KG-reference metrics.

---

## Query Structure Metric: SQM-Lite

The metric `sparql_structure_match` is a lightweight structural similarity metric inspired by structural query matching. It is referred to as SQM-lite because it does not implement full SPARQL algebra equivalence.

The metric:

- extracts the outer `WHERE` body
- extracts statement-like query patterns
- normalizes whitespace
- ignores the order of extracted patterns
- computes precision, recall, and F1 over pattern overlap

For example, two queries with the same triple patterns in different order can receive a perfect SQM-lite score.

The metric reports:

```text
precision
recall
F1
matched pattern count
prediction pattern count
gold pattern count
missing gold patterns
extra predicted patterns
```

SQM-lite is useful because it is less sensitive to pattern order than raw query exact match, while still being stricter than answer-based evaluation.

---

## Knowledge-Graph Reference Metrics

ORKG template queries strongly depend on the correct use of ORKG identifiers. A model may generate syntactically valid SPARQL that still uses the wrong predicate or class. Therefore, the evaluation includes KG-reference metrics.

The extraction step identifies ORKG references such as:

```text
orkgp:P181003
orkgc:C121001
orkgr:R1544125
```

It also canonicalizes full ORKG IRIs to the same prefixed format.

---

### KG Reference Match

The metric `kg_ref_match` compares all ORKG references in the predicted query against the gold query.

It includes:

- predicates: `orkgp:*`
- classes: `orkgc:*`
- resources: `orkgr:*`

The metric computes precision, recall, and F1 over reference overlap and records matched, missing, and extra references.

---

### Predicate Reference Match

The metric `predicate_ref_match` compares only ORKG predicates (`orkgp:*`).

This is especially important for ORKG template queries. The meaning of a query often depends on selecting the correct predicate ID. For example, confusing an NLP task property with an NLP task type property can make a query semantically wrong even if it is executable.

This metric is closely related to PID-level evaluation because it directly measures whether the predicted predicate IDs match the gold predicate IDs.

---

### Class Reference Match

The metric `class_ref_match` compares only ORKG classes (`orkgc:*`).

This is important for checking whether the model selected the correct template family. In this project, two important contribution classes are:

```text
orkgc:C121001  NLP4RE contribution
orkgc:C27001   Empirical Research Practice contribution
```

Using the wrong class can move the query into the wrong template space.

---

### Resource Reference Match

The metric `resource_ref_match` compares only ORKG resources (`orkgr:*`).

This is useful for questions involving concrete resources such as papers, datasets, venues, or templates.

---

## URI Hallucination

The metric `uri_hallucination` checks whether the predicted query contains ORKG references that are unknown to the configured local ORKG/PGMR memory.

This metric is designed to capture hallucinated or unsupported identifiers. It is evaluated against local memory files, not against the entire ORKG.

Therefore, the interpretation is:

```text
The predicted reference is unknown to the local memory used by the pipeline.
```

It does not prove that the reference does not exist anywhere in ORKG.

By default, the metric checks predicates and classes. Resource references are ignored by default because concrete resources can be open-ended and may not be fully listed in the local template memory.

The metric reports:

```text
has_hallucination
hallucinated_ref_rate
hallucinated_ref_count
hallucinated_refs
checked_prediction_refs
```

The value is defined as:

```text
0.0 if no hallucinated reference was detected
1.0 if at least one hallucinated reference was detected
```

This metric is important for comparing direct SPARQL generation and PGMR-lite. Direct generation may produce unknown ORKG IDs, while a mapping-based method can reduce such hallucinations by grounding outputs through a controlled memory.

---

## PGMR-Lite-Specific Diagnostic

The metric `pgmr_unmapped_placeholders` detects unresolved PGMR-lite placeholders in the final predicted query.

It is only meaningful for PGMR-lite runs. For direct SPARQL runs, the metric is marked as not applicable:

```text
comparable = false
reason = not_pgmr_mode
```

The metric detects unresolved patterns such as:

```text
{{NLP_TASK_PROPERTY}}
<NLP_TASK>
[UNMAPPED]
PGMR_UNKNOWN_PROPERTY
UNMAPPED_PREDICATE
__UNMAPPED__
```

The value is defined as:

```text
0.0 if no unresolved placeholder was detected
1.0 if at least one unresolved placeholder was detected
```

This diagnostic separates PGMR mapping failures from ordinary SPARQL generation errors. A direct SPARQL model may hallucinate an unknown ID, while a PGMR-lite system may instead leave a semantic placeholder unmapped.

---

## Primary Error Category

The metric `primary_error_category` assigns one high-level diagnostic category to each evaluated item.

Typical categories are:

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

This metric is used for high-level error analysis and to identify dominant failure modes across models and prompting strategies.

---

## Why These Metrics Were Selected

The selected metrics cover complementary aspects of the Text-to-SPARQL task.

### Execution and answer metrics

These measure whether the generated query actually works and returns the correct answer. They are the most important correctness metrics from a question-answering perspective.

### Value-only answer metrics

These provide a more relaxed view of answer correctness by ignoring arbitrary variable names. This is useful because variable names often do not affect the answer semantics.

### Query text and structure metrics

These make it possible to compare predicted queries to gold queries even when endpoint execution is unavailable or when one wants to analyze how close the generated query is to the reference query. BLEU provides token-level similarity, while SQM-lite provides a more structure-oriented comparison.

### KG-reference metrics

These are essential for ORKG template questions because the correct use of predicates and classes is central to query semantics. They provide a detailed view of whether the model uses the right ORKG identifiers.

### URI hallucination

This metric captures whether the model produces ORKG references that are not known to the local memory. This is important for evaluating grounding behavior and for comparing direct SPARQL generation with memory-guided methods.

### PGMR-lite diagnostics

PGMR-lite introduces a mapping step from semantic representations to SPARQL. Therefore, it requires a specific diagnostic for unresolved placeholders or mapping failures.

---

## Limitations

The evaluation metrics have several limitations.

First, normalized query exact match and BLEU are text-based and do not capture semantic equivalence. They should not be used as the only correctness criteria.

Second, SQM-lite is not a full SPARQL algebra comparison. It is a lightweight structural approximation and may not correctly handle all complex SPARQL constructs.

Third, URI hallucination is evaluated against local memory. A reference marked as unknown is not necessarily globally invalid in ORKG.

Fourth, answer-based metrics depend on endpoint availability and the current state of the ORKG triplestore.

These limitations are addressed by using multiple complementary metrics instead of relying on a single score.

---

## Recommended Metric Reporting

For the final evaluation, the following metrics should be reported:

1. `query_extracted`
2. `prediction_execution_success`
3. `answer_exact_match`
4. `answer_f1`
5. `answer_value_exact_match`
6. `answer_value_f1`
7. `query_normalized_exact_match`
8. `query_bleu`
9. `sparql_structure_f1`
10. `predicate_ref_f1`
11. `class_ref_f1`
12. `kg_ref_f1`
13. `uri_hallucination`
14. `pgmr_unmapped_placeholders` for PGMR-lite runs
15. `primary_error_category` distribution

Together, these metrics provide a comprehensive view of format quality, executability, answer correctness, query similarity, structural similarity, ORKG grounding quality, hallucination behavior, and PGMR mapping completeness.
