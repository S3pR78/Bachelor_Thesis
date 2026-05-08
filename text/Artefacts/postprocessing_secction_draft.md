# Postprocessing of PGMR-lite Queries

The evaluation pipeline includes a dedicated postprocessing step for PGMR-lite queries. Although this step is technically located in the PGMR-lite path, its main motivation was not a general weakness of the PGMR-lite representation itself. The need for this repair stage emerged primarily from the behaviour of T5 in the PGMR-lite setting. This issue was most visible in the T5 PGMR-lite outputs inspected during development, whereas the larger instruction-tuned causal language models, such as Qwen2.5-Coder and Mistral, more often produced syntactically complete query structures. In particular, T5 sometimes generated plausible triple patterns and correct-looking query fragments, but omitted required SPARQL braces around `WHERE`, `OPTIONAL`, or `FILTER NOT EXISTS` blocks. Such outputs could not be executed directly, even though parts of the intended query structure were visible.

The purpose of postprocessing is therefore not to semantically correct model predictions, but to reduce a specific class of syntax-related failures observed in the T5-based PGMR-lite pipeline. The postprocessor attempts to make clearly recognizable malformed outputs executable where possible. It does not try to infer the intended query from scratch, and it does not repair wrong predicates, wrong classes, wrong joins, wrong answer variables, or missing semantic constraints. Instead, it addresses recurring local syntax artifacts that prevent otherwise interpretable outputs from passing through restoration and execution.

In the benchmark evaluation runner, this postprocessing step is applied only when the prediction format is `pgmr_lite`. Direct-SPARQL outputs generated with the Empire Compass prompting strategy are not repaired by this PGMR postprocessor in the benchmark evaluation pipeline. For PGMR-lite, the processing order is as follows: first, the raw model output is obtained; second, the PGMR-lite postprocessor is applied; third, PGMR placeholders are restored to ORKG identifiers using the template memory; fourth, a second postprocessing pass is applied after restoration; and fifth, the restored query is executed and used for metric computation if restoration succeeds. The benchmark outputs store these stages separately, including the raw model output, the postprocessed PGMR query, the restored query, and the final extracted query used for execution. This is important because the evaluated query is not always identical to the raw model output.

A typical T5 output motivating this step is shown below. The generated query contains a recognizable structure and plausible PGMR placeholders, but the `WHERE` clause and the `OPTIONAL` label pattern are not properly braced:

```sparql
SELECT DISTINCT ?metricLabel WHERE
?paper pgmr:has_contribution ?contribution .
?contribution a pgmrc:nlp4re_contribution .
?contribution pgmr:evaluation ?evaluation .
?evaluation pgmr:evaluation_metric ?metric .
OPTIONAL ?metric rdfs:label ?metricLabel .
ORDER BY ?metricLabel
```

After postprocessing, the same output is transformed into a syntactically regular PGMR-lite query:

```sparql
SELECT DISTINCT ?metricLabel WHERE {
  ?paper pgmr:has_contribution ?contribution .
  ?contribution a pgmrc:nlp4re_contribution .
  ?contribution pgmr:evaluation ?evaluation .
  ?evaluation pgmr:evaluation_metric ?metric .
  OPTIONAL { ?metric rdfs:label ?metricLabel . }
}
ORDER BY ?metricLabel
```

This example illustrates the intended role of the postprocessor. It does not replace the model output with a new query, but repairs local syntax around an already recognizable structure. The generated predicates, classes, variables, and joins remain those produced by the model.

The implemented repairs can be summarized as follows. The table is intentionally methodological rather than code-oriented: it describes the type of generated artifact and the conservative normalization applied before restoration and execution.

| Repair category | Typical generated artifact | Conservative postprocessing action |
| --- | --- | --- |
| Markdown and whitespace cleanup | Code fences or irregular spacing around the query | Remove presentation artifacts and normalize whitespace. |
| Missing `WHERE` braces | `WHERE` followed by a bare graph pattern | Wrap the recognizable body in `WHERE { ... }` while keeping solution modifiers outside. |
| Bare one-triple `OPTIONAL` | `OPTIONAL ?s ?p ?o .` | Rewrite as `OPTIONAL { ?s ?p ?o . }`. |
| Misplaced solution modifiers | `ORDER BY`, `GROUP BY`, or similar modifiers inside the `WHERE` body | Move recognized solution modifiers outside the graph pattern. |
| Malformed `FILTER NOT EXISTS` | `FILTER NOT EXISTS` followed by an unbraced triple chain | Wrap the directly following connected triple-pattern chain in `{ ... }`. |
| Malformed regex equality | `FILTER(REGEX(A = B))` | Rewrite as a plain equality filter `FILTER(A = B)`. |
| Mandatory output labels | Output-only `rdfs:label` triple | Wrap as `OPTIONAL { ... }` when the label is not used as a constraint. |

The first repair category concerns Markdown and whitespace cleanup. Model outputs may contain fenced code blocks or irregular spacing. These presentation artifacts are removed, and repeated whitespace is normalized. This step is purely textual and does not alter the logical content of the query.

The second category repairs missing `WHERE { ... }` braces. Some T5 outputs contain the keyword `WHERE` followed directly by the graph pattern. Since SPARQL requires the graph pattern to be enclosed in braces, the postprocessor wraps the body in a `WHERE { ... }` block when the structure is locally recognizable. Solution modifiers such as `ORDER BY`, `GROUP BY`, `HAVING`, `LIMIT`, and `OFFSET` are kept outside the `WHERE` block. This avoids turning modifiers into graph-pattern content.

The third category repairs bare one-triple `OPTIONAL` patterns. T5 sometimes generated patterns such as:

```sparql
OPTIONAL ?paper rdfs:label ?paperLabel .
```

The postprocessor rewrites such cases into the valid SPARQL form:

```sparql
OPTIONAL { ?paper rdfs:label ?paperLabel . }
```

This repair is intentionally limited to simple local patterns. It does not construct complex optional graph patterns or infer missing joins.

The fourth category moves misplaced solution modifiers out of the `WHERE` body. Generated queries sometimes place `ORDER BY`, `GROUP BY`, `HAVING`, `LIMIT`, or `OFFSET` before the closing brace of the graph pattern. Since these modifiers belong outside the graph pattern, the postprocessor moves them after the `WHERE` block when the boundary can be identified. This repair affects syntax placement, not the semantic correctness of the modifier itself.

A further repair handles malformed `FILTER NOT EXISTS` blocks. SPARQL requires `FILTER NOT EXISTS` to be followed by a braced graph pattern. However, T5 sometimes generated a bare chain of triples after this expression:

```sparql
FILTER NOT EXISTS ?contribution orkgp:P15124 ?dataAnalysis .
?dataAnalysis orkgp:P56043 ?inferentialStatistics .
```

The postprocessor rewrites this into:

```sparql
FILTER NOT EXISTS {
  ?contribution orkgp:P15124 ?dataAnalysis .
  ?dataAnalysis orkgp:P56043 ?inferentialStatistics .
}
```

The repair wraps only the directly following connected chain of simple triple patterns. It stops before unrelated constructs such as `OPTIONAL`, `FILTER`, `GROUP BY`, `ORDER BY`, or closing braces. This conservative boundary detection is important because the postprocessor should not accidentally move later query components into the negated block.

Another repair concerns malformed `REGEX` wrappers around equality filters. In some generated outputs, an equality comparison is incorrectly wrapped inside `REGEX`, for example:

```sparql
FILTER(REGEX(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
```

This is not a valid regex call, because SPARQL `REGEX` expects a text expression and a pattern argument. Since the model has already generated an equality comparison, the postprocessor treats the intended constraint as equality and rewrites the expression as:

```sparql
FILTER(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
```

Valid regex calls with comma-separated arguments are not rewritten. The repair therefore targets only the malformed pattern where an equality expression has been incorrectly placed inside a regex wrapper.

The final repair concerns output labels. Query outputs often include `rdfs:label` triples to return human-readable labels alongside resources. If such label triples are mandatory, valid resources may be removed from the result set when a label is missing. Therefore, pure output/helper label triples can be wrapped in `OPTIONAL` blocks:

```sparql
?paper rdfs:label ?paperLabel .
```

becomes:

```sparql
OPTIONAL { ?paper rdfs:label ?paperLabel . }
```

This transformation is only applied when the label variable is not used as a constraint. Labels used in `FILTER`, `BIND`, `HAVING`, or other graph patterns are not optionalized, because in those cases the label is part of the query condition. For example, a venue label used to filter for a specific conference name must remain mandatory.

The design of the postprocessor is conservative. It introduces no new ORKG identifiers, no new PGMR placeholders, no new predicates, no new classes, no new resources, no new joins, and no new domain constraints. It is not a semantic correction system. If the model predicts an incorrect predicate, uses the wrong class, projects the wrong variable, or misses an important join, the postprocessor does not fix the error. It only repairs selected recurring syntax artifacts that were observed in generated outputs, especially from T5.

This has direct implications for evaluation. Postprocessing can improve the Executable Query Rate by making syntactically malformed but structurally recognizable outputs executable after PGMR restoration. If strict answer match or answer value F1 also improves, this indicates that some previously invalid outputs were already semantically close enough to the gold query and failed mainly because of syntax. If only execution improves, then the syntax barrier has been removed, but semantic errors remain. For this reason, postprocessing must be reported transparently: the evaluated query is the transformed query produced by the pipeline, not always the raw model output.

The main limitation is that the postprocessor is heuristic rather than a full SPARQL parser. Ambiguous malformed outputs can be repaired incorrectly, and heavily truncated or severely malformed queries cannot always be repaired safely. The `FILTER NOT EXISTS` chain detection may choose an imperfect boundary in rare cases, and optionalizing labels can be harmful if a label was intended as a mandatory existence constraint but this intention is not visible from local variable usage. The implementation reduces this risk by avoiding label optionalization when the label variable is used in filters or other constraint contexts. Overall, postprocessing should be understood as a narrow syntax-normalization component for the T5-motivated PGMR-lite evaluation path. It reduces selected syntax-related failures, but it is not a replacement for better prompting, fine-tuning, PGMR memory coverage, or model improvements.
