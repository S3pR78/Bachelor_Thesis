---
title: "PGMR-lite and T5 Experiments for ORKG Text-to-SPARQL"
author: "Draft for Bachelor Thesis Approach/Experiments Chapter"
date: "2026-04-27"
---

# PGMR-lite and T5 Experiments for ORKG Text-to-SPARQL

## 1. Motivation

The goal of this part of the project was to improve an open-source language model for Text-to-SPARQL generation over ORKG template data. The initial benchmark setup required the model to generate complete ORKG-SPARQL queries directly from natural language questions. This is difficult for small encoder-decoder models such as T5-base, because the output query contains several types of information at the same time:

- general SPARQL syntax,
- ORKG-specific classes and predicates,
- template-specific relation paths,
- aggregation and grouping logic,
- filters, labels, optional patterns, and endpoint-compatible syntax.

In direct ORKG-SPARQL, the model has to generate identifiers such as `orkgp:P181011`, `orkgp:P135046`, `orkgc:C121001`, or `orkgc:C27001`. These identifiers are meaningful in the ORKG schema, but they are not semantically transparent to the language model. For example, the model has to learn that `orkgp:P31` links a paper to a contribution, while `orkgc:C121001` identifies an NLP4RE contribution and `orkgc:C27001` identifies an Empirical Research Practice contribution.

To reduce this difficulty, I introduced an intermediate representation called **PGMR-lite**. Instead of generating real ORKG identifiers directly, the model generates readable placeholders such as `pgmr:has_contribution`, `pgmr:evaluation_metric`, `pgmr:validation_procedure`, or `pgmrc:nlp4re_contribution`. These placeholders are then deterministically restored to real ORKG-SPARQL identifiers using a mapping/memory component.

The resulting pipeline is:

```text
Natural language question
-> PGMR-lite SPARQL prediction
-> PGMR postprocessing
-> restored ORKG-SPARQL query
-> endpoint execution and evaluation
```

The motivation was that the model should learn the semantic query structure, while the exact ORKG identifier mapping is handled deterministically after generation.

---

## 2. Dataset Repair and Validation

Before the PGMR-lite approach became useful, the dataset itself had to be repaired. Some generated dataset entries, especially from `Generated_NLP4RE` and `Generated_Empirical_Research`, contained incorrect gold SPARQL queries. Typical problems were:

- wrong template classes,
- wrong predicate paths,
- missing contribution patterns,
- incorrect or missing venue filters,
- old or inconsistent gold queries that did not match the question,
- queries that were syntactically valid but semantically not aligned with the intended template.

For the `empirical_research_practice` family, the standard contribution pattern was normalized to:

```sparql
?paper orkgp:P31 ?contribution .
?contribution a orkgc:C27001 .
```

For many empirical research practice queries, the venue filter for the IEEE International Requirements Engineering Conference was also added or fixed:

```sparql
?contribution orkgp:P135046 ?venue .
?venue rdfs:label ?venue_name .
FILTER(LCASE(STR(?venue_name)) = LCASE("IEEE International Requirements Engineering Conference"))
```

For the `nlp4re` family, the standard contribution class was `orkgc:C121001`. The repaired dataset was then validated against the ORKG endpoint so that invalid gold queries could be found and corrected before training.

After repair and validation, the dataset was split into final train, validation, and test files. The final SPARQL dataset was then transformed into PGMR-lite files. These PGMR-lite files still contain the original `gold_sparql`, but additionally include fields such as:

```text
gold_pgmr_sparql
pgmr_status
pgmr_replaced_terms
pgmr_unmapped_terms
```

This made it possible to train on PGMR-lite targets while still evaluating against the original executable ORKG-SPARQL gold queries.

---

## 3. First Failed Direction: LC-QuAD2-style Training

One early idea was to use an external Text-to-SPARQL dataset, such as LC-QuAD2, before training on the ORKG data. The assumption was that the model might learn general SPARQL structure from a larger dataset and then transfer this knowledge to ORKG.

In practice, this did not work well. The generated outputs contained patterns that were not compatible with the ORKG setting. Example problems included outputs with generic placeholder structures such as:

```text
entity0 relation0 ?X . ?Y relation1 ?x
```

and outputs that mixed PGMR-like patterns with unrelated relation descriptions. The model appeared to learn a different graph schema rather than transferable ORKG-SPARQL behavior. Since LC-QuAD2 is not based on the ORKG schema and uses a different data model, it was not helpful for this specific task.

This experiment showed that general Text-to-SPARQL pretraining data does not automatically transfer to ORKG template queries. For the rest of the work, I focused on the repaired ORKG-specific dataset and PGMR-lite representation.

---

## 4. First PGMR-lite Training Attempts

The first PGMR-lite training attempts used a minimal prompt:

```text
task: text_to_pgmr_sparql
family: {family}
question: {question}
pgmr_sparql:
```

This was intentionally simple. The model only received the template family and the natural language question. The target was `gold_pgmr_sparql`.

The results were better than the LC-QuAD2-style experiment, but still not reliable. The model often learned the beginning of the query but failed to finish it correctly. For example, it could generate the beginning of a count query but stop too early:

```sparql
SELECT (COUNT(DISTINCT ?participation) AS ?count) WHERE ?paper pgmr:has_contribution
```

Other outputs were syntactically incomplete or contained repeated fragments. These early results showed that PGMR-lite made the task easier, but the model still needed better data, better decoding settings, and better prompting.

---

## 5. Generation Parameter Issue

A major issue was caused by the generation settings used during inference. Initially, generation used constraints such as:

```python
num_beams=4
early_stopping=True
repetition_penalty=1.2
no_repeat_ngram_size=3
```

These settings can be useful for natural language generation, but they are harmful for SPARQL. SPARQL queries often contain repeated triple patterns and similar structures. For example, label patterns occur repeatedly:

```sparql
?x rdfs:label ?xLabel .
?y rdfs:label ?yLabel .
```

With `no_repeat_ngram_size=3` and a repetition penalty, the model was discouraged from producing valid repeated SPARQL structures. This led to truncated or malformed outputs.

After simplifying the generation settings to:

```python
output_ids = model.generate(
    **inputs,
    max_new_tokens=max_new_tokens,
    num_beams=4,
    do_sample=False,
)
```

outputs improved immediately. For the same example question, the model generated a much better PGMR-lite structure:

```sparql
SELECT (COUNT(DISTINCT ?contribution) AS ?count) WHERE
  ?paper pgmr:has_contribution ?contribution .
  ?contribution a pgmrc:nlp4re_contribution .
  ?contribution pgmr:evaluation ?evaluation .
  ?evaluation pgmr:evaluation_metric ?metric .
  ?evaluation pgmr:validation_procedure ?validationProcedure .
```

The query was still missing `WHERE { ... }` braces, but the semantic structure was much better. This showed that decoding parameters are an important part of the evaluation setup for structured query generation.

---

## 6. Paraphrase-Augmented Training

The dataset contained paraphrases in the field:

```json
"paraphrased_questions": [...]
```

Initially, these paraphrases were not used by the trainer because the training code only used the `question` field. To make use of them, I created an augmented training split:

```text
code/data/dataset/pgmr/final/train_augmented_with_paraphrases.json
```

Each paraphrase was converted into a separate training example with the same target PGMR-lite query:

```text
original question -> gold_pgmr_sparql
paraphrase 1      -> same gold_pgmr_sparql
paraphrase 2      -> same gold_pgmr_sparql
```

The validation and test splits were not augmented in the same way, so that evaluation stayed cleaner and less affected by duplicated paraphrase variants.

This step increased training diversity and helped the model become more robust to different question formulations.

---

## 7. Training with More Epochs

After the dataset repair and paraphrase augmentation, I trained T5-base for more epochs. Earlier runs with fewer epochs were not strong enough. A 30-epoch run was tested with the following setup:

```text
model: t5_base
task: pgmr_lite
train_path: code/data/dataset/pgmr/final/train_augmented_with_paraphrases.json
validation_path: code/data/dataset/pgmr/final/validation.json
target_field: gold_pgmr_sparql
num_train_epochs: 30
learning_rate: 3e-5
max_source_length: 192
max_target_length: 512
```

This run performed much better than the earlier attempts. The validation loss decreased and stabilized around:

```text
eval_loss approximately 0.2156
```

The loss curve did not show a strong overfitting signal. Around epochs 25-30, the improvement became small, so more epochs would probably not have added much benefit.

A structural validation on 80 validation entries showed:

| Metric | Result |
|---|---:|
| COUNT match | 86.25% |
| GROUP BY match | 78.75% |
| ORDER BY match | 86.25% |
| BIND match | 85.00% |
| Boolean-filter hallucination | 27.50% |
| PGMR token subset of gold | 75.00% |

This confirmed that the model learned many query skeletons, but still struggled with complex query shape semantics.

---

## 8. Metadata-aware Prompting

The next improvement was to add structured metadata to the prompt. The previous prompt only gave the family and question. However, the dataset already contained metadata such as `answer_type`, `query_shape`, `special_types`, and `complexity_level`. These fields can help the model decide whether the query needs aggregation, grouping, ordering, BIND expressions, or other special constructs.

The metadata-aware prompt was:

```text
task: text_to_pgmr_sparql
family: {family}
answer_type: {answer_type}
query_shape: {query_shape}
special_types: {special_types}
complexity_level: {complexity_level}
question: {question}
pgmr_sparql:
```

This became the `v5_meta_para_30ep` training run. It used the paraphrase-augmented training split and 30 epochs. The final validation loss was approximately:

```text
eval_loss approximately 0.1932
```

The metadata-aware model improved several structural metrics compared to the earlier paraphrase-only model:

| Metric | v2 paraphrase 30ep | v5 metadata 30ep |
|---|---:|---:|
| COUNT match | 86.25% | 88.75% |
| GROUP BY match | 78.75% | 78.75% |
| ORDER BY match | 86.25% | 91.25% |
| BIND match | 85.00% | 85.00% |
| Boolean-filter hallucination | 27.50% | 17.50% |
| PGMR token subset of gold | 75.00% | 78.75% |

The most important improvement was the reduction in Boolean-filter hallucinations. The model also improved in COUNT and ORDER BY behavior. However, GROUP BY and BIND remained difficult, especially for questions involving per-year, per-decade, or grouped aggregation logic.

---

## 9. Postprocessing

Even after fine-tuning, the model still produced systematic syntax issues. These were not always semantic errors; often the query only needed small formatting repairs before it became executable.

### 9.1 Missing WHERE braces

The model often generated:

```sparql
SELECT ... WHERE ?paper pgmr:has_contribution ?contribution .
```

instead of:

```sparql
SELECT ... WHERE {
  ?paper pgmr:has_contribution ?contribution .
}
```

A postprocessing rule was introduced to wrap the body after `WHERE` in braces.

### 9.2 GROUP BY and ORDER BY inside WHERE

Another common problem was:

```sparql
WHERE {
  ...
  ORDER BY ?label
}
```

This is invalid SPARQL because solution modifiers such as `GROUP BY`, `ORDER BY`, `LIMIT`, and `OFFSET` must be outside the `WHERE` block. The postprocessor moves these modifiers outside:

```sparql
WHERE {
  ...
}
ORDER BY ?label
```

### 9.3 Bare OPTIONAL patterns

The model also generated invalid OPTIONAL patterns:

```sparql
OPTIONAL ?paper rdfs:label ?paperLabel
```

The correct SPARQL syntax is:

```sparql
OPTIONAL {
  ?paper rdfs:label ?paperLabel .
}
```

A first fix only worked when the optional triple ended with a period. However, real predictions often omitted the period before the closing brace. Therefore the fix was made more robust so that both of these cases are handled:

```sparql
OPTIONAL ?x rdfs:label ?label .
OPTIONAL ?x rdfs:label ?label }
```

This postprocessing was a major contributor to executable predictions.

---

## 10. PGMR Restore and Mapping

After PGMR-lite generation and postprocessing, the placeholder query is restored to real ORKG-SPARQL. For this, the system uses PGMR memory files from:

```text
code/data/orkg_memory/templates
```

In addition, a few safe fallback mappings were added:

```text
pgmr:has_contribution -> orkgp:P31
pgmr:publication_year -> orkgp:P29
pgmr:statistical_test -> orkgp:P35133
```

The last mapping is a safe alias. In the gold PGMR dataset, the plural token `pgmr:statistical_tests` maps to `orkgp:P35133`. The model once produced the singular form `pgmr:statistical_test`, so it was added as a controlled alias.

I deliberately avoided mapping all unknown PGMR tokens manually. Some of the remaining unknown tokens appeared to be model hallucinations or incorrect schema compositions. Blindly mapping them would make the evaluation artificially better and less trustworthy.

---

## 11. Endpoint Execution Results

The endpoint execution results improved strongly after postprocessing and controlled restore fixes. On the validation split with 80 entries, the following progression was observed:

| Stage | Executable Predictions |
|---|---:|
| Before postprocessing fixes | 24 / 80 |
| After WHERE / GROUP / ORDER fix | 40 / 80 |
| After first OPTIONAL fix | 47 / 80 |
| After robust OPTIONAL fix | 70 / 80 |
| After safe `pgmr:statistical_test` alias | 71 / 80 |

The final isolated PGMR-lite validation reached:

```text
71 / 80 executable predictions = 88.75%
```

This means the restored ORKG-SPARQL query was accepted by the ORKG endpoint without execution errors. This does not necessarily mean that the answer is semantically correct, but it is an important technical milestone. Without a syntactically executable query, result-set comparison is not possible.

In the final integrated evaluation pipeline, the model outputs are processed as:

```text
raw_model_output
-> pgmr_postprocessed_query
-> pgmr_restored_query
-> query_execution
-> gold_execution
-> validation metrics
```

This makes the evaluation traceable. For each item, the benchmark output records the raw model output, the postprocessed PGMR query, the restored ORKG-SPARQL query, missing mappings, remaining PGMR tokens, endpoint execution result, and validation output.

---

## 12. Remaining Error Types

Before the final integrated run, the remaining problematic cases were mainly:

```text
8 missing or hallucinated PGMR placeholders
1 malformed FILTER expression
```

The remaining unknown PGMR tokens were:

```text
pgmr:question_answer
pgmr:baseline_comparison_metric
pgmr:domain_experience
pgmr:annotator_conflict
pgmr:documentation_type
pgmr:algorithm_and_dependency
pgmr:assignment
pgmr:nlp_data_output
```

Not all of these should necessarily be added as mappings. Some may be legitimate aliases, but others are likely model hallucinations. For example, `pgmr:algorithm_and_dependency` and `pgmr:nlp_data_output` looked more like wrong schema compositions than missing memory entries.

The malformed FILTER example was:

```sparql
FILTER(LCASE(STR(?algorithmLabel)), "random forest"))
```

A valid form would be closer to:

```sparql
FILTER(CONTAINS(LCASE(STR(?algorithmLabel)), "random forest"))
```

or:

```sparql
FILTER(REGEX(LCASE(STR(?algorithmLabel)), "random forest"))
```

Such cases are genuine model errors and should be counted in the error analysis rather than hidden by postprocessing.

---

## 13. Integration into the Evaluation Pipeline

The existing benchmark runner originally assumed that the model directly generates SPARQL. The PGMR-lite model required a new evaluation mode:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model t5_base_pgmr_lite_final \
  --dataset code/data/dataset/pgmr/final/validation.json \
  --prompt-mode pgmr_lite_meta \
  --prediction-format pgmr_lite \
  --pgmr-memory-dir code/data/orkg_memory/templates \
  --sparql-endpoint https://www.orkg.org/triplestore
```

The important new options are:

```text
--prompt-mode pgmr_lite_meta
--prediction-format pgmr_lite
--pgmr-memory-dir code/data/orkg_memory/templates
```

With this setup, the benchmark runner no longer treats the model output as direct SPARQL. Instead, it performs PGMR postprocessing and restore before execution.

For comparison, the original T5-base can still be evaluated as a direct SPARQL baseline:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model t5_base \
  --dataset code/data/dataset/pgmr/final/validation.json \
  --prompt-mode zero_shot \
  --prediction-format sparql \
  --sparql-endpoint https://www.orkg.org/triplestore
```

This comparison is important because it shows what the PGMR-lite strategy and fine-tuning contributed compared to direct SPARQL generation.

---

## 14. Interpretation

The final PGMR-lite approach helped because it decomposed the problem. Instead of asking T5-base to learn every ORKG identifier and every SPARQL structure at once, the model learns a more semantic intermediate form. The deterministic restore step then handles the ORKG-specific identifiers.

The approach improved:

- syntactic stability,
- endpoint executability,
- separation of model errors and mapping errors,
- interpretability of generated queries,
- ability to inspect intermediate outputs.

However, the approach does not solve all problems. The model still struggles with:

- complex grouped aggregation,
- BIND expressions for decade buckets,
- exact relation-path selection,
- occasional Boolean-filter hallucinations,
- unknown or hallucinated PGMR placeholders,
- malformed filters in rare cases.

Therefore, the final interpretation is that PGMR-lite is useful as a controlled intermediate representation for small open-source models, but it still requires postprocessing and careful error analysis. It improves executability and structural quality, but semantic correctness must still be measured separately using answer-based evaluation metrics.

---

## 15. Lessons Learned

1. **Dataset quality was critical.** Early training was unreliable because some gold queries were wrong. Repairing and validating the dataset was necessary before meaningful model evaluation.

2. **LC-QuAD2 did not transfer well.** General Text-to-SPARQL data did not match the ORKG template structure and produced poor outputs.

3. **Prompt length alone was not enough.** A large prompt with many rules was less helpful than a compact prompt with structured metadata.

4. **Decoding settings mattered.** Constraints such as `no_repeat_ngram_size` and `repetition_penalty` harmed SPARQL generation.

5. **Paraphrase augmentation helped.** Using paraphrased questions as additional training inputs improved robustness.

6. **Metadata-aware prompting improved structural behavior.** Adding `answer_type`, `query_shape`, `special_types`, and `complexity_level` reduced some hallucinations and improved several structural metrics.

7. **Postprocessing was necessary.** Even after fine-tuning, small SPARQL syntax errors prevented execution. Rule-based postprocessing dramatically improved endpoint executability.

8. **Execution is not correctness.** A query can execute successfully and still return the wrong answer. Execution success is only one part of the final evaluation.

---

## 16. Short Summary for Thesis

In this work, I introduced PGMR-lite as an intermediate representation for ORKG Text-to-SPARQL generation. Instead of training T5-base to generate real ORKG identifiers directly, the model generates semantically readable PGMR placeholders, which are later restored to ORKG-SPARQL using a deterministic mapping. After repairing and validating the dataset, I trained T5-base on paraphrase-augmented PGMR-lite data. A metadata-aware prompt further improved the model by providing answer type, query shape, special types, and complexity information. The final model still required rule-based postprocessing to repair systematic syntax issues such as missing WHERE braces, misplaced ORDER BY/GROUP BY clauses, and malformed OPTIONAL patterns. After postprocessing and restore, the final PGMR-lite approach achieved high endpoint executability on the validation set and provided a transparent pipeline for analyzing model, syntax, and mapping errors separately.

