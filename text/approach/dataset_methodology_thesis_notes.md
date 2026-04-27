# Dataset Construction and Curation Process

## 1. Starting Point

The dataset construction process started from a comparatively small manually curated question set.
The initial pool consisted of **127 questions** in total.

- **26 questions** originated from the **EmpiRE-Compass** prompt and template setup.
- **101 questions** were created with the help of **ChatGPT 5.4 Thinking**.

For these 101 additional questions, the natural-language questions were generated first, while the corresponding **gold SPARQL queries were written manually** afterward. This was an important design decision. The goal was to avoid relying on automatically generated SPARQL in the earliest phase and instead ensure that the initial core set had manually controlled gold queries.

This initial set served as the conceptual seed of the later benchmark and training dataset. At this point, however, the dataset was still too small and too narrow to support the broader benchmark, training, and evaluation goals of the thesis.

---

## 2. Motivation for Dataset Expansion

The initial seed set was useful as a starting point, but it was not sufficient for the intended experiments.
Several reasons motivated an explicit dataset expansion process:

1. **The number of questions was too small** for robust benchmarking and especially too small for later fine-tuning experiments.
2. The early seed set did not yet cover the full breadth of:
   - template sections,
   - answer types,
   - SPARQL operators,
   - query shapes,
   - reasoning patterns,
   - and difficulty levels.
3. The dataset needed stronger coverage across the two target template families:
   - `nlp4re`
   - `empirical_research_practice`
4. The dataset needed a clearer distinction between:
   - benchmark-quality items,
   - training-oriented items,
   - and reserve or repair candidates.

Because of this, the dataset work shifted from a purely manual seed-building phase to a more structured **generation-review-selection-validation pipeline**.

---

## 3. Design Principles of the Expansion Process

A number of principles guided the expansion process.

### 3.1 Minimal generation output

One important decision was that generation prompts should return only a **minimal candidate format**.
Instead of asking the model to also assign metadata directly, candidate entries initially contained only:

- `id`
- `question`
- `gold_sparql`
- `family`
- `answer_type`

This reduced the risk that generation quality would be mixed with unreliable metadata labeling. Metadata was intentionally postponed to later processing stages.

### 3.2 Review after generation

Generated candidates were never treated as final immediately.
Instead, they were subjected to structured review steps such as:

- schema checks,
- duplicate checks,
- execution review against the ORKG endpoint,
- manual inspection,
- later paraphrasing,
- and final split construction.

### 3.3 Strong separation of concerns

The workflow was organized into separate phases:

1. generation,
2. review,
3. selection,
4. normalization,
5. deduplication,
6. manual validation,
7. paraphrase generation,
8. distribution analysis,
9. split construction.

This separation was important because many problems were easier to diagnose when each phase had its own artifacts and reports.

---

## 4. Prompting and Batch-Based Expansion

### 4.1 Prompt assembly

The prompt workflow was not based on one single prompt, but on a compositional setup.
Each generation prompt was assembled from:

1. a **family-specific base prompt**,
2. a **wrapper prompt**, and
3. a **run prompt** or **scaled run prompt**.

The base prompt provided the template-specific schema grounding.
The wrapper defined the intended generation behavior, such as:

- answer-type coverage,
- difficult or ambiguous cases,
- missing query components,
- family-specific priority,
- or reserve-pool generation.

The run prompt defined the concrete batch instance, such as:

- batch id,
- wave id,
- family,
- output size,
- and focus of generation.

This setup made the process more modular and more reproducible than relying on one monolithic expansion prompt.

### 4.2 Batch and wave logic

Expansion was performed in multiple **batches** and later in larger **waves**.
Some batches focused on more standard or coverage-oriented cases, whereas others intentionally emphasized:

- higher difficulty,
- stronger multi-hop structure,
- missing-information queries,
- comparison,
- ranking,
- non-factoid queries,
- or special SPARQL components.

Scaled runs with **50 candidates per wave** were especially important, because they allowed the dataset to grow quickly while still remaining reviewable.

---

## 5. Execution Review Against the ORKG Endpoint

A central quality-control step was the **execution review** of generated queries against the ORKG triplestore endpoint:

- `https://www.orkg.org/triplestore`

This phase was critical because syntactic plausibility alone was not sufficient.
A gold query should ideally also be executable and produce a meaningful result profile.

### 5.1 Review logic

Generated candidates were executed and categorized based on the result:

- **green**: executable and returned non-empty results,
- **yellow**: executable but returned empty results,
- **red**: execution error or invalid query behavior.

This proved highly useful in practice.
It created a strong distinction between:

- benchmark-oriented entries,
- reserve or training-oriented entries,
- and problematic candidates that needed repair or exclusion.

### 5.2 What went well

The endpoint-based execution review turned out to be one of the strongest parts of the pipeline.
It made it possible to filter out weak candidates much earlier than a purely manual process would have allowed.
It also provided objective evidence about whether a generated query was technically usable.

### 5.3 What went wrong or was difficult

Several issues appeared during this phase:

- some queries were executable but returned **empty results**, which made them questionable for benchmark use,
- some generated candidates reused or approximated patterns that were syntactically fine but semantically too narrow,
- earlier in development there had already been confusion around endpoint behavior and path consistency,
- and empty-result queries were especially difficult because they are not strictly “wrong”, but often weaker as benchmark items.

This is why the green/yellow distinction became important instead of using only a binary valid/invalid judgment.

---

## 6. Selection Pools: Green and Yellow

After execution review, candidates were merged into larger pools.

### 6.1 Green pool

The **green pool** was treated as the stronger benchmark-oriented pool.
These entries were:

- executable,
- non-empty,
- and generally more trustworthy.

### 6.2 Yellow pool

The **yellow pool** was not discarded.
Instead, it was retained as a secondary pool for:

- reserve use,
- training augmentation,
- and possible later repair.

This was a deliberate design choice.
Yellow entries were considered weaker than green ones, but still potentially useful, especially for training, where perfect benchmark quality is less critical than in the final evaluation set.

### 6.3 Merging and selection outcome

Across the scaled runs, a large pool was created and merged.
A summary selection stage produced:

- **468 green candidates**
- **132 yellow candidates**
- **0 red candidates**

This was a very strong result, because it showed that the large majority of generated items were at least executable and a substantial portion were strong enough for the green pool.

---

## 7. SPARQL Normalization and Exact Deduplication

Once the candidate pools had been merged, the next challenge was to clean and consolidate the resulting dataset.

### 7.1 Prefix normalization

SPARQL queries appeared in slightly different surface forms.
In particular, prefixes were sometimes:

- repeated,
- line-based,
- or inlined at the beginning of a query.

A dedicated normalization step was introduced to remove leading prefix declarations consistently and normalize whitespace. This was necessary for robust deduplication and later structural analysis.

### 7.2 Deduplication

After normalization, the merged dataset was checked for exact duplicates.
The deduplication stage looked at:

- duplicate questions,
- duplicate `gold_sparql`,
- and duplicate question-query pairs.

The numbers were:

- **817 entries before exact deduplication**
- **762 entries after exact deduplication**

Removed duplicates:

- **41** duplicate question-query pairs
- **9** duplicate queries
- **5** duplicate questions

This showed that the generation process had indeed introduced redundancy, especially in scaled runs, but the duplication level was still manageable.

### 7.3 What went well

The normalization-plus-deduplication step substantially improved the cleanliness of the dataset and reduced noise without requiring difficult semantic decisions.

### 7.4 What went wrong or was difficult

The first prefix-removal logic was not sufficient, because some queries contained prefixes inline rather than line by line. That required a revised normalization function.
This was a good example of a small but important engineering issue: seemingly minor formatting differences can significantly affect dataset consolidation.

---

## 8. Manual Review and Query Validation

After deduplication, a manual review phase followed.
This phase was important because execution success alone is not enough to establish benchmark quality.

### 8.1 Manual review goal

The purpose of manual review was to ensure that:

- the question still matched the query,
- the query was semantically plausible,
- the item was not an obvious duplicate or low-value paraphrase,
- and problematic entries were detected before final splitting.

### 8.2 Current status after review

At the end of this step, the working decision was that the queries were **validated**, but not necessarily **final** in the strongest possible sense.
This distinction matters for thesis documentation:

- **validated** means the queries were manually reviewed and accepted for current use,
- **final** would imply an even stronger claim of full maturity and no remaining intended changes.

Using `validated` at this stage was more honest and methodologically appropriate.

---

## 9. Metadata Enrichment and Schema Alignment

The benchmark schema already existed, but the candidate data did not yet contain all final metadata in a reliable form.

A later enrichment step added or revised fields such as:

- `source_dataset`
- `source_id`
- `split`
- `language`
- `query_type`
- `special_types`
- `query_shape`
- `number_of_patterns`
- `query_components`
- `complexity_level`
- `ambiguity_risk`
- `lexical_gap_risk`
- `hallucination_risk`
- `human_or_generated`
- `review_status`
- `gold_status`
- `notes`

### 9.1 Important caveat

Not all metadata values were equally strong from the start.
Some were straightforward to derive, but others initially depended on heuristics and later manual revision.
This is important to document honestly.
The process therefore moved gradually from rough enrichment toward more carefully reviewed metadata.

### 9.2 Source dataset naming

A cleaner source dataset scheme was introduced to distinguish between different origins more transparently:

- `EmpiRE_Compass`
- `Hybrid_NLP4RE`
- `Hybrid_Empirical_Research`
- `Generated_NLP4RE`
- `Generated_Empirical_Research`

This was a useful improvement over collapsing too many entries into only “hybrid” categories.

---

## 10. Paraphrased Questions

An important later addition was the generation of exactly one **paraphrased question** per dataset entry.
The schema already supported `paraphrased_questions`, so this became part of the cleaned working dataset.

### 10.1 Motivation

Paraphrases were useful because they:

- enrich the dataset linguistically,
- improve training usefulness,
- preserve semantic equivalence while increasing surface variation,
- and can later support robustness-oriented evaluation.

### 10.2 Procedure

A dedicated OpenAI-based tool was built to generate one paraphrase per entry under strict rules:

- preserve meaning exactly,
- preserve answer scope,
- do not add or remove constraints,
- do not distort negation, temporal scope, comparison, ranking, or missing-information logic.

### 10.3 Quality control

A sample run on 25 entries was used first.
Initially, problems appeared such as:

- paraphrases identical to the original,
- incomplete responses due to token limits,
- punctuation mismatches.

The tool was then improved with:

- retries,
- stronger validation rules,
- adjusted output-token limits,
- and cost tracking.

### 10.4 Final outcome

For the full dataset:

- **762 total items**
- **761 paraphrases generated automatically**
- **1 item required manual completion**

The total estimated cost was approximately **$0.586**, which was acceptable for the value added.

This was a very successful stage overall.

---

## 11. Distribution Analysis

Once the dataset had been merged, deduplicated, reviewed, validated, and paraphrased, a distribution analysis was created.
This was necessary before designing the final split.

### 11.1 Size and family distribution

Final working dataset size before final split:

- **762 entries**

Family distribution:

- **359** `nlp4re`
- **403** `empirical_research_practice`

### 11.2 Source dataset distribution

- `EmpiRE_Compass`: 22
- `Hybrid_Empirical_Research`: 61
- `Hybrid_NLP4RE`: 39
- `Generated_NLP4RE`: 310
- `Generated_Empirical_Research`: 330

This clearly shows that generated data forms the bulk of the dataset, while EmpiRE-Compass and hybrid entries form a smaller but strategically important subset.

### 11.3 What the analysis revealed

The distribution analysis was helpful because it showed that split decisions could not be made purely by size.
A naïve split would have produced undesirable benchmark characteristics, such as overly narrow answer-type coverage or a train set dominated too strongly by generated-only material.

---

## 12. Split Strategy and Final Dataset Files

### 12.1 General principle

The final split was not intended to be random.
Instead, the goal was to create three subsets with different roles:

- **test** = benchmark-oriented evaluation set,
- **validation** = smaller development/control set,
- **train** = the main learning set.

### 12.2 Intended benchmark principle

A key idea was that the benchmark should prioritize stronger source material.
Therefore, the benchmark-oriented test split emphasized:

- `EmpiRE_Compass`
- `Hybrid_*`

and avoided relying primarily on generated entries.

### 12.3 Important trade-off

This led to one of the most important methodological tensions in the entire process:

- If the test set is defined too strictly by source origin, it may become too narrow in answer-type coverage.
- If it is defined too broadly, it may lose its stronger benchmark character.

This tension became visible during split experiments.
Some split versions were structurally balanced by family, but their answer-type distribution in the benchmark set was highly skewed.
This showed that source-based selection alone is not sufficient.

### 12.4 Final split sizes

The current final split sizes are:

- **train**: 602
- **validation**: 80
- **test**: 80

These sizes are appropriate for the thesis context and offer a reasonable balance between benchmark quality, validation utility, and training volume.

### 12.5 Final export

The process culminated in the creation of three final dataset files:

- `train.json`
- `validation.json`
- `test.json`

These files constitute the practical endpoint of the dataset construction workflow.

---

## 13. Repository and Data-Structure Cleanup

Another important part of the work was the repository cleanup itself.
Over time, many intermediate artifacts had accumulated:

- temporary merged files,
- old normalized files,
- old benchmark versions,
- expansion artifacts,
- prompt artifacts,
- and outdated structure assumptions.

### 13.1 Why cleanup mattered

This was not only a cosmetic issue.
A chaotic repository makes it harder to:

- reproduce results,
- locate the current source of truth,
- maintain scripts,
- and document the process in the thesis.

### 13.2 Structural reorganization

The data structure was cleaned and reorganized into clearer areas such as:

- `sources/`
- `expansion/`
- `working/`
- `reports/`
- `final/`
- `archive/`

Similarly, README files were added or revised to explain active vs. archival directories.

### 13.3 Path-config migration

The path configuration also had to be updated because many default paths still referred to outdated files or structures.
Old config keys and references to no longer active locations were replaced by keys aligned with the new structure.

This step was essential to prevent the tooling from silently pointing to obsolete files.

---

## 14. What Worked Well

Several aspects of the process worked especially well.

### 14.1 Minimal candidate generation format

Restricting generation outputs to only the core fields was a strong decision.
It kept generation simple and avoided contaminating the process with weak early metadata.

### 14.2 Execution review

The execution review against the ORKG endpoint was one of the most effective quality filters in the entire pipeline.
It gave an objective technical signal and made it possible to construct green and yellow pools in a systematic way.

### 14.3 Batch/wave-based scaling

The batch and wave process made it possible to expand the dataset quickly without completely losing control.
This was crucial for scaling from a small initial seed set to a much larger working dataset.

### 14.4 Paraphrase generation after stabilization

Adding paraphrases only after the dataset had been cleaned and validated was a good sequencing decision.
Doing it earlier would likely have propagated noise.

### 14.5 Data cleanup and path cleanup

Cleaning the repository and path configuration was very helpful for reducing confusion and preparing the project for its final thesis phase.

---

## 15. What Went Wrong or Was Difficult

The process also revealed a number of problems and difficulties.
These are important to document honestly.

### 15.1 Early repository chaos

Over time, many intermediate files accumulated and active vs. archival files became difficult to distinguish.
This made it harder to know which dataset file was currently authoritative.

### 15.2 Prefix handling and normalization issues

The first normalization logic did not fully remove prefixes because some queries had inline prefixes instead of line-based prefix declarations.
This had to be fixed.

### 15.3 Heuristic metadata was initially too rough

Some metadata fields were initially filled by crude heuristics, which led to suspicious distributions, especially for:

- `complexity_level`
- `query_shape`
- `special_types`
- risk fields

This showed that some metadata requires more careful revision than simple rule-based bootstrapping can provide.

### 15.4 Empty-result queries

A major difficulty was the treatment of queries that execute successfully but return empty results.
These are not necessarily invalid, but they are weaker benchmark candidates.
This is why the yellow pool had to be retained separately instead of being simply accepted or discarded.

### 15.5 Benchmark split tension

The strongest methodological difficulty in the final phase was split design.
A source-pure benchmark split can easily become distributionally poor, whereas a more balanced benchmark risks including more generated material than originally intended.
This required explicit trade-off reasoning rather than automatic splitting alone.

---

## 16. Final Status of the Dataset Process

At the current stage, the dataset process has achieved the following:

- initial seed questions established,
- large-scale candidate expansion completed,
- endpoint-based execution review completed,
- green and yellow pools constructed,
- merged pool created,
- SPARQL normalized,
- exact deduplication completed,
- manual review completed,
- gold queries treated as validated,
- paraphrases generated and stored,
- dataset distributions analyzed,
- train/validation/test files exported,
- repository structure and path configuration significantly cleaned.

This means the dataset work has moved from an exploratory generation phase into a much more stable and thesis-ready state.

---

## 17. Interpretation for the Thesis

From a thesis perspective, this process demonstrates that benchmark and training dataset construction for text-to-SPARQL in a template-based knowledge graph setting is not only a matter of writing questions and queries.
Instead, it requires a multi-stage curation process involving:

- seed design,
- controlled generation,
- endpoint validation,
- candidate selection,
- normalization,
- deduplication,
- manual review,
- metadata alignment,
- paraphrasing,
- distribution analysis,
- and split design.

The final dataset is therefore not merely a collection of generated examples.
It is the result of repeated filtering, repair, validation, and structural consolidation.

---

## 18. Concise Process Summary

In short, the dataset was built in the following trajectory:

1. Start with **127 manually controlled seed questions**:
   - 26 from EmpiRE-Compass
   - 101 created with ChatGPT 5.4 Thinking, with manually written SPARQL queries
2. Expand the dataset with structured prompt-based generation in batches and waves
3. Execute all generated queries against the ORKG endpoint
4. Separate candidates into green and yellow pools
5. Merge the candidate pools
6. Normalize SPARQL and remove exact duplicates
7. Manually review the resulting dataset
8. Mark gold queries as validated
9. Add paraphrased questions
10. Analyze dataset distributions
11. Create train, validation, and test splits
12. Clean repository structure and path configuration for reproducibility

This staged process provided a practical balance between scale and quality control and forms the methodological foundation of the final dataset used in the thesis.
