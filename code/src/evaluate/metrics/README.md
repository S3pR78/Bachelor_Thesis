# Evaluation Metrics

This directory contains modular evaluation metrics for the Text-to-SPARQL benchmark pipeline.

The metrics are intentionally split into small modules so that each criterion can be tested, explained, and extended independently.

The evaluation currently distinguishes between:

1. extraction and execution checks
2. answer-based metrics
3. value-only answer-based metrics
4. query-/KG-reference-based metrics
5. local-memory URI hallucination checks
6. PGMR-lite-specific diagnostics

---

## 1. Extraction and Query Form Metrics

### `query_extracted`

Checks whether the model output contains an extracted SPARQL query.

**Meaning:**

- `1.0`: a query was extracted
- `0.0`: no query was extracted

This metric is useful for separating formatting/extraction failures from later execution or answer errors.

---

### `supported_query_form`

Checks whether the extracted query has a supported SPARQL form.

Currently relevant forms are usually:

- `SELECT`
- `ASK`

Unsupported or missing query forms are not evaluated further as normal executable predictions.

---

### `query_form_match`

Checks whether the predicted query form matches the gold query form.

Example:

- prediction: `SELECT`
- gold: `SELECT`
- result: match

Example mismatch:

- prediction: `ASK`
- gold: `SELECT`

This is a query-level metric, not an answer-level metric.

---

## 2. Execution Metrics

### `prediction_execution_success`

Checks whether the predicted query could be executed successfully against the configured SPARQL endpoint.

**Meaning:**

- `1.0`: prediction executed successfully
- `0.0`: prediction execution failed
- `None`: not comparable, for example no endpoint configured or no supported prediction query

This metric helps identify syntax errors, malformed queries, endpoint errors, and truncated model outputs.

---

### `gold_execution_success`

Checks whether the gold query could be executed successfully against the configured SPARQL endpoint.

This is important because answer-based metrics are only meaningful if the gold query itself can be executed.

---

## 3. Strict Answer-Based Metrics

Strict answer-based metrics compare the **executed answers**, not the raw SPARQL strings.

They use `answer_normalization.py` in strict mode.

Strict SELECT behavior:

- row order does not matter
- variable order inside a row does not matter
- duplicate rows are collapsed
- variable names are part of the normalized answer
- literal datatype and language tag are part of the normalized answer
- numeric typed literals are normalized where possible

### `answer_exact_match`

Compares the normalized predicted answer with the normalized gold answer.

**Meaning:**

- `1.0`: predicted answer equals gold answer exactly
- `0.0`: predicted answer differs from gold answer
- `None`: not comparable, for example prediction execution failed

For `ASK`, the boolean values are compared.

For `SELECT`, the normalized result rows are compared as sets.

---

### `answer_precision_recall_f1`

Computes answer-level precision, recall, and F1 over normalized SELECT result rows.

For SELECT:

```text
true positives = predicted rows ∩ gold rows
precision      = true positives / predicted rows
recall         = true positives / gold rows
F1             = harmonic mean of precision and recall
```

For ASK, the metric behaves like binary exact match:

- same boolean: precision/recall/F1 = `1.0`
- different boolean: precision/recall/F1 = `0.0`

This metric is answer-based, not SPARQL-string-based.

---

## 4. Value-Only Answer-Based Metrics

Value-only answer metrics are relaxed answer-based metrics.

They compare executed answers while ignoring SELECT variable names.

This is useful because two SPARQL queries can return the same content with different variable names.

Example:

```sparql
SELECT ?name WHERE { ... }
```

and:

```sparql
SELECT ?surname WHERE { ... }
```

can be answer-equivalent if the returned values are the same.

### `answer_value_exact_match`

Relaxed exact match over executed answers.

Differences from `answer_exact_match`:

- SELECT variable names are ignored
- returned values are still compared
- datatypes and language tags are still compared
- row content still matters

**Meaning:**

- `1.0`: value-only answer equals gold answer
- `0.0`: value-only answer differs from gold answer
- `None`: not comparable

---

### `answer_value_precision_recall_f1`

Relaxed precision/recall/F1 over executed SELECT answers.

It uses value-only normalization:

- row order does not matter
- variable order inside a row does not matter
- SELECT variable names are ignored
- returned values are still compared

This metric is useful for distinguishing between:

1. wrong answer content
2. correct answer content with different variable names

---

## 5. KG Reference Metrics

KG reference metrics compare ORKG identifiers in the predicted SPARQL query against the gold SPARQL query.

They are query-based metrics, not answer-based metrics.

The extraction is implemented in:

```text
code/src/evaluate/query_elements.py
```

It extracts references such as:

```text
orkgp:P181003
orkgc:C121001
orkgr:R1544125
```

and also canonicalizes full ORKG IRIs such as:

```text
http://orkg.org/orkg/predicate/P181003
```

to:

```text
orkgp:P181003
```

---

### `kg_ref_match`

Compares all extracted ORKG references together:

- predicates: `orkgp:*`
- classes: `orkgc:*`
- resources: `orkgr:*`

It reports:

- precision
- recall
- F1
- matched refs
- missing gold refs
- extra predicted refs

This helps diagnose whether the model uses the correct ORKG identifiers.

---

### `predicate_ref_match`

Same logic as `kg_ref_match`, but only for predicates:

```text
orkgp:*
```

This is especially important for ORKG template questions because template semantics often depend on choosing the correct property ID.

Example:

```text
orkgp:P181003  NLP task
orkgp:P181004  NLP task type
orkgp:P181011  NLP dataset
orkgp:P29      publication year
```

A query can be syntactically valid but semantically wrong if it uses the wrong predicate.

---

### `class_ref_match`

Same logic as `kg_ref_match`, but only for classes:

```text
orkgc:*
```

This is important for checking whether the model uses the correct template family/class.

Important examples:

```text
orkgc:C121001  NLP4RE contribution
orkgc:C27001   Empirical Research Practice contribution
```

---

### `resource_ref_match`

Same logic as `kg_ref_match`, but only for resources:

```text
orkgr:*
```

This is useful when queries contain concrete ORKG resources such as paper, venue, dataset, or template resources.

---

## 6. URI Hallucination Metric

### `uri_hallucination`

Checks whether the predicted query contains ORKG references that are unknown to the local ORKG/PGMR memory.

This is a local-memory hallucination check.

It does **not** prove that a reference does not exist anywhere in ORKG. It only checks whether the reference is absent from the configured local memory.

The memory is loaded from paths such as:

```text
code/data/orkg_memory/templates/
```

Default checked reference kinds:

```text
predicate
class
```

Resource references are ignored by default because concrete `orkgr:*` resources can be open-ended and may not be fully listed in the local template memory.

**Value semantics:**

- `0.0`: no hallucinated reference detected
- `1.0`: at least one hallucinated reference detected
- `None`: not comparable

Additional fields include:

- `has_hallucination`
- `hallucinated_ref_rate`
- `hallucinated_ref_count`
- `hallucinated_refs`
- `checked_prediction_refs`

Example:

```text
orkgp:P999999999
```

is considered hallucinated if it is not present in the local allowed reference memory.

---

## 7. PGMR-Lite-Specific Metric

### `pgmr_unmapped_placeholders`

Detects unresolved PGMR-lite placeholders in the final predicted query.

This metric is only meaningful for PGMR-lite runs.

For normal direct SPARQL runs, this metric is marked as not applicable:

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

**Value semantics for PGMR runs:**

- `0.0`: no unmapped placeholders detected
- `1.0`: at least one unmapped placeholder detected
- `None`: not comparable

This metric helps distinguish PGMR mapping failures from ordinary SPARQL generation errors.

---

## 8. Error Category Metric

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

This is useful for high-level error analysis and for quickly identifying the dominant failure modes of a model.

---

## 9. Metric Groups

### General metrics

These apply to normal direct SPARQL runs and PGMR-lite runs:

```text
query_extracted
supported_query_form
query_form_match
prediction_execution_success
gold_execution_success
answer_exact_match
answer_precision_recall_f1
answer_value_exact_match
answer_value_precision_recall_f1
kg_ref_match
predicate_ref_match
class_ref_match
resource_ref_match
uri_hallucination
primary_error_category
```

### PGMR-lite-only metrics

These should only be interpreted for PGMR-lite runs:

```text
pgmr_unmapped_placeholders
```

For non-PGMR runs, this metric should be marked as:

```text
reason = not_pgmr_mode
```

---

## 10. Interpretation Notes

### Answer-based vs. query-based

Answer-based metrics compare the results of executing SPARQL queries.

Query-based metrics compare properties of the SPARQL query itself.

A model can have:

- low query-string similarity but correct answer
- high query similarity but wrong answer
- correct answer but wrong variable names
- executable query with wrong ORKG predicate
- correct ORKG IDs but wrong joins or filters

Therefore, multiple metric groups are needed.

---

### Strict answer metrics vs. value-only answer metrics

Strict answer metrics include SELECT variable names.

Value-only answer metrics ignore SELECT variable names.

This distinction is useful because variable names are often arbitrary in SPARQL, while the returned values are what matters for many question-answering settings.

---

### KG reference metrics vs. URI hallucination

KG reference metrics compare prediction against gold.

URI hallucination compares prediction against local memory.

An extra predicted reference is not automatically hallucinated.

Example:

```text
Prediction has orkgp:P181004
Gold expects orkgp:P181003
```

This is an extra/wrong predicate, but not necessarily hallucination if `orkgp:P181004` exists in memory.

Example:

```text
Prediction has orkgp:P999999999
```

This is hallucinated if it is not present in the local allowed memory.

---

### PGMR unmapped placeholders

Unmapped placeholders are a PGMR-lite-specific failure mode.

They indicate that the semantic intermediate representation was not fully grounded into executable SPARQL.

This is different from URI hallucination:

- URI hallucination: model produced an unknown ORKG ID
- unmapped placeholder: mapping did not produce a final ORKG ID
