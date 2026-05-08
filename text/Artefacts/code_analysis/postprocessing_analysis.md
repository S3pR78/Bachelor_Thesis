# Postprocessing Analysis

This document is a technical analysis of the current query postprocessing logic in the repository. It is intended as working material for a later thesis section, not as the final thesis text.

Scope: PGMR-lite and Direct-SPARQL evaluation/generation paths are considered. ACE-specific logic is intentionally ignored except where file searches reveal unrelated references.

Last synchronized with `code/src/pgmr/postprocess.py`: 2026-05-08. At this point, the implementation contains the six cleanup passes listed in Section 2 and no additional semantic rewriting rules.

## 1. Purpose and Position in the Pipeline

### Facts from the implementation

The central implementation is `code/src/pgmr/postprocess.py`. Its public entry point is:

```python
postprocess_pgmr_query(query: str) -> str
```

In the benchmark evaluation runner, `code/src/evaluate/runner.py`, postprocessing is applied only when `prediction_format == "pgmr_lite"`.

For non-PGMR predictions, including Direct-SPARQL / Empire Compass runs, the runner does not call `postprocess_pgmr_query`. Instead, it calls:

```python
extract_sparql_query(raw_model_output)
```

from `code/src/evaluate/sparql_extraction.py`. That extraction step removes markdown fences, full-line comments, and prefix declarations, then returns the substring beginning at the first SPARQL query form such as `SELECT`, `ASK`, `CONSTRUCT`, or `DESCRIBE`.

For PGMR-lite evaluation, the order in `code/src/evaluate/runner.py` is:

1. Raw model output is passed to `postprocess_pgmr_query`.
2. The postprocessed PGMR-lite query is restored using PGMR memory mappings.
3. The restored ORKG-SPARQL query is passed through `postprocess_pgmr_query` again.
4. If restoration succeeds with no missing mappings and no remaining PGMR placeholders, the restored query becomes `extracted_query`.
5. The extracted/restored query is prepared with ORKG prefixes and optionally executed.

The relevant fields stored in benchmark outputs are:

| Field | Meaning |
| --- | --- |
| `raw_model_output` | The unmodified model output. |
| `pgmr_postprocessed_query` | The PGMR-lite output after postprocessing, before restoration. This is `null` for non-PGMR prediction formats. |
| `pgmr_restored_query` | The restored ORKG-SPARQL query after PGMR placeholder restoration and a second postprocessing pass. |
| `extracted_query` | The query used for execution and most metrics. For Direct-SPARQL this comes from `extract_sparql_query`; for PGMR-lite it is the restored query if PGMR restoration succeeds. |
| `query_execution.query_with_prefixes` | The executable query after prefixes are prepended. |

The manual single-query CLI path in `code/src/main.py` can also apply `postprocess_pgmr_query` when `--postprocess-pgmr` or `--restore-pgmr` is used.

`code/tools/pgmr/restore_and_execute_predictions.py` imports `postprocess_pgmr_query` from `src.pgmr.postprocess` and applies it after restoration. `code/tools/pgmr/evaluate_model_outputs.py` contains an older local postprocessing implementation with only the earlier cleanup rules. The current benchmark runner uses `src.pgmr.postprocess`, not that local tool copy.

### Interpretation

In the main evaluation pipeline, postprocessing is part of the PGMR-lite method rather than a general Direct-SPARQL cleanup stage. It acts before PGMR restoration to make the placeholder query more regular, and again after restoration to clean up syntax that may remain in the restored SPARQL string. Direct-SPARQL outputs are only extracted from the model response; they are not repaired by the PGMR postprocessor in the benchmark runner.

## 2. Implemented Postprocessing Rules

The postprocessor first strips markdown fences and normalizes whitespace. It then applies a sequence of small rewrite functions:

```python
add_missing_where_braces
wrap_bare_optional_patterns
repair_malformed_filter_not_exists
normalize_malformed_regex_equality_filters
move_solution_modifiers_outside_where
wrap_output_label_triples
```

Finally, whitespace and markdown fences are normalized again.

### Existing baseline cleanup rules

These rules existed before the latest limited patch and remain part of the current implementation.

#### Markdown and whitespace cleanup

Problem pattern: model output can contain markdown fences or irregular whitespace.

Repair rule: remove leading/trailing fenced code blocks, for example fences marked as `sparql`, and collapse repeated whitespace to single spaces.

Example:

````text
```sparql
SELECT ?paper WHERE {
  ?paper pgmr:has_contribution ?contribution .
}
```
````

becomes:

```sparql
SELECT ?paper WHERE { ?paper pgmr:has_contribution ?contribution . }
```

Conservative aspect: this only removes presentation wrappers and whitespace. It does not change identifiers, triple patterns, filters, projections, or joins.

Intentionally not repaired: malformed SPARQL that requires semantic interpretation is not repaired by this rule.

#### Missing `WHERE { ... }` braces

Problem pattern: model output contains `WHERE` followed by a bare body.

Repair rule: if `WHERE` exists but is not followed by `{`, the postprocessor wraps the body in braces. Solution modifiers such as `ORDER BY`, `GROUP BY`, `HAVING`, `LIMIT`, and `OFFSET` are split off so they remain outside the `WHERE` body.

Before:

```sparql
SELECT ?paper WHERE ?paper pgmr:has_contribution ?contribution . ORDER BY ?paper
```

After:

```sparql
SELECT ?paper WHERE { ?paper pgmr:has_contribution ?contribution . } ORDER BY ?paper
```

Conservative aspect: the rule only triggers when `WHERE` is present and no opening brace follows it.

Intentionally not repaired: nested or deeply malformed query bodies are not parsed into a full SPARQL AST.

#### Bare `OPTIONAL` triple patterns

Problem pattern: model output sometimes emits `OPTIONAL ?s ?p ?o .` instead of `OPTIONAL { ?s ?p ?o . }`.

Repair rule: a simple one-triple optional pattern is wrapped in braces.

Before:

```sparql
OPTIONAL ?paper rdfs:label ?paperLabel .
```

After:

```sparql
OPTIONAL { ?paper rdfs:label ?paperLabel . }
```

Conservative aspect: the regex targets a single variable-subject, prefixed-predicate, variable-object triple. It does not try to consume arbitrary graph patterns.

Intentionally not repaired: multi-triple optional blocks, semicolon property lists, and more complex optional graph patterns are not constructed.

#### Solution modifiers inside `WHERE`

Problem pattern: solution modifiers can appear inside the `WHERE` braces.

Repair rule: the postprocessor finds the top-level `WHERE` body, splits out modifiers such as `GROUP BY`, `ORDER BY`, `HAVING`, `LIMIT`, and `OFFSET`, and places them after the closing `}`.

Before:

```sparql
SELECT ?paper WHERE { ?paper pgmr:has_contribution ?contribution . ORDER BY ?paper }
```

After:

```sparql
SELECT ?paper WHERE { ?paper pgmr:has_contribution ?contribution . } ORDER BY ?paper
```

Conservative aspect: only known solution modifier keywords are moved.

Intentionally not repaired: the rule does not validate whether the modifier itself is semantically correct.

### 2.1 Repair malformed `FILTER NOT EXISTS` blocks

#### Problem pattern

Some T5/PGMR-lite outputs generate `FILTER NOT EXISTS` without the required graph-pattern braces:

```sparql
FILTER NOT EXISTS ?contribution orkgp:P15124 ?dataAnalysis .
?dataAnalysis orkgp:P56043 ?inferentialStatistics .
?inferentialStatistics orkgp:P35133 ?statisticalTechnique .
OPTIONAL { ?paper rdfs:label ?paperLabel . }
```

This is syntactically invalid SPARQL, but the intended negated pattern is structurally recognizable.

#### Repair rule

The function `repair_malformed_filter_not_exists` wraps a simple connected triple chain after `FILTER NOT EXISTS`:

```sparql
FILTER NOT EXISTS {
  ?contribution orkgp:P15124 ?dataAnalysis .
  ?dataAnalysis orkgp:P56043 ?inferentialStatistics .
  ?inferentialStatistics orkgp:P35133 ?statisticalTechnique .
}
OPTIONAL { ?paper rdfs:label ?paperLabel . }
```

#### How connected triple chains are detected

The code uses `SIMPLE_TRIPLE_PATTERN` to match simple triples of the form:

```sparql
?subject prefixed:predicate ?object .
?subject a prefixed:Class .
?subject prefixed:predicate "literal" .
```

After the first triple, each following triple is accepted only if its subject is the previous triple's object variable. For example:

```sparql
?contribution orkgp:P15124 ?dataAnalysis .
?dataAnalysis orkgp:P56043 ?inferentialStatistics .
?inferentialStatistics orkgp:P35133 ?statisticalTechnique .
```

forms a connected chain because each object variable becomes the next subject.

#### Where the repair stops

The repair stops when:

- the next token begins a block boundary or different construct such as `OPTIONAL`, `FILTER`, `BIND`, `VALUES`, `UNION`, `SERVICE`, `MINUS`, `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `HAVING`, `LIMIT`, `OFFSET`, or `}`;
- the next text is not a simple triple;
- a following triple is not connected to the previous object variable;
- the previous object is not a variable.

This is why the example stops before:

```sparql
OPTIONAL { ?paper rdfs:label ?paperLabel . }
```

#### Why the repair is conservative

The function does not try to infer an arbitrary graph pattern. It consumes only a simple connected chain. If the model output becomes ambiguous, the function stops rather than pulling later clauses into the negated block.

Existing correct blocks are preserved because `FILTER_NOT_EXISTS_PATTERN` explicitly excludes occurrences already followed by `{`:

```sparql
FILTER NOT EXISTS { ?contribution orkgp:P15124 ?dataAnalysis . }
```

is left structurally unchanged apart from global whitespace normalization.

#### Intentionally not repaired

This rule does not repair:

- nested `FILTER NOT EXISTS` blocks;
- graph patterns with semicolon property lists;
- unions or nested optionals inside the negated block;
- missing subjects, predicates, or objects;
- wrong predicates, wrong classes, or wrong contribution paths.

### 2.2 Normalize malformed `REGEX` wrappers around equality filters

#### Problem pattern

Some outputs wrap an equality comparison inside `REGEX`, for example:

```sparql
FILTER(REGEX(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
```

This is not a valid `REGEX` call because SPARQL `REGEX` expects a text expression and a pattern argument, not an equality expression.

#### Repair rule

The function `normalize_malformed_regex_equality_filters` rewrites malformed regex wrappers into plain equality filters:

```sparql
FILTER(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
```

The code scans for `FILTER(` followed by `REGEX(`, finds the matching closing parenthesis for the regex call, and inspects the inner content. It rewrites only when the inner content contains a top-level equality operator and no top-level comma.

#### Why this is treated as equality

The model output already contains both sides of an equality comparison:

```sparql
LCASE(STR(?venueName)) = LCASE("...")
```

The implemented interpretation is therefore that the intended constraint was exact case-insensitive equality, not regex matching. The repair does not convert the expression into `REGEX(A, B)`.

#### Valid regex preservation

Valid regex calls contain a comma-separated argument list, for example:

```sparql
FILTER(REGEX(?label, "abc"))
FILTER(REGEX(LCASE(STR(?label)), "abc"))
```

The helper `_has_top_level_equality_without_comma` returns `False` for these because they contain a top-level comma and no top-level equality. They are preserved.

#### Missing parentheses

The implementation handles the common case where the regex call has a matching close parenthesis but the outer `FILTER(` is missing one close parenthesis. In that case, it uses the regex close as the end of the malformed wrapper and emits a balanced `FILTER(...)`.

It does not perform global parenthesis balancing. If a matching `REGEX(` close cannot be found, the rule does not rewrite.

#### Intentionally not repaired

This rule does not repair:

- valid regex calls;
- malformed regex calls without a recoverable closing delimiter;
- arbitrary broken filter expressions;
- semantic mistakes such as filtering the wrong variable or using the wrong literal.

### 2.3 Wrap pure output `rdfs:label` triples in `OPTIONAL`

#### Problem pattern

Model outputs sometimes emit output label triples as mandatory graph patterns:

```sparql
?paper rdfs:label ?paperLabel .
```

For output/helper labels, the expected query style often uses optional labels:

```sparql
OPTIONAL { ?paper rdfs:label ?paperLabel . }
```

#### Repair rule

The function `wrap_output_label_triples` wraps selected `rdfs:label` triples in `OPTIONAL { ... }`.

Before:

```sparql
SELECT DISTINCT ?paper ?paperLabel WHERE {
  ?paper orkgp:P31 ?contribution .
  ?contribution a orkgc:C27001 .
  ?paper rdfs:label ?paperLabel .
}
ORDER BY ?paperLabel
```

After:

```sparql
SELECT DISTINCT ?paper ?paperLabel WHERE {
  ?paper orkgp:P31 ?contribution .
  ?contribution a orkgc:C27001 .
  OPTIONAL { ?paper rdfs:label ?paperLabel . }
}
ORDER BY ?paperLabel
```

#### When a label triple is treated as pure output/helper label

The implementation detects simple triples matching:

```sparql
?subject rdfs:label ?labelVariable .
```

The label triple is considered optionalizable only if the label variable is not used as a constraint elsewhere.

#### Constraint detection

The code does not optionalize the label triple if the label variable appears in:

- `FILTER`;
- `BIND`;
- `HAVING`;
- another simple triple pattern.

For example, this remains mandatory:

```sparql
?venue rdfs:label ?venueName .
FILTER(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
```

The label is needed as a constraint variable, so optionalizing it could change query semantics.

#### `SELECT` and `ORDER BY`

The implementation allows optionalization when the label variable appears only in projection or ordering contexts such as:

```sparql
SELECT ?paper ?paperLabel
ORDER BY ?paperLabel
```

Interpretation: in this repository's PGMR-lite query style, such variables are treated as output/helper labels rather than constraints.

#### Already optional label triples

Already optional label triples are preserved. The helper `_optional_ranges` finds existing `OPTIONAL { ... }` ranges, and `wrap_output_label_triples` skips label triples inside them.

#### Intentionally not repaired

This rule does not repair:

- label triples with literals instead of variables;
- complex nested patterns;
- cases where a label should be mandatory for semantic reasons but is not detectable from local variable use;
- wrong label variables or wrong resource variables.

## 3. Conservative Design Principles

### Facts from the implementation

The postprocessor rewrites query syntax but does not introduce new ORKG compact identifiers such as `orkgp:P...`, `orkgc:C...`, or `orkgr:R...`. It also does not invent new PGMR placeholders. Existing identifiers and placeholders are preserved unless the PGMR restoration step, outside the postprocessor, maps placeholders to known ORKG identifiers.

The implemented postprocessing rules are limited to recurring syntactic artifacts:

- markdown/code-fence cleanup;
- whitespace normalization;
- missing `WHERE` braces;
- misplaced solution modifiers;
- bare one-triple `OPTIONAL` patterns;
- malformed `FILTER NOT EXISTS` without braces;
- malformed `REGEX` wrappers around equality filters;
- mandatory output/helper `rdfs:label` triples that can be safely optionalized.

### Interpretation

The design is conservative because it repairs local syntax patterns while avoiding domain-specific inference. It does not add template-specific predicates, classes, resources, joins, or constraints. When the code cannot identify a simple pattern, it leaves the text unchanged.

This is important methodologically: postprocessing can make structurally recognizable outputs executable, but it cannot turn a semantically wrong query into a correct one. For example, a query with the wrong ORKG predicate may still execute after postprocessing, but it will still be wrong under answer-based or reference-based metrics.

## 4. Examples and Smoke Tests

### Direct smoke test

Run from the repository root:

```bash
PYTHONPATH=code python - <<'PY'
from src.pgmr.postprocess import postprocess_pgmr_query

q = '''SELECT DISTINCT ?paper ?paperLabel WHERE {
?paper orkgp:P31 ?contribution .
?contribution a orkgc:C27001 .
?contribution orkgp:P135046 ?venue .
?venue rdfs:label ?venueName .
FILTER NOT EXISTS ?contribution orkgp:P15124 ?dataAnalysis .
?dataAnalysis orkgp:P56043 ?inferentialStatistics .
?inferentialStatistics orkgp:P35133 ?statisticalTechnique .
?paper rdfs:label ?paperLabel .
FILTER(REGEX(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
} ORDER BY ?paperLabel'''

print(postprocess_pgmr_query(q))
PY
```

Expected important changes:

```sparql
FILTER NOT EXISTS { ?contribution orkgp:P15124 ?dataAnalysis . ?dataAnalysis orkgp:P56043 ?inferentialStatistics . ?inferentialStatistics orkgp:P35133 ?statisticalTechnique . }
OPTIONAL { ?paper rdfs:label ?paperLabel . }
FILTER(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
```

Expected important non-change:

```sparql
?venue rdfs:label ?venueName .
```

The venue label remains mandatory because `?venueName` is used in the equality filter.

### Assertion-style smoke test

```bash
PYTHONPATH=code python - <<'PY'
from src.pgmr.postprocess import postprocess_pgmr_query

q = '''SELECT DISTINCT ?paper ?paperLabel WHERE {
?paper orkgp:P31 ?contribution .
?contribution a orkgc:C27001 .
?contribution orkgp:P135046 ?venue .
?venue rdfs:label ?venueName .
FILTER NOT EXISTS ?contribution orkgp:P15124 ?dataAnalysis .
?dataAnalysis orkgp:P56043 ?inferentialStatistics .
?inferentialStatistics orkgp:P35133 ?statisticalTechnique .
?paper rdfs:label ?paperLabel .
FILTER(REGEX(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))
} ORDER BY ?paperLabel'''

fixed = postprocess_pgmr_query(q)
print(fixed)

assert 'FILTER NOT EXISTS { ?contribution orkgp:P15124 ?dataAnalysis . ?dataAnalysis orkgp:P56043 ?inferentialStatistics . ?inferentialStatistics orkgp:P35133 ?statisticalTechnique . }' in fixed
assert 'OPTIONAL { ?paper rdfs:label ?paperLabel . }' in fixed
assert 'FILTER(LCASE(STR(?venueName)) = LCASE("IEEE International Requirements Engineering Conference"))' in fixed
assert 'OPTIONAL { ?venue rdfs:label ?venueName . }' not in fixed

print("postprocessing smoke ok")
PY
```

### Unit tests

Focused unit tests exist in:

```text
code/tests/pgmr/test_postprocess.py
```

Run all tests:

```bash
PYTHONPATH=code python -m pytest code/tests -q
```

Run only postprocessing tests:

```bash
PYTHONPATH=code python -m pytest code/tests/pgmr/test_postprocess.py -q
```

Inspection note: in the active environment used for this analysis, `python -m pytest` failed with `No module named pytest`. However, `requirements.txt` lists `pytest==9.0.3`. If pytest is unavailable, use the direct smoke tests above or install the project requirements in the intended environment.

## 5. Interaction with Evaluation Metrics

### Facts from the implementation

In `code/src/evaluate/runner.py`, metrics are computed after PGMR-lite postprocessing and restoration. The value passed as `prediction_query` is `extracted_query`. For PGMR-lite, this is the restored query if restoration succeeds. The value passed as `prediction_pgmr_query` is `pgmr_postprocessed_query`.

The metric runner computes, among others:

- `prediction_execution_success`;
- `answer_exact_match`;
- `answer_value_precision_recall_f1`;
- `kg_ref_match`;
- `predicate_ref_match`;
- `class_ref_match`;
- `resource_ref_match`;
- `query_bleu`;
- `query_rouge1_f1`, `query_rouge2_f1`, `query_rougeL_f1`;
- PGMR ROUGE scores when PGMR metrics are enabled;
- `sparql_structure_match`;
- `primary_error_category`.

LLM judge tooling in `code/tools/evaluate/run_llm_judge.py` can use `pgmr_restored_query` for PGMR runs and `extracted_query` for Direct-SPARQL runs.

### Interpretation by metric type

#### Executable Query Rate

Postprocessing is expected to mainly affect executable query rate. A syntactically broken query with recognizable structure may become parseable and executable after bracing `FILTER NOT EXISTS`, fixing malformed equality filters, moving solution modifiers, or adding missing `WHERE` braces.

#### Strict Answer Match

Strict answer match may improve if the original query was semantically close but blocked by syntax. If the repaired query executes but selects different variables, applies wrong filters, or uses wrong predicates, strict answer match can remain low.

#### Answer Value F1

Answer Value F1 can improve when postprocessing enables execution and the repaired query returns overlapping values with the gold query. If only syntax is fixed but the retrieved answer set is wrong, this metric will not necessarily improve.

#### KG Reference F1

KG reference metrics compare ORKG references in the evaluated query. Since postprocessing does not introduce new ORKG identifiers, improvements here should not come directly from postprocessing. Changes may occur indirectly because PGMR restoration only produces the evaluated restored query after postprocessing has made the PGMR-lite text restorable.

#### SPARQL Structure F1

SPARQL Structure F1 can change because postprocessing changes graph-pattern syntax. For example, converting a bare label triple into an `OPTIONAL` block or wrapping a `FILTER NOT EXISTS` chain changes the structural pattern representation. This should be reported transparently because the evaluated structure is the repaired structure.

#### Query BLEU / ROUGE

Query BLEU and ROUGE compare normalized query tokens. Postprocessing changes tokens and ordering in limited ways, so it can affect these string-similarity metrics. In PGMR mode, PGMR ROUGE uses the postprocessed PGMR query against the gold PGMR query when available.

#### LLM judge scores

LLM judge scores may improve if the judge sees the restored/postprocessed query and the repair makes the intended structure clearer. This should be interpreted carefully: the judge evaluates the query text after pipeline transformations, not the raw model output alone.

### Methodological interpretation

If execution metrics improve, this indicates that some model outputs were syntactically broken but structurally recognizable. If answer metrics also improve, this suggests that some of those outputs were semantically close to the target. If only execution improves, the remaining errors are likely semantic, such as wrong predicates, wrong joins, wrong projections, or missing constraints.

Postprocessing should therefore be reported as part of the evaluated pipeline. It changes the query before execution and metric computation.

## 6. Limitations and Risks

### Facts from the implementation

The postprocessor is regex/scanner based, not a complete SPARQL parser or rewriting engine. It targets selected recurring artifacts.

### Risks

- Heuristic repair can be wrong in ambiguous cases.
- `FILTER NOT EXISTS` repair may choose an imperfect block boundary if a model output contains a pattern that looks like a connected chain but was not intended to be fully negated.
- The chain repair intentionally stops at known boundaries, but it cannot understand all legal SPARQL constructs.
- Optionalizing labels can change result availability if a label was intended as a mandatory existence constraint but is not detected as such.
- Malformed or heavily truncated queries cannot always be repaired safely.
- Missing braces, parentheses, or clauses beyond the implemented patterns are not globally balanced.
- The postprocessor does not fix wrong predicates, wrong classes, wrong resources, wrong projections, wrong joins, missing constraints, or incorrect answer variables.
- It is not a replacement for better training, prompting, template design, or PGMR memory quality.

### Interpretation

The safest interpretation is that postprocessing removes a small number of systematic syntax barriers. It should not be described as semantic correction.

## 7. Recommended Thesis Wording

Draft paragraph:

> To reduce the effect of recurring syntax artifacts in small-model outputs, the PGMR-lite pipeline includes a limited postprocessing step before placeholder restoration and execution. The postprocessor repairs local and structurally recognizable errors such as missing `WHERE` braces, bare one-triple `OPTIONAL` patterns, misplaced solution modifiers, malformed `FILTER NOT EXISTS` chains, malformed `REGEX` wrappers around equality filters, and mandatory output-only `rdfs:label` triples that can safely be made optional. These repairs are deliberately conservative: they do not introduce new ORKG identifiers, PGMR placeholders, template-specific predicates or classes, or new domain constraints. The goal is only to make syntactically incomplete but recognizable generated queries executable where possible. The evaluation records the raw output, postprocessed PGMR-lite query, restored ORKG-SPARQL query, and extracted query separately, so the effect of postprocessing remains transparent in the analysis.

## 8. Commands to Inspect the Implementation

Inspect the current postprocessor:

```bash
sed -n '1,460p' code/src/pgmr/postprocess.py
```

Inspect the evaluation pipeline around PGMR postprocessing/restoration:

```bash
sed -n '180,270p' code/src/evaluate/runner.py
```

Inspect how Direct-SPARQL extraction works:

```bash
sed -n '1,160p' code/src/evaluate/sparql_extraction.py
```

Find postprocessing tests:

```bash
find code/tests -type f | sort | grep -i post
```

Run postprocessing tests:

```bash
PYTHONPATH=code python -m pytest code/tests/pgmr/test_postprocess.py -q
```

Search for relevant postprocessing terms:

```bash
rg -n "postprocess_pgmr_query|FILTER NOT EXISTS|REGEX|rdfs:label|pgmr_postprocessed_query" code/src code/tests code/tools/pgmr code/outputs/evaluation_runs
```

List benchmark raw files:

```bash
find code/outputs/evaluation_runs -path '*benchmark_raw.json' | sort
```

Print raw output, PGMR postprocessed query, restored query, and extracted query for one PGMR run. This version automatically uses the newest available `benchmark_raw.json` under the T5 PGMR-mini 30-epoch evaluation directory:

```bash
PYTHONPATH=code python - <<'PY'
import json
from pathlib import Path

paths = sorted(
    Path("code/outputs/evaluation_runs/t5_base_pgmr_mini_full_finetune_30ep")
    .glob("pgmr_mini__benchmark__*/benchmark_raw.json")
)
if not paths:
    raise SystemExit("No T5 PGMR-mini benchmark_raw.json file found.")

path = paths[-1]
print("using:", path)
data = json.loads(path.read_text())
results = data.get("results", data)

for item in results:
    if item.get("pgmr_postprocessed_query"):
        print("id:", item.get("id"))
        print("raw_model_output:")
        print(item.get("raw_model_output"))
        print()
        print("pgmr_postprocessed_query:")
        print(item.get("pgmr_postprocessed_query"))
        print()
        print("pgmr_restored_query:")
        print(item.get("pgmr_restored_query"))
        print()
        print("extracted_query:")
        print(item.get("extracted_query"))
        break
PY
```

Find examples where a stored output contains `FILTER NOT EXISTS`:

```bash
PYTHONPATH=code python - <<'PY'
import json
from pathlib import Path

for path in sorted(Path("code/outputs/evaluation_runs").glob("**/benchmark_raw.json")):
    data = json.loads(path.read_text())
    results = data.get("results", data)
    if not isinstance(results, list):
        continue

    for item in results:
        text = " ".join(
            str(item.get(field) or "")
            for field in [
                "raw_model_output",
                "pgmr_postprocessed_query",
                "pgmr_restored_query",
                "extracted_query",
            ]
        )
        if "FILTER NOT EXISTS" in text:
            print(path)
            print("id:", item.get("id"))
            print("raw:", str(item.get("raw_model_output") or "")[:500])
            print("postprocessed:", str(item.get("pgmr_postprocessed_query") or "")[:500])
            print("restored:", str(item.get("pgmr_restored_query") or "")[:500])
            raise SystemExit
PY
```

Inspect metric computation:

```bash
sed -n '1,230p' code/src/evaluate/metric_runner.py
```

Inspect LLM judge prediction-field selection and scoring context:

```bash
sed -n '130,220p' code/tools/evaluate/run_llm_judge.py
```
