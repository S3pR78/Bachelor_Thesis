# Dataset

## 1. Dataset Scope and Role

This work uses a custom dataset for practical Text-to-SPARQL experiments on Open Research Knowledge Graph (ORKG) template data. The dataset is focused on two ORKG template families: `nlp4re` and `empirical_research_practice`. These two families define the practical scope of the experiments and determine the schema grounding, query patterns, and evaluation cases used throughout the thesis.

The dataset is not used for one single purpose only. Instead, it provides the common data basis for several experimental stages: direct prompting with full SPARQL, PGMR-lite prompting with placeholder-based target queries, fine-tuning, validation, ACE playbook construction, and final benchmark evaluation. For that reason, the dataset has to be described on two levels. First, the consolidated master dataset describes the complete validated data basis and its global distribution. Second, the final exported JSON files describe the actual experimental roles of the data, such as training, validation, benchmark evaluation, and ACE development.

This distinction is important because later project steps introduced additional files for paraphrase-augmented training and ACE. These files are not independent new datasets and must not be counted additively. In particular, `train_with_paraphrases.json` is an augmented training variant, while `ace_dev_pool.json` is a composed ACE development pool that intentionally overlaps with other files.

---

## 2. Dataset Construction and Curation Process

### 2.1 Initial Seed Set

The dataset construction process started from a comparatively small manually controlled seed set. The initial pool consisted of 127 questions in total. Of these, 26 questions originated from the EmpiRE-Compass prompt and template setup, while 101 additional natural-language questions were created with the help of ChatGPT 5.4 Thinking.

For the 101 additional questions, only the natural-language side was generated first. The corresponding gold SPARQL queries were then written manually. This was an important methodological decision, because the earliest version of the dataset should not depend on automatically generated SPARQL queries. The initial goal was to establish a manually controlled core set whose gold queries could serve as a trustworthy starting point for later expansion and validation.

However, this seed set was too small for the intended scope of the thesis. It did not provide enough examples for robust benchmarking, fine-tuning, ACE development, or distributional analysis across both target template families. It also did not yet cover enough answer types, SPARQL operators, query phenomena, and template sections.

### 2.2 Motivation for Expansion

The dataset therefore had to be expanded beyond the initial seed set. The main motivation was practical: open-source models need enough training and evaluation data to make fine-tuning and comparative benchmarking meaningful. At the same time, the dataset had to remain sufficiently controlled so that the final benchmark would not become an unreviewed collection of synthetic examples.

The expansion was designed to improve coverage across the two template families, answer types, SPARQL constructs, and question types. It also introduced a clearer distinction between benchmark-oriented examples, training-oriented examples, ACE development material, and reserve or repair candidates.

### 2.3 Generation Strategy

The expansion process was not based on one monolithic generation prompt. Instead, prompts were assembled compositionally from several parts:

1. a family-specific base prompt,
2. a wrapper prompt, and
3. a run prompt or scaled run prompt.

The family-specific base prompt provided grounding in the relevant ORKG template family. The wrapper prompt controlled the generation behavior, such as coverage of answer types, difficult cases, missing query components, or reserve-pool generation. The run prompt defined the concrete batch instance, including batch ID, wave ID, family, output size, and generation focus.

A key design choice was that generated candidate entries initially used a minimal format. Rather than asking the model to generate all metadata fields directly, candidate entries focused on core fields such as `id`, `question`, `gold_sparql`, `family`, and `answer_type`. This reduced the risk of mixing query generation quality with unreliable metadata labeling. Metadata enrichment was intentionally postponed to later processing steps.

### 2.4 Batch- and Wave-Based Expansion

Expansion was performed in multiple batches and later in larger waves. Some batches focused on standard coverage-oriented examples, while others emphasized more difficult cases, multi-hop structures, missing-information questions, comparisons, ranking, non-factoid questions, or special SPARQL components.

The use of scaled runs with larger batches made it possible to increase the dataset size quickly while keeping the process reviewable. This was especially important because the dataset had to support not only final evaluation but also fine-tuning and ACE development.

### 2.5 Execution Review Against the ORKG Endpoint

A central quality-control step was the execution review of generated gold queries against the ORKG triplestore endpoint. This step was necessary because syntactic plausibility alone is not sufficient for Text-to-SPARQL data. A query may look valid but still be semantically too narrow, return no useful result, or fail against the actual endpoint.

Generated candidates were categorized according to endpoint behavior:

| Category | Meaning | Use |
|---|---|---|
| `green` | executable and returned non-empty results | strongest benchmark-oriented candidates |
| `yellow` | executable but returned empty results | reserve, training, or later repair candidates |
| `red` | execution error or invalid query behavior | problematic candidates |

This distinction was useful because empty-result queries are not necessarily syntactically wrong, but they are weaker benchmark items. The green/yellow distinction therefore provided a more nuanced quality signal than a simple valid/invalid decision.

Across the scaled generation runs, the selection stage produced 468 green candidates, 132 yellow candidates, and 0 red candidates. This indicated that the expansion process produced a large number of executable candidates, while still leaving room for quality-based selection.

### 2.6 SPARQL Normalization and Exact Deduplication

After merging the candidate pools, the dataset was normalized and deduplicated. SPARQL queries appeared in different surface forms, especially with respect to prefixes and whitespace. Some queries used prefix declarations line by line, while others included prefixes inline. A normalization step was therefore introduced to remove leading prefix declarations consistently and normalize whitespace.

After normalization, exact duplicates were removed. The deduplication stage considered duplicate questions, duplicate `gold_sparql` queries, and duplicate question-query pairs.

| Deduplication stage | Count |
|---|---:|
| Entries before exact deduplication | 817 |
| Entries after exact deduplication | 762 |
| Removed duplicate question-query pairs | 41 |
| Removed duplicate queries | 9 |
| Removed duplicate questions | 5 |

This step reduced redundancy introduced during scaled generation and improved the cleanliness of the final working dataset. It also showed that the generation process produced some repeated material, but the redundancy level remained manageable.

### 2.7 Manual Review and Query Validation

Execution success alone was not treated as sufficient evidence of benchmark quality. After deduplication, a manual review phase checked whether questions matched their gold queries, whether the queries were semantically plausible, and whether entries were obvious duplicates or low-value paraphrases.

The gold queries were treated as validated for the purposes of the thesis, but not all entries were described as final in the strongest possible sense. This distinction matters: `validated` means that an entry was reviewed and accepted for current use, whereas `final` is reserved for stronger benchmark-oriented material.

### 2.8 Metadata Enrichment

After the core data was stabilized, additional metadata was added or revised. This included fields such as `source_dataset`, `source_id`, `split`, `language`, `query_type`, `special_types`, `query_components`, `human_or_generated`, `review_status`, and `gold_status`.

Not all metadata fields have the same level of reliability. Some fields, such as `family`, `source_dataset`, `answer_type`, `human_or_generated`, `review_status`, and `gold_status`, are used directly in the analysis. Other fields were initially more heuristic. In particular, `number_of_patterns`, `query_shape`, and `complexity_level` are not used as central evidence in the final dataset analysis. The field `query_type` is retained only as a coarse heuristic orientation, not as a fully manual semantic taxonomy.

This caveat is important because it avoids giving the impression that all metadata fields are equally precise.

### 2.9 Paraphrase Generation

After the dataset had been cleaned and validated, one paraphrased question was generated for each entry. This step was introduced only after stabilization, because generating paraphrases earlier would have risked propagating noise from unreviewed examples.

The paraphrase generation followed strict constraints: the paraphrase had to preserve meaning, answer scope, constraints, negation, comparison, ranking, and missing-information logic. A smaller sample run was used first to identify issues such as identical paraphrases, incomplete responses, and punctuation mismatches. The tool was then improved using retries, validation rules, adjusted output-token limits, and cost tracking.

The final master dataset contains 762 entries and 762 paraphrase strings. Earlier notes recorded that 761 paraphrases were generated automatically and one required manual completion. In the current consolidated dataset, every master entry contains a paraphrased question.

### 2.10 Repository and Data-Structure Cleanup

The dataset work also required repository cleanup. Over time, many intermediate artifacts accumulated, including temporary merged files, old normalized files, earlier benchmark versions, expansion artifacts, prompt artifacts, and outdated structure assumptions. The dataset directory was reorganized into clearer areas such as `sources`, `expansion`, `working`, `reports`, `final`, and `archive`.

This cleanup was not merely cosmetic. It was necessary to make the current source of truth easier to identify, reduce confusion, and support reproducibility in the final thesis phase.

---

## 3. Consolidated Master Dataset

The global dataset statistics are based on the consolidated master file:

```text
code/data/dataset/working/master_validated_with_paraphrases_split_v2_no_prefixes.json
```

This file is used for global dataset analysis because it contains the complete validated data basis with metadata and paraphrases.

| Master dataset property | Count |
|---|---:|
| Items | 762 |
| Unique IDs | 762 |
| Duplicate ID count | 0 |
| Entries with paraphrased questions | 762 |
| Entries without paraphrased questions | 0 |
| Total paraphrase strings | 762 |

The master dataset therefore contains 762 unique entries and no duplicate IDs. Each master entry has one paraphrased question. The paraphrased training file is treated separately and is not counted as additional original questions.

---

## 4. Dataset Composition

### 4.1 Template Families

The dataset covers two ORKG template families.

| Template family | Count |
|---|---:|
| `empirical_research_practice` | 403 |
| `nlp4re` | 359 |

The distribution is not perfectly balanced, but both target families are strongly represented. The slightly larger share of `empirical_research_practice` reflects the final composition after expansion, review, and deduplication.

### 4.2 Source Datasets

The field `source_dataset` documents the origin or construction route of each entry.

| Source dataset | Count |
|---|---:|
| `Generated_Empirical_Research` | 330 |
| `Generated_NLP4RE` | 310 |
| `Hybrid_Empirical_Research` | 61 |
| `Hybrid_NLP4RE` | 39 |
| `EmpiRE_Compass` | 22 |

The dataset is dominated by generated examples, which was necessary for scaling the data to a size suitable for training and experimentation. At the same time, hybrid and EmpiRE-derived entries remain important because they represent more manually controlled or benchmark-oriented material.

### 4.3 Human, Hybrid, and Generated Entries

The broader origin of entries is also reflected in the `human_or_generated` field.

| Origin type | Count |
|---|---:|
| `generated` | 640 |
| `hybrid` | 100 |
| `human` | 22 |

This distribution confirms that generated data forms the majority of the dataset. This is acceptable for the purpose of training and broad experimentation, but it also motivates a stricter benchmark design that emphasizes hybrid and human-oriented material more strongly than the training split.

### 4.4 Review and Gold Status

The fields `review_status` and `gold_status` document the review state of the examples and their gold queries.

| Review status | Count |
|---|---:|
| `reviewed` | 640 |
| `approved` | 122 |

| Gold status | Count |
|---|---:|
| `validated` | 640 |
| `final` | 122 |

These fields are especially useful for interpreting the benchmark. The benchmark set is composed only of entries marked as `approved` and `final`, whereas the broader training-oriented data contains many entries marked as `reviewed` and `validated`.

### 4.5 Answer Types

The field `answer_type` describes the expected answer form.

| Answer type | Count |
|---|---:|
| `resource` | 202 |
| `string` | 176 |
| `number` | 144 |
| `date` | 118 |
| `mixed` | 78 |
| `list` | 34 |
| `boolean` | 10 |

The distribution shows that the dataset is not limited to simple entity lookup. It includes resource answers, literal strings, numeric answers, dates, mixed result structures, lists, and Boolean questions. This matters for evaluation because different answer types behave differently under exact matching and result-set comparison.

### 4.6 Heuristic Query-Type Labels

The field `query_type` is retained only as a coarse heuristic distinction between factoid and non-factoid examples.

| Query type | Count |
|---|---:|
| `factoid` | 543 |
| `non_factoid` | 219 |

This field should not be interpreted as a fully manual semantic taxonomy. It was influenced by structural cues and query patterns, such as whether a question involved aggregation, filtering, comparison, ranking, or more complex answer behavior. It is useful for orientation, but not used as a hard evaluation category.

### 4.7 Special-Type Labels

The field `special_types` provides multi-label annotations for recurring query phenomena. Unlike `query_components`, this field is not populated for every entry.

| Coverage of `special_types` | Count |
|---|---:|
| Entries with non-empty list | 497 |
| Entries with empty list | 265 |
| Entries missing field | 0 |

The following table reports label frequencies. Since `special_types` is a multi-label field, the counts are not mutually exclusive classes. A single entry can contribute to several labels.

| Special type | Label count |
|---|---:|
| `multi_hop` | 311 |
| `lookup` | 244 |
| `string_operation` | 170 |
| `typed_lookup` | 95 |
| `aggregation` | 89 |
| `temporal` | 76 |
| `ranking` | 67 |
| `count` | 62 |
| `comparison` | 58 |
| `superlative` | 48 |
| `multi_intent` | 39 |
| `negation` | 38 |
| `missing_info` | 28 |
| `boolean` | 11 |

These labels are useful for describing the structural and semantic variety of the dataset, but they are not treated as a complete taxonomy. In particular, the 265 entries with an empty list show that this annotation is incomplete. The labels are therefore used descriptively rather than as fully reliable disjoint categories.

### 4.8 SPARQL Query Components

The field `query_components` was re-derived deterministically from the gold SPARQL queries. Unlike `special_types`, it is populated for all 762 master entries.

| Coverage of `query_components` | Count |
|---|---:|
| Entries with non-empty list | 762 |
| Entries with empty list | 0 |
| Entries missing field | 0 |

The following table reports component label frequencies. Like `special_types`, this is a multi-label field: a query may contain several SPARQL components.

| Query component | Label count |
|---|---:|
| `SELECT` | 753 |
| `DISTINCT` | 718 |
| `FILTER` | 534 |
| `STR` | 466 |
| `LCASE` | 428 |
| `ORDER_BY` | 404 |
| `OPTIONAL` | 309 |
| `COUNT` | 140 |
| `GROUP_BY` | 70 |
| `CONTAINS` | 60 |
| `BIND` | 49 |
| `EXISTS` | 41 |
| `NOT_EXISTS` | 40 |
| `COALESCE` | 33 |
| `REGEX` | 33 |
| `MAX` | 23 |
| `MIN` | 20 |
| `UNION` | 12 |
| `IF` | 11 |
| `AVG` | 11 |
| `ASK` | 10 |
| `YEAR` | 9 |
| `HAVING` | 9 |
| `BOUND` | 5 |
| `CONSTRUCT` | 4 |
| `SUM` | 3 |
| `LIMIT` | 2 |
| `VALUES` | 1 |

This distribution shows that the dataset contains many queries with filtering, string normalization, ordering, optional patterns, aggregation, grouping, negation-like constructs, and ASK queries. These components are important for later evaluation because they often create failure modes that are not visible from exact query string comparison alone.

---

## 5. Experimental Dataset Files

The final experimental Direct-SPARQL files are stored under:

```text
code/data/dataset/final/
```

The following files are used in the current experimental setup.

| File | Items | Unique IDs | Role |
|---|---:|---:|---|
| `train.json` | 602 | 602 | base fine-tuning data |
| `train_with_paraphrases.json` | 1204 | 1204 | augmented training variant with original and paraphrased questions |
| `validation.json` | 50 | 50 | development/control set |
| `benchmark.json` | 51 | 51 | final benchmark set |
| `ace_playbook.json` | 59 | 59 | examples used for ACE playbook construction |
| `ace_dev_pool.json` | 711 | 711 | composed ACE development pool |

These files must not be counted additively. `train_with_paraphrases.json` contains the 602 training questions plus their paraphrased variants, which results in 1204 training examples. `ace_dev_pool.json` is also not an independent split. It intentionally overlaps with `train.json`, `validation.json`, and `ace_playbook.json`.

The overlap analysis confirms this structure:

| Overlap | Count |
|---|---:|
| `train.json` ∩ `train_with_paraphrases.json` | 602 |
| `train.json` ∩ `ace_dev_pool.json` | 602 |
| `validation.json` ∩ `ace_dev_pool.json` | 50 |
| `ace_playbook.json` ∩ `ace_dev_pool.json` | 59 |

This means that the current dataset organization should be interpreted by experimental role rather than as a single disjoint split table.

---

## 6. Profiles of Key Experimental Files

### 6.1 Training File

The base training file contains 602 entries.

| Property | Distribution |
|---|---|
| Family | 325 `empirical_research_practice`, 277 `nlp4re` |
| Main sources | 287 `Generated_Empirical_Research`, 269 `Generated_NLP4RE`, 38 `Hybrid_Empirical_Research`, 8 `Hybrid_NLP4RE` |
| Main answer types | 174 `resource`, 153 `string`, 127 `number`, 102 `date`, 34 `mixed`, 9 `list`, 3 `boolean` |
| Origin | 556 `generated`, 46 `hybrid` |
| Review/gold status | 556 `reviewed`/`validated`, 46 `approved`/`final` |

The training data is therefore strongly generated-oriented. This is useful for scaling fine-tuning but also means that benchmark performance should not be interpreted as if the benchmark had the same source distribution as the training set.

### 6.2 Paraphrase-Augmented Training File

The file `train_with_paraphrases.json` contains 1204 entries. It doubles the 602 base training examples by adding one paraphrased variant per training question. This file is intended for training augmentation, not for counting additional original questions.

Because the paraphrased entries inherit the same semantic target, the distribution of metadata labels is approximately doubled compared to `train.json`.

### 6.3 Validation File

The validation file contains 50 entries.

| Property | Distribution |
|---|---|
| Family | 26 `empirical_research_practice`, 24 `nlp4re` |
| Main sources | 24 `Generated_Empirical_Research`, 23 `Generated_NLP4RE`, 2 `Hybrid_Empirical_Research`, 1 `Hybrid_NLP4RE` |
| Main answer types | 15 `resource`, 14 `string`, 9 `date`, 9 `number`, 3 `mixed` |
| Origin | 47 `generated`, 3 `hybrid` |

The validation file is a small development/control set. Like the training data, it is mostly generated, so it should not be treated as a strict proxy for the final benchmark.

### 6.4 ACE Playbook File

The file `ace_playbook.json` contains 59 examples used for ACE playbook construction.

| Property | Distribution |
|---|---|
| Family | 31 `nlp4re`, 28 `empirical_research_practice` |
| Sources | 19 `Generated_Empirical_Research`, 18 `Generated_NLP4RE`, 10 `EmpiRE_Compass`, 7 `Hybrid_Empirical_Research`, 5 `Hybrid_NLP4RE` |
| Answer types | 13 `resource`, 12 `list`, 9 `string`, 8 `number`, 7 `date`, 6 `mixed`, 4 `boolean` |
| Origin | 37 `generated`, 12 `hybrid`, 10 `human` |
| Review/gold status | 37 `reviewed`/`validated`, 22 `approved`/`final` |

This file is not used as the final benchmark. Instead, it provides examples for constructing and refining ACE rules.

### 6.5 ACE Development Pool

The file `ace_dev_pool.json` contains 711 entries. It is a composed pool, not a disjoint split.

| Property | Distribution |
|---|---|
| Family | 379 `empirical_research_practice`, 332 `nlp4re` |
| Sources | 330 `Generated_Empirical_Research`, 310 `Generated_NLP4RE`, 47 `Hybrid_Empirical_Research`, 14 `Hybrid_NLP4RE`, 10 `EmpiRE_Compass` |
| Answer types | 202 `resource`, 176 `string`, 144 `number`, 118 `date`, 43 `mixed`, 21 `list`, 7 `boolean` |
| Origin | 640 `generated`, 61 `hybrid`, 10 `human` |
| Review/gold status | 640 `reviewed`/`validated`, 71 `approved`/`final` |

The ACE development pool combines material from several experimental roles. It is useful for rule development and analysis, but it should not be treated as a held-out evaluation set.

---

## 7. Benchmark Profile

The final benchmark file is `benchmark.json`. It contains 51 entries and is intentionally different from the training and validation files.

| Benchmark property | Count |
|---|---:|
| Items | 51 |
| Unique IDs | 51 |
| `nlp4re` | 27 |
| `empirical_research_practice` | 24 |
| `Hybrid_NLP4RE` | 25 |
| `Hybrid_Empirical_Research` | 14 |
| `EmpiRE_Compass` | 12 |
| `approved` | 51 |
| `final` | 51 |

The benchmark answer types are concentrated in more complex output forms.

| Benchmark answer type | Count |
|---|---:|
| `mixed` | 35 |
| `list` | 13 |
| `boolean` | 3 |

The benchmark differs from the training split in several important ways. It contains no large generated-only source group and is composed of hybrid and EmpiRE-derived material. All benchmark entries are marked as `approved` and `final`. This makes the benchmark smaller but stricter than the training and validation files.

This distinction matters for later result interpretation. A model may perform better on training-like or validation-like examples because those files are more generated-heavy and contain many simpler answer types. The benchmark is designed to test a more controlled and more demanding subset.

---

## 8. Direct-SPARQL and PGMR-lite Representations

The dataset exists in two target-query representations.

| Representation | Target field | Description |
|---|---|---|
| Direct-SPARQL | `gold_sparql` | full SPARQL with real ORKG IDs |
| PGMR-lite | `gold_pgmr_sparql` | SPARQL-like query with `pgmr:` and `pgmrc:` placeholders |

The Direct-SPARQL representation is the original target format. It requires models to generate real ORKG predicates, classes, and resources, such as `orkgp:` and `orkgc:` identifiers. This is difficult for smaller open-source models because it combines structural query generation with memorization of many opaque IDs.

The PGMR-lite representation reduces this ID burden. It replaces real ORKG IDs with semantically meaningful placeholders using `pgmr:` and `pgmrc:` prefixes. These placeholders are then restored to executable ORKG SPARQL using family-specific memory files under:

```text
code/data/orkg_memory/templates/
```

The purpose of PGMR-lite is not to change the semantic target, but to separate structural query generation from exact ORKG ID memorization.

### 8.1 PGMR-lite Completeness

The final PGMR-lite files are stored under:

```text
code/data/dataset/pgmr/final/
```

The current analysis shows that PGMR-lite is complete for the final experimental files.

| PGMR-lite file | Items | With `gold_pgmr_sparql` | With unmapped terms |
|---|---:|---:|---:|
| `train.json` | 602 | 602 | 0 |
| `train_with_paraphrases.json` | 1204 | 1204 | 0 |
| `validation.json` | 50 | 50 | 0 |
| `benchmark.json` | 51 | 51 | 0 |
| `ace_playbook.json` | 59 | 59 | 0 |
| `ace_dev_pool.json` | 711 | 711 | 0 |

This is important for interpreting PGMR-lite experiments. If a PGMR-lite model performs poorly, the cause is unlikely to be missing placeholder mappings in the final dataset files, because all final PGMR-lite entries contain `gold_pgmr_sparql` and none have unmapped terms.

---

## 9. Interpretation for Evaluation

The dataset has several properties that directly affect later model evaluation.

First, the training data is much more generated-oriented than the benchmark. This makes the benchmark a stricter test of generalization. It is not simply a random subset of the training distribution, but a smaller and more quality-oriented evaluation file.

Second, the answer-type distribution is diverse. The dataset includes resource, string, number, date, mixed, list, and Boolean answers. This motivates answer-level metrics that go beyond query-string exact match. For example, a query can be syntactically different from the gold query but still return the same answer, or it can use similar triple patterns but project the wrong variable.

Third, the SPARQL component analysis shows that many queries include constructs such as `FILTER`, `ORDER_BY`, `OPTIONAL`, `COUNT`, `GROUP_BY`, `NOT_EXISTS`, and `ASK`. These constructs introduce several common failure modes: wrong projection variables, missing label columns, incorrect aggregation, wrong grouping, over-restrictive filters, and incorrect handling of optional information.

Fourth, `special_types` provide useful evidence of recurring query phenomena such as multi-hop reasoning, lookup, string operations, aggregation, temporal questions, ranking, comparison, negation, missing information, and Boolean questions. However, these labels are incomplete and multi-label, so they are used cautiously.

These properties motivate the use of evaluation metrics beyond exact query matching. In particular, answer-level metrics such as Answer Cell Value F1 and KG Reference F1 are better aligned with the practical behavior of Text-to-SPARQL systems. They make it possible to distinguish between structural errors, projection errors, wrong KG references, and answer-level mismatches.

---

## 10. Summary

The final dataset is the result of a multi-stage curation process rather than a simple collection of generated examples. It started from a manually controlled seed set, was expanded through structured prompting, filtered through endpoint-based execution review, normalized, deduplicated, manually reviewed, enriched with metadata, extended with paraphrases, and reorganized into experimental files for training, validation, benchmarking, ACE, and PGMR-lite experiments.

The consolidated master dataset contains 762 unique entries and 762 paraphrases. It covers two ORKG template families, multiple answer types, several source categories, and a broad range of SPARQL components. The final benchmark is intentionally smaller and stricter than the training data, while the PGMR-lite representation provides a second target format that reduces ORKG ID complexity for local models.

For the thesis, the dataset should therefore be understood as both a methodological contribution and an experimental foundation. It provides the controlled data basis required to compare Direct-SPARQL prompting, PGMR-lite prompting, fine-tuning, and ACE-based improvement strategies for open-source Text-to-SPARQL models on ORKG templates.
