# PGMR-lite: Thesis Notes and Writing Material

Working notes for the bachelor thesis section on **PGMR-lite** in the project:

> *Practical Text-to-SPARQL: A Comparative Study of Approaches for Improving Open-Source LLMs for the Open Research Knowledge Graph (ORKG).*



---

## 1. Role of PGMR-lite in the Thesis

PGMR-lite is one of the practical approaches investigated in this thesis to improve Text-to-SPARQL generation for ORKG templates. It is motivated by the observation that direct SPARQL generation is difficult for open-source language models for two reasons:

1. Fully rendered template-specific prompts can become very long, especially when they contain detailed instructions, schema knowledge, and template-specific query patterns.
2. Direct SPARQL generation requires the model to produce concrete ORKG identifiers such as `orkgp:P57003` or `orkgc:C27001`, which are difficult to infer from the natural-language question and are only weakly semantically transparent.

PGMR-lite addresses these problems by using an intermediate SPARQL-like representation. Instead of asking the model to generate final ORKG-SPARQL directly, the model generates a query with controlled placeholders such as `pgmr:research_paradigm` or `pgmrc:empirical_research_practice_contribution`. These placeholders are later restored to executable ORKG-SPARQL using a template-specific memory.

The core idea is therefore:

```text
Natural-language question
        ↓
PGMR-lite query with semantic placeholders
        ↓
Memory-based restoration
        ↓
Executable ORKG-SPARQL query
        ↓
Execution and evaluation against the ORKG endpoint
```

This means that PGMR-lite does not replace SPARQL. It keeps the structure of SPARQL but abstracts the most difficult ORKG-specific identifiers.

---

## 2. Conceptual Relation to the PGMR Paper

The PGMR paper introduces **Post-Generation Memory Retrieval** as a method for reducing hallucinations in LLM-based SPARQL generation. The central idea is to separate two subtasks:

1. The language model generates the structure of the query.
2. A memory/retrieval component resolves placeholders to real knowledge graph identifiers after generation.

This idea is highly relevant for ORKG Text-to-SPARQL because ORKG identifiers behave similarly to opaque identifiers in other knowledge graphs: they are necessary for executable SPARQL, but they are not easy for a language model to generate reliably from the question alone.

However, PGMR-lite is **not a full reimplementation of the PGMR paper**. It is a practical, template-specific adaptation for this thesis.

| Aspect | Original PGMR | PGMR-lite in this thesis |
|---|---|---|
| Main idea | Separate query-structure generation from URI grounding | Same conceptual separation |
| Intermediate format | SPARQL with placeholders plus generated label/description mapping blocks | SPARQL-like query with controlled `pgmr:` and `pgmrc:` placeholders |
| Grounding method | Retriever over labels/descriptions, e.g. embedding-based memory retrieval | Template-specific ORKG memory with exact matching, aliases, and optional conservative similarity-based resolution |
| Scope | General SPARQL generation over KGQA datasets | Two ORKG template families: `nlp4re` and `empirical_research_practice` |
| Model burden | Generate structure and natural-language placeholder descriptions | Generate structure and semantically named placeholder tokens |
| Practical goal | Reduce URI hallucination and improve query correctness | Reduce prompt complexity, avoid direct ORKG-ID generation, and make outputs easier to restore and evaluate |



PGMR-lite adopts the core PGMR principle of decoupling SPARQL structure generation from knowledge graph identifier grounding. In contrast to the full PGMR framework, this thesis uses a lightweight, template-specific variant: the model generates controlled `pgmr:` and `pgmrc:` placeholders, and a memory-based restoration step maps these placeholders back to ORKG identifiers.

This wording is important because it avoids overclaiming. The thesis should not claim to implement the complete PGMR architecture with generated mapping blocks and embedding-based retrieval. Instead, PGMR-lite should be presented as a PGMR-inspired practical adaptation for ORKG templates.

---

## 3. Motivation: Prompt Length and Seq2Seq Constraints

One major motivation for PGMR-lite is prompt length. The fully rendered Empire-Compass prompts contain detailed template-specific instructions and are useful for strong models, but they are too long for smaller models and especially problematic for sequence-to-sequence models such as T5-base.

For T5, long inputs are not only a conceptual problem. They directly affect memory usage, runtime, and truncation risk. If the prompt already exceeds the practical input length, the model cannot effectively use the complete instruction. Therefore, PGMR-lite was designed as a more compact representation and instruction style.

Measured with the T5 tokenizer, the prompt sizes were:

| Prompt | Characters | Words | T5 tokens |
|---|---:|---:|---:|
| `code/prompts/empire_compass/generated/rendered/nlp4re_prompt.txt` | 37,833 | 4,716 | 14,963 |
| `code/prompts/empire_compass/generated/rendered/empirical_research_prompt.txt` | 43,418 | 5,346 | 17,289 |
| `code/prompts/pgmr_mini/nlp4re_prompt.txt` | 2,144 | 305 | 671 |
| `code/prompts/pgmr_mini/empirical_research_prompt.txt` | 4,260 | 613 | 1,278 |
| `code/prompts/pgmr/nlp4re_prompt.txt` | 3,978 | 385 | 1,623 |
| `code/prompts/pgmr/empirical_research_prompt.txt` | 4,075 | 412 | 1632|

The reduction from full Empire-Compass to PGMR-mini is substantial:

| Family | Full Empire-Compass tokens | PGMR-mini tokens | Approximate reduction |
|---|---:|---:|---:|
| `nlp4re` | 14,963 | 671 | 95.5% |
| `empirical_research_practice` | 17,289 | 1,278 | 92.6% |

This reduction is important for the thesis argument. The point is not that PGMR-lite is always the shortest possible prompt. The point is that PGMR-lite offers a practical compromise: it is much shorter than the full template prompt while still preserving enough template structure to guide the model.

The previously tested `empire_compass_mini` prompts should not be treated as a central method in this section. They were technical experiments to check whether T5 can work with extremely compressed prompts. Since those prompts were too reduced to reliably generate meaningful SPARQL, they can either be omitted from the PGMR-lite section or mentioned briefly as preliminary prompt-length experiments.



The fully rendered Empire-Compass prompts provide rich template-specific information, but their length makes them unsuitable for smaller sequence-to-sequence models such as T5-base. PGMR-lite was therefore introduced as a more compact and structured alternative. It reduces the prompt length by more than 90% compared to the full rendered prompts while avoiding the need for the model to generate opaque ORKG identifiers directly.

---

## 4. Motivation: Avoiding Direct ORKG Identifier Generation

The second core motivation is the difficulty of generating ORKG identifiers directly. In direct SPARQL generation, the model must output identifiers such as:

```sparql
orkgp:P57003
orkgp:P135046
orkgc:C27001
orkgc:C121004
```

These identifiers are required for execution, but they are not naturally recoverable from the question. For example, a question may contain the phrase *research paradigm*, but the model would still need to know that the corresponding ORKG predicate is `orkgp:P57003`.

PGMR-lite replaces these opaque identifiers with semantically meaningful placeholders:

```sparql
pgmr:research_paradigm
pgmr:venue_serie
pgmrc:empirical_research_practice_contribution
pgmrc:nlp_task
```

This changes the task. Instead of memorizing arbitrary identifiers, the model can generate placeholder names that are closer to the natural-language question and the template labels. The exact ORKG identifiers are then restored after generation.

This is especially relevant for smaller open-source models because these models are less likely to have memorized ORKG-specific identifier mappings. PGMR-lite therefore reduces the burden on the model by shifting identifier grounding from parametric model memory to an external, controlled memory.


In direct SPARQL generation, the model has to produce ORKG-specific identifiers that are only weakly related to the surface form of the question. PGMR-lite reduces this burden by replacing such identifiers with semantically meaningful placeholders. This allows the model to focus on generating the query structure and the relevant template concepts, while the exact ORKG identifiers are restored deterministically or semi-automatically afterwards.

---

## 5. PGMR-lite Representation

PGMR-lite keeps the syntax and structure of SPARQL but replaces ORKG-specific identifiers with placeholder namespaces.

| Namespace | Meaning | Example |
|---|---|---|
| `pgmr:` | Template relations / predicates | `pgmr:research_paradigm`, `pgmr:publication_year`, `pgmr:venue_serie` |
| `pgmrc:` | Template classes | `pgmrc:nlp4re_contribution`, `pgmrc:hypothesis`, `pgmrc:data_collection_method` |
| Standard RDF/SPARQL terms | Remain unchanged | `rdfs:label`, `FILTER`, `OPTIONAL`, `ORDER BY`, `SELECT`, `ASK` |

This distinction is important. PGMR-lite does not abstract every part of the query. It only abstracts ORKG-template-specific identifiers. Standard SPARQL and RDF constructs remain unchanged.

This has two advantages:

1. The intermediate query remains close to executable SPARQL and is easy to inspect.
2. The model still learns normal SPARQL structure, while only the difficult ORKG identifiers are replaced by more meaningful placeholders.


PGMR-lite is not a separate query language. It is an intermediate representation that preserves the structure of SPARQL while replacing ORKG-specific classes and predicates with controlled placeholders. Standard SPARQL constructs such as `FILTER`, `OPTIONAL`, `ORDER BY`, and `rdfs:label` remain unchanged.

---

## 6. Semantic Placeholder Design

The placeholders were not chosen as arbitrary technical labels. They were intentionally designed to resemble the natural-language concepts that appear in questions and ORKG template fields.

This is a central design decision. The goal is that a model can infer placeholders from question elements more easily than concrete ORKG identifiers. For example, if a question asks for the *research paradigm*, the placeholder `pgmr:research_paradigm` is much easier to generate than `orkgp:P57003`.

### 6.1 Examples from `empirical_research_practice`

| ORKG identifier | Label | PGMR-lite placeholder | Why it is useful |
|---|---|---|---|
| `orkgc:C28005` | inferential statistics | `pgmrc:inferential_statistics` | Directly reflects the statistical concept |
| `orkgc:C28008` | Hypothesis | `pgmrc:hypothesis` | Matches question terms about hypotheses |
| `orkgc:C29005` | research question answer | `pgmrc:research_question_answer` | Preserves the full template concept |
| `orkgc:C29012` | machine learning | `pgmrc:machine_learning` | Transparent and easy to infer |
| `orkgc:C29030` | research data | `pgmrc:research_data` | Close to questions about reported data |
| `orkgc:C89001` | data collection method | `pgmrc:data_collection_method` | Mirrors natural question wording |
| `orkgp:DATA` | data | `pgmr:data` | Simple and semantically transparent |
| `orkgp:P1005` | method | `pgmr:method` | Can be linked to “data collection method” through aliases |
| `orkgp:P135046` | venue serie | `pgmr:venue_serie` | Represents the venue filter field |

### 6.2 Examples from `nlp4re`

| ORKG identifier | Label | PGMR-lite placeholder | Why it is useful |
|---|---|---|---|
| `orkgp:P29` | publication year | `pgmr:publication_year` | Matches questions using “year” or “published year” |
| `orkgc:C121001` | NLP4RE contribution | `pgmrc:nlp4re_contribution` | Represents the root contribution class |
| `orkgc:C121004` | NLP task | `pgmrc:nlp_task` | Matches questions about NLP tasks |
| `orkgc:C121007` | NLP task output | `pgmrc:nlp_task_output` | Represents output-related task fields |
| `orkgc:C121010` | NLP dataset | `pgmrc:nlp_dataset` | Matches questions about datasets |
| `orkgc:C121011` | NLP data source | `pgmrc:nlp_data_source` | Matches data-source questions |
| `orkgc:C121015` | NLP data type | `pgmrc:nlp_data_type` | Matches questions about data types |
| `orkgc:C121018` | License | `pgmrc:license` | Simple and semantically clear |

The important methodological point is that PGMR-lite does not merely shorten or rename identifiers. It creates a controlled representation that is closer to the language of the questions.


The placeholders were deliberately derived from ORKG template labels and common question terms. This makes them semantically more transparent than numerical ORKG identifiers. For example, `orkgp:P57003` is represented as `pgmr:research_paradigm`, and `orkgc:C121004` is represented as `pgmrc:nlp_task`. This design allows the model to generate placeholders that are closer to the linguistic form of the question, while the exact ORKG identifiers remain recoverable through the memory.

---

## 7. Transformation Example: Gold SPARQL to Gold PGMR-SPARQL

A central part of the method is the transformation of existing gold SPARQL queries into PGMR-lite target queries. This creates the `gold_pgmr_sparql` field used for PGMR-lite prompting and fine-tuning.

The following example is useful for the thesis because it shows that PGMR-lite keeps the SPARQL structure intact while only replacing ORKG-specific identifiers.

### 7.1 Natural-language question

```text
Which papers report which research paradigm?
```

### 7.2 Original gold SPARQL

```sparql
SELECT DISTINCT ?paper ?paperLabel ?researchParadigm ?researchParadigmLabel
WHERE {
    ?paper orkgp:P31 ?contribution .
    ?contribution a orkgc:C27001.
    ?contribution orkgp:P57003 ?researchParadigm .
    ?contribution orkgp:P135046 ?venue .
    ?venue rdfs:label ?venue_name .

    FILTER(?venue_name = "IEEE International Requirements Engineering Conference"^^xsd:string)
    OPTIONAL { ?paper rdfs:label ?paperLabel . }
    OPTIONAL { ?researchParadigm rdfs:label ?researchParadigmLabel . }
}
ORDER BY ?paperLabel ?researchParadigmLabel
```

### 7.3 PGMR-lite target query

```sparql
SELECT DISTINCT ?paper ?paperLabel ?researchParadigm ?researchParadigmLabel
WHERE {
    ?paper pgmr:has_contribution ?contribution .
    ?contribution a pgmrc:empirical_research_practice_contribution.
    ?contribution pgmr:research_paradigm ?researchParadigm .
    ?contribution pgmr:venue_serie ?venue .
    ?venue rdfs:label ?venue_name .

    FILTER(?venue_name = "IEEE International Requirements Engineering Conference"^^xsd:string)
    OPTIONAL { ?paper rdfs:label ?paperLabel . }
    OPTIONAL { ?researchParadigm rdfs:label ?researchParadigmLabel . }
}
ORDER BY ?paperLabel ?researchParadigmLabel
```

### 7.4 Mapping illustrated by the example

| Original ORKG identifier | PGMR-lite placeholder | Meaning |
|---|---|---|
| `orkgp:P31` | `pgmr:has_contribution` | Links the paper to its contribution node |
| `orkgc:C27001` | `pgmrc:empirical_research_practice_contribution` | Root class of the empirical research practice template |
| `orkgp:P57003` | `pgmr:research_paradigm` | Template field for the research paradigm |
| `orkgp:P135046` | `pgmr:venue_serie` | Venue field used for filtering |

The following parts remain unchanged:

```sparql
?venue rdfs:label ?venue_name .
FILTER(?venue_name = "IEEE International Requirements Engineering Conference"^^xsd:string)
OPTIONAL { ?paper rdfs:label ?paperLabel . }
OPTIONAL { ?researchParadigm rdfs:label ?researchParadigmLabel . }
ORDER BY ?paperLabel ?researchParadigmLabel
```

This example supports an important explanation:

> PGMR-lite abstracts ORKG-template-specific identifiers, but it does not remove standard SPARQL semantics. The query still contains variables, filters, optional label retrieval, ordering, and the same overall graph pattern. Therefore, the intermediate representation remains structurally close to the final executable query.

---

## 8. Prompt Design for PGMR-lite

The PGMR-lite prompt does not only define the output format. It also guides the model toward template-aware query construction.

The most important prompt objectives are:

1. Return only the final query.
2. Use only `pgmr:` relations and `pgmrc:` classes for template elements.
3. Include the required contribution pattern.
4. Select the correct query form (`SELECT`, `COUNT`, `ASK`).
5. Plan the path from the contribution node to the requested target.
6. Use full paths through nested template structures.
7. Avoid invalid triples and avoid placing triples inside `FILTER` clauses.

### 8.1 Core instruction excerpt

The following excerpt is especially important:

```text
Before writing the query, internally decompose the question into smaller parts.
Build a private path map from the contribution node to the requested target.
Use this path map to decide which parent nodes and relations are needed.
Do not output your reasoning or the path map.
Output only the final PGMR-lite SPARQL query.
```

This instruction is not meant to produce visible chain-of-thought. Instead, it is a task-structuring instruction. The model should internally identify the path through the ORKG template before writing the query, but the output remains a clean PGMR-lite SPARQL query.

This is important because many ORKG template fields are nested. The model often has to bind an intermediate parent node before it can access the requested target field.

For example, in `empirical_research_practice`, a question about a machine learning metric may require the path:

```text
?contribution -> data analysis -> machine learning -> metric
```

In `nlp4re`, a question about dataset language or format may require the path:

```text
?contribution -> NLP dataset -> nested dataset field
```



The PGMR-lite prompt includes an internal path-planning instruction. This was introduced because many ORKG template fields are not attached directly to the contribution node but are reachable only through intermediate template nodes. The model is therefore instructed to decompose the question internally and plan the path from the contribution to the requested target before generating the final query. The path itself is not returned, which keeps the output directly evaluable.

### 8.2 Required core pattern

For `nlp4re`, the prompt requires:

```sparql
?paper pgmr:has_contribution ?contribution .
?contribution a pgmrc:nlp4re_contribution .
```

For `empirical_research_practice`, the prompt requires:

```sparql
?paper pgmr:has_contribution ?contribution .
?contribution a pgmrc:empirical_research_practice_contribution .
```

This enforces the template-specific root structure. It also reduces the risk that the model generates incomplete queries that directly attach template fields to the paper instead of the contribution.

### 8.3 Path planning hints

The prompt contains compact path hints. These hints are not full examples, but they provide the model with template-level routing information.

Examples for `nlp4re`:

| Question concept | Intended template path |
|---|---|
| evaluation metric | `?contribution -> evaluation -> metric` |
| validation procedure | `?contribution -> evaluation -> validation procedure` |
| algorithm | `?contribution -> implemented approach -> algorithm` |
| NLP task type | `?contribution -> NLP task -> task type` |
| dataset/source/format/language | `?contribution -> NLP dataset -> nested dataset field` |
| year/time | `?paper -> publication year` |

Examples for `empirical_research_practice`:

| Question concept | Intended template path |
|---|---|
| venue | `?contribution -> venue serie` |
| data collection method | `?contribution -> data collection -> method` |
| research data | `?contribution -> data collection -> data` |
| qualitative/quantitative | `?contribution -> data collection -> data -> data type` |
| machine learning algorithm | `?contribution -> data analysis -> machine learning -> algorithm` |
| metric/accuracy | `?contribution -> data analysis -> machine learning -> metric` |
| statistical test | `?contribution -> data analysis -> inferential statistics -> statistical tests` |
| research question | `?contribution -> research question -> question` |
| year/time | `?paper -> publication year` |

These path hints are a compact alternative to long template documentation. They are especially useful for smaller models because they provide structural guidance without requiring the full Empire-Compass prompt.

---

## 9. Memory-based Restoration

After the model generates a PGMR-lite query, the query must be restored to executable ORKG-SPARQL. This restoration is performed using a template-specific memory.

The memory stores mappings between:

- ORKG identifiers,
- template labels,
- canonical PGMR-lite placeholders,
- aliases and placeholder variants.

Conceptually, restoration has three levels:

| Level | Purpose | Example |
|---|---|---|
| Exact mapping | The generated placeholder exactly matches a memory entry | `pgmr:research_paradigm` → `orkgp:P57003` |
| Alias mapping | The generated form matches a known alias or observed variant | `year` / `published year` → `pgmr:publication_year` |
| Similarity-based resolution | The generated placeholder is not known, but is very similar to an existing memory entry | `pgmr:DataSource` → candidate such as `pgmr:dataset_source` |

This multi-level design is important because model outputs are not always perfectly canonical. Smaller models may produce different casing, redundant words, missing underscores, singular/plural variants, or conceptually close placeholder names.


> The restoration step is not limited to strict string replacement. It uses a layered memory-resolution strategy. Exact matches provide the safest mapping, aliases cover known linguistic and model-generated variants, and an optional conservative similarity mechanism can recover from minor placeholder deviations when the intended memory entry is sufficiently clear.

---

## 10. Alias-based Resolution

Aliases are important because the same concept can appear in different linguistic forms. For example, a question may say *year*, *publication year*, or *published year*, while the canonical placeholder is `pgmr:publication_year`.

Examples:

| Canonical placeholder | Aliases / variants | Purpose |
|---|---|---|
| `pgmr:publication_year` | `publication year`, `year`, `published year` | Captures common question wording |
| `pgmr:method` | `data collection method`, `method`, `pgmr:method_method` | Captures both natural labels and observed model variants |
| `pgmrc:nlp_data_type` | `nlp data type`, `pgmrc:nlp_data_type_type` | Handles redundant model-generated forms |
| `pgmrc:data_type` | `data type`, `pgmrc:data_type_type` | Handles label variants and duplication errors |

Aliases therefore serve two purposes:

1. They encode legitimate linguistic alternatives.
2. They capture recurring model-output variants observed during development and evaluation.

This makes the memory more robust without requiring the model to always generate exactly the canonical placeholder.


> Aliases were added to bridge the gap between canonical placeholder names, natural question wording, and recurring model-output variants. This is especially useful for smaller models, which may produce semantically plausible but non-canonical placeholder forms. Alias-based resolution allows such variants to be restored without changing the PGMR-lite representation itself.

---

## 11. Similarity-based Placeholder Resolution

Similarity-based resolution is an optional extension of the memory restore process. Its purpose is to handle unresolved placeholders that are not exact matches and are not covered by aliases, but still strongly resemble an existing memory entry.

This should be explained in the thesis as a **conservative heuristic**, not as a machine-learning retriever and not as a mathematically optimized scoring model.

### 11.1 Why similarity-based resolution is needed

Even with semantically designed placeholders and aliases, a model can generate small variations that are easy for a human to understand but unknown to the memory. Examples include:

```text
pgmr:DataSource
pgmr:data_sources
pgmr:dataset_location
pgmrc:nlp_data_type_type
```

Without similarity-based resolution, such outputs would remain unresolved and the restored SPARQL query would fail or contain leftover PGMR tokens. Similarity-based resolution tries to recover from these minor deviations, but only when the evidence is strong.

The purpose is therefore not to guess arbitrary missing identifiers. The purpose is to improve robustness against small lexical deviations in a controlled placeholder vocabulary.

### 11.2 Normalization before comparison

Before two placeholders are compared, they are normalized. This normalization is important because model-generated placeholders may differ in surface form while still expressing the same concept.

Typical normalization steps include:

- extracting the local name after the prefix,
- splitting CamelCase forms,
- splitting underscores, hyphens, and spaces,
- lowercasing,
- reducing simple plural forms,
- applying selected synonym replacements,
- collapsing repeated adjacent tokens.

For example:

```text
pgmr:DataSource
→ DataSource
→ data source
→ [data, source]
```

A synonym replacement can then align related forms, for example:

```text
data → dataset
url / uri → location
```

The normalized representation makes the comparison less sensitive to formatting and small wording differences.

### 11.3 Token-level Jaccard similarity

The first similarity signal is token-level Jaccard similarity. It compares the sets of normalized tokens from the generated placeholder and a candidate memory placeholder.

The Jaccard similarity is defined as:

```text
Jaccard(A, B) = |A ∩ B| / |A ∪ B|
```

It measures how much the two token sets overlap.

Example:

```text
A = {data, source}
B = {dataset, source}
```

After synonym normalization, these sets may become highly similar. This is useful because PGMR-lite placeholders are intentionally built from meaningful semantic components such as:

```text
research, question, data, collection, method, metric, publication, year
```

Jaccard similarity answers the question:

> Do the generated placeholder and the memory candidate contain the same conceptual building blocks?

This makes it robust to superficial formatting differences such as underscores, capitalization, or hyphens. It also works well for a controlled placeholder vocabulary, where individual tokens are meaningful.

### 11.4 Sequence-level string similarity

The second signal is sequence-level string similarity. This compares the normalized placeholder strings as ordered sequences of characters.

This is necessary because token overlap alone ignores order and surface structure. For example:

```text
data_collection_method
method_data_collection
```

These two strings contain similar tokens, but their order differs. In a template setting, order can carry useful information because it often reflects a path or a compound concept.

Sequence similarity answers the question:

> Do the two normalized placeholders look similar as ordered strings?

It complements Jaccard similarity by adding sensitivity to ordering and spelling. This helps distinguish placeholders that share some tokens but refer to different concepts.

### 11.5 Combined score and weighting

The final similarity score combines both signals:

```text
score = 0.55 * token_jaccard
      + 0.45 * sequence_ratio
      + substring_bonus
      + exact_bonus
```

The weighting is a practical heuristic. It is not claimed to be mathematically optimal. The reason for giving token-level Jaccard similarity slightly more weight is that PGMR-lite placeholders are designed around semantic components. If two placeholders share the same meaningful parts, this is a strong signal that they refer to the same template concept.

At the same time, sequence similarity receives almost equal weight. This is important because placeholders are not unordered bags of words. Their order and surface form can still help distinguish related concepts. For example, `data_type`, `data_source`, and `research_data` share tokens but represent different fields.

The 0.55 / 0.45 split therefore reflects the nature of PGMR-lite placeholders:

| Component | What it measures | Why it matters |
|---|---|---|
| `token_jaccard` | Overlap of normalized semantic tokens | Captures whether the same concept words are present |
| `sequence_ratio` | Similarity of normalized strings | Captures order, spelling, and surface structure |
| `substring_bonus` | Whether one normalized form contains the other | Helps with shortened or extended variants |
| `exact_bonus` | Whether normalized token lists match exactly | Strengthens very reliable matches |


> The score gives slightly more weight to token-level overlap than to sequence-level similarity because the placeholders are composed of meaningful template concepts. However, sequence similarity remains nearly equally important because the order and surface form of the placeholder can help disambiguate related template fields. The weighting should therefore be understood as a conservative practical heuristic tailored to a controlled placeholder vocabulary.

### 11.6 Why small bonuses are used

Two small bonuses are added for especially strong evidence:

| Bonus | Motivation |
|---|---|
| `substring_bonus` | A shortened or extended placeholder may still clearly contain the intended concept |
| `exact_bonus` | If the normalized token lists are identical, the candidate is especially reliable |

These bonuses are intentionally small. They should not dominate the score. They only slightly strengthen candidates that are already similar according to the main similarity measures.

For example, if one placeholder contains the other after normalization, this can be a useful signal:

```text
data_type
nlp_data_type
```

The substring relation suggests that the two placeholders are related. However, it should not automatically override the possibility that they refer to different template-specific concepts. This is why the bonus is small and automatic mapping still depends on strict confidence rules.

### 11.7 Why the decision thresholds are conservative

The similarity score alone is not enough to automatically replace a placeholder. PGMR-lite uses conservative decision thresholds because an incorrect automatic mapping can silently change the meaning of the generated query.

The design principle is:

> It is better to leave an uncertain placeholder unresolved than to restore it to the wrong ORKG identifier.

This is especially important in Text-to-SPARQL evaluation. A wrong mapping can produce an executable query that looks syntactically correct but answers a different question.

The decision logic distinguishes three cases:

| Case | Interpretation | Desired behavior |
|---|---|---|
| Very high score and clear margin | The generated placeholder almost certainly refers to one memory entry | Automatic mapping |
| Plausible score but not enough confidence | The placeholder may refer to a memory entry, but ambiguity remains | Suggestion for manual review |
| Low score | No reliable memory candidate | Leave unresolved |

The threshold values support this conservative behavior:

| Threshold | Value | Methodological reason |
|---|---:|---|
| Auto-mapping threshold | `0.90` | Requires very strong similarity before silently changing the query |
| Minimum margin | `0.08` | Ensures the best candidate is clearly better than the second-best candidate |
| Suggestion threshold | `0.75` | Allows plausible cases to be surfaced without automatically modifying the query |

The high auto-mapping threshold (`0.90`) reflects that automatic restoration should only occur when the resolver is very confident. Since PGMR-lite placeholders are controlled and semantically designed, truly equivalent variants should usually receive a high score after normalization. If the score is below this level, the case is more likely to be ambiguous or only partially related.

The margin requirement (`0.08`) is equally important. A high score alone can be misleading when several memory entries share similar tokens. For example, the empirical template may contain related concepts such as:

```text
research_data
data_type
data_collection_method
```

Similarly, `nlp4re` may contain related concepts such as:

```text
nlp_dataset
nlp_data_source
nlp_data_type
```

In such cases, several candidates may be similar. The margin requirement prevents automatic mapping when the best candidate is only slightly better than another plausible candidate.

The suggestion threshold (`0.75`) is lower because suggestions do not change the query automatically. They are useful for manual inspection and memory improvement. If a generated placeholder repeatedly appears as a high-scoring suggestion, it can be added as an alias or placeholder variant later.


> The similarity resolver is intentionally conservative. Automatic mapping requires both a high absolute score and a sufficient margin over the second-best candidate. This prevents ambiguous placeholders from being silently mapped to the wrong ORKG identifier. Lower-confidence matches are retained as suggestions for manual review, which supports iterative improvement of the memory without compromising the reliability of automatic restoration.

---

## 12. How Similarity Resolution Fits into PGMR-lite

Similarity-based resolution should not be presented as the main contribution by itself. It is a supporting mechanism within PGMR-lite.

Its role is to make the intermediate representation robust enough for practical model outputs. The overall logic is:

1. Semantically meaningful placeholders make generation easier.
2. Exact memory mappings restore canonical placeholders safely.
3. Aliases handle expected linguistic and model-output variants.
4. Similarity resolution handles minor unexpected deviations conservatively.
5. Uncertain cases remain unresolved or become suggestions instead of being guessed.

This makes PGMR-lite practical for real model outputs while still preserving traceability.

Similarity-based resolution complements the controlled placeholder design. It does not replace the memory and does not attempt open-ended semantic retrieval. Instead, it acts as a conservative repair mechanism for minor deviations in model-generated placeholder names. This is important for smaller models, where outputs may be semantically close but not exactly identical to the canonical memory entries.

---

## 13. Restore and Evaluation Workflow

The PGMR-lite evaluation workflow can be described as follows:

```text
1. The model receives a question and a PGMR-lite prompt.
2. The model generates a PGMR-lite SPARQL query.
3. The restore step maps PGMR-lite placeholders back to ORKG identifiers.
4. The restored query is executed against the ORKG SPARQL endpoint.
5. The result is compared with the gold query result using execution-based metrics.
```

This workflow is important because the model is not evaluated only by string similarity. The final restored SPARQL query is executed, and evaluation metrics such as execution success, answer exact match, answer F1, answer cell value F1, and KG-reference F1 can be computed.



> PGMR-lite outputs are not final answers by themselves. They become executable only after the memory-based restoration step. The restored SPARQL query is then evaluated in the same execution-based pipeline as direct SPARQL outputs. This allows PGMR-lite to be compared with direct generation approaches using the same downstream evaluation criteria.

---

## 14. Advantages of PGMR-lite

PGMR-lite has several advantages in the context of this thesis.

### 14.1 Reduced prompt complexity

Compared to the fully rendered Empire-Compass prompts, PGMR-lite substantially reduces prompt length. This is particularly relevant for T5-base and other smaller models.

### 14.2 More semantically transparent target representation

Instead of opaque ORKG identifiers, the model generates readable placeholders that resemble template labels and question terms.

### 14.3 Separation of generation and grounding

The model focuses on query structure and template concepts, while the memory handles ORKG identifier grounding.

### 14.4 Better inspectability

PGMR-lite queries are easier to inspect than raw ORKG-ID-heavy SPARQL because placeholders reveal the intended template concepts.

### 14.5 Robustness through aliases and similarity resolution

Aliases and conservative similarity resolution make the approach more tolerant of realistic model-output variation.

---

## 15. Limitations of PGMR-lite

The limitations should be clearly stated. This makes the methodology more credible.

### 15.1 PGMR-lite does not fix wrong query structure

If the model chooses the wrong path through the template, the restore step cannot automatically correct the query. For example, if a metric is attached directly to the contribution although it should be nested under a machine-learning node, the placeholders may still be valid but the structure will be wrong.

### 15.2 The approach depends on memory coverage

If a placeholder or its intended ORKG identifier is not represented in the memory, restoration can fail. This can lead to unresolved PGMR tokens or missing mappings.

### 15.3 Similarity resolution is lexical, not semantic retrieval

The similarity mechanism is based on normalized token overlap and string similarity. It is not an embedding-based semantic retriever. Therefore, it works best for small lexical deviations but cannot reliably resolve conceptually related placeholders with very different wording.

### 15.4 Conservative thresholds may leave some placeholders unresolved

The conservative design reduces false mappings but may also leave some potentially correct mappings unresolved. This is acceptable for reliability, but it means that memory improvement and alias expansion remain important.

### 15.5 PGMR-lite is template-specific

The method relies on known template families and curated memory files. It is therefore not a fully generic SPARQL generation method for arbitrary knowledge graphs.

A possible thesis formulation:

> PGMR-lite improves the controllability of SPARQL generation, but it does not eliminate all sources of error. The model still has to generate the correct query structure, and the restore step depends on the completeness and quality of the template memory. Moreover, the similarity resolver is deliberately lexical and conservative; it can repair small placeholder deviations but cannot replace a full semantic retrieval system.

---

## 16. Suggested Structure for the Final Thesis Section

A good final PGMR-lite section could be structured like this:

```text
3.x PGMR-lite
  3.x.1 Motivation
        - long full prompts
        - ORKG identifier difficulty
        - relevance for smaller and seq2seq models

  3.x.2 Relation to PGMR
        - structural generation vs. identifier grounding
        - explanation that this thesis uses a lightweight adaptation

  3.x.3 PGMR-lite Representation
        - pgmr:/pgmrc: namespaces
        - standard SPARQL constructs remain unchanged
        - semantic placeholder design

  3.x.4 Transformation of Gold Queries
        - gold_sparql -> gold_pgmr_sparql
        - include research paradigm example

  3.x.5 Prompt Design
        - required core
        - query form rules
        - private path-map instruction
        - path hints for nested template structures

  3.x.6 Memory-based Restoration
        - exact mapping
        - alias mapping
        - similarity-based placeholder resolution
        - conservative thresholds and manual suggestions

  3.x.7 Limitations
        - wrong structure cannot be fixed by restore
        - memory coverage matters
        - similarity is lexical, not semantic retrieval
        - template-specific nature of the approach
```

---

## 17. Strong Sentences for Later Use

The following sentences can be reused or adapted in the final thesis text.

### Motivation

> PGMR-lite was introduced as a practical response to two limitations of direct ORKG-SPARQL generation: the length of fully rendered template prompts and the difficulty of generating opaque ORKG identifiers directly.

### Placeholder representation

> The placeholders are intentionally semantically transparent. They are derived from template labels and common question terms, allowing the model to generate concept names such as `pgmr:research_paradigm` instead of opaque identifiers such as `orkgp:P57003`.

### Prompt design

> The prompt does not only specify the output format; it also encourages internal path planning through the template structure. This is necessary because many target fields are reachable only through intermediate nodes.

### Memory restoration

> The restoration step transfers identifier grounding from the model’s parametric memory to an external template memory. This makes the mapping explicit, inspectable, and easier to update.

### Similarity resolution

> Similarity-based resolution is used as a conservative repair mechanism for minor placeholder deviations. It is deliberately thresholded to avoid silently mapping ambiguous placeholders to incorrect ORKG identifiers.

### Limitation

> PGMR-lite reduces the burden of identifier generation, but it does not remove the need for correct structural query generation. If the model chooses the wrong template path, the restored query can still be executable but semantically incorrect.

---

## 18. Compact Summary

PGMR-lite can be summarized as follows:

> PGMR-lite is a PGMR-inspired intermediate representation for ORKG Text-to-SPARQL. It replaces hard-to-generate ORKG identifiers with semantically meaningful placeholders, reduces prompt length compared to fully rendered template prompts, and restores executable ORKG-SPARQL through a template-specific memory. The memory supports exact mappings, aliases, and optional conservative similarity-based resolution. This makes PGMR-lite especially relevant for smaller open-source models and sequence-to-sequence models such as T5, where prompt length, output regularity, and identifier memorization are major practical constraints.

