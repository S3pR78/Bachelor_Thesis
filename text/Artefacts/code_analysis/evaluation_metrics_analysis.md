# Evaluation Metrics Analysis

Technical basis for a later thesis section on "Evaluation Pipeline and Metrics".

Scope analyzed: `README.md`, `code/src/main.py`, `code/src/evaluate/`, `code/src/evaluate/metrics/`, `code/src/query/`, `code/src/sparql/`, `code/src/pgmr/`, `code/tools/evaluate/run_llm_judge.py`, `code/tools/evaluate/`, `code/tools/pgmr/`, `code/config/model_config.json`, final datasets, PGMR final datasets, existing evaluation outputs, and evaluation tests.

Important note: this document describes the repository implementation. It is not a final thesis section.

## 1. Evaluation Pipeline Overview

Evaluation is started through the main CLI:

```bash
PYTHONPATH=code python code/src/main.py evaluate ...
```

The `evaluate` subcommand is registered in `code/src/main.py` and dispatched to `src.evaluate.runner.execute_evaluate_task`.

The implemented flow is:

1. Parse CLI options in `code/src/main.py`.
2. Load benchmark entries with `load_evaluate_entries()` from `code/src/evaluate/dataset_loader.py`.
3. Create an output directory under the configured `outputs.evaluation_runs` path from `code/config/path_config.json`.
4. Build run metadata with `build_initial_run_metadata()` from `code/src/evaluate/run_io.py`.
5. Prepare one inference session with `prepare_inference_session()` from `code/src/query/inference_session.py`.
6. Optionally load PGMR-lite family memory from `--pgmr-memory-dir` when `--prediction-format pgmr_lite`.
7. Optionally load local ORKG memory from `--kg-memory-path` for URI hallucination checks.
8. For each dataset entry:
   - Select `id`, `uid`, `family`, `question`, `gold_sparql`, and `gold_pgmr_sparql`.
   - Build a prompt from `prompt_mode`.
   - Optionally prepend ACE playbook context.
   - Generate a raw model output.
   - Convert the model output into the prediction query to be evaluated.
   - Execute predicted and gold queries against the configured SPARQL endpoint.
   - Compute validation metrics.
   - Append a per-item record to `benchmark_raw.json`.
9. After all entries are processed:
   - Finalize `benchmark_raw.json`.
   - Aggregate metrics with `build_benchmark_summary()` from `code/src/evaluate/summary.py`.
   - Write `benchmark_summary.json`.

Dataset loading:

- `load_evaluate_entries(dataset_path, limit)` accepts either a JSON list or an object containing one of `entries`, `items`, or `data`.
- `--limit` keeps only the first N entries and must be positive.
- The direct final benchmark is under `code/data/dataset/final/benchmark.json`.
- The PGMR-lite transformed benchmark is under `code/data/dataset/pgmr/final/benchmark.json`.

Prompt building:

- Implemented in `code/src/query/prompt_builder.py`.
- Supported evaluation prompt modes are `empire_compass`, `empire_compass_mini`, `pgmr_mini`, `pgmr`, `zero_shot`, `few_shot`, and `pgmr_lite_meta`.
- `empire_compass`, `empire_compass_mini`, `pgmr_mini`, and `pgmr` require a dataset `family`.
- `zero_shot`, `few_shot`, and unknown modes currently fall back to the raw question text in `build_final_prompt_for_question()`. The names are accepted by the CLI, but no separate zero-shot/few-shot template implementation was found in this function.
- `pgmr_lite_meta` is evaluation-only and is built directly in `code/src/evaluate/runner.py` from metadata fields such as `family`, `answer_type`, `query_shape`, `special_types`, `complexity_level`, and `question`.

Model calling:

- Implemented in `code/src/query/inference_session.py`.
- Local Hugging Face models are loaded once with `load_model_and_tokenizer()` and reused.
- OpenAI models use `client.chat.completions.create()`.
- Model keys come from `code/config/model_config.json`.
- Local generation uses `max_new_tokens`, `do_sample`, and `temperature`.
- OpenAI generation uses `max_completion_tokens` from `max_output_tokens` or `max_new_tokens`, plus `temperature`.

Raw model output:

- Stored per item as `raw_model_output` in `benchmark_raw.json`.
- For OpenAI models, `model_usage` is stored when returned by the API.
- A `cost` payload is stored for all items; local Hugging Face models normally have zero token usage and no estimated price.

SPARQL extraction:

- Direct SPARQL mode uses `extract_sparql_query()` from `code/src/evaluate/sparql_extraction.py`.
- The extractor:
  - strips Markdown code fences,
  - removes full-line comments,
  - removes `PREFIX` lines,
  - finds the first `SELECT`, `ASK`, `CONSTRUCT`, or `DESCRIBE`,
  - returns text from that point onward.
- It does not parse SPARQL syntax.

Prefix handling:

- Implemented in `code/src/sparql/prefixes.py`.
- `prepend_orkg_prefixes()` prepends standard ORKG/RDF prefixes only if the query does not already start with `PREFIX`.
- Standard prefixes include `orkgr`, `orkgc`, `orkgp`, `rdfs`, `xsd`, and `rdf`.

PGMR-lite restoration:

- Applied only when `--prediction-format pgmr_lite`.
- Raw model output is first cleaned by `postprocess_pgmr_query()` from `code/src/pgmr/postprocess.py`.
- The runner builds a family-scoped memory index using `code/tools/pgmr/restore_and_execute_predictions.py` and `code/src/pgmr/memory_resolver.py`.
- Placeholders such as `pgmr:*` and `pgmrc:*` are restored to ORKG compact identifiers such as `orkgp:P31` or `orkgc:C27001`.
- If missing mappings or remaining PGMR tokens exist, `extracted_query` is set to `None` and execution is skipped.
- PGMR restoration diagnostics are stored in raw outputs.

Execution:

- Query form detection and endpoint execution are in `code/src/sparql/execution.py`.
- `detect_sparql_query_type()` supports `select`, `ask`, `construct`, `describe`, and `unknown`.
- Only `select` and `ask` are supported for execution-based evaluation in `code/src/evaluate/runner.py`.
- Execution uses HTTP GET with `Accept: application/sparql-results+json` and a default timeout of 60 seconds.
- Endpoint failures are stored as `status: "error"` and an error string.

Answer normalization:

- Implemented in `code/src/evaluate/answer_normalization.py` and `code/src/evaluate/metrics/answer_cell_value_precision_recall_f1.py`.
- ASK results become boolean values.
- SELECT results become sets, so row order is ignored and duplicate rows are collapsed.
- Strict row-level metrics include variable names.
- Value-only row metrics ignore variable names.
- Cell-value metrics compare unique individual cell values, ignoring row grouping and variable names.

Metric computation:

- `build_validation_metrics()` in `code/src/evaluate/metric_runner.py` computes all per-item metrics.
- The output is stored under each result's `validation` field.

Output writing:

- No `code/src/evaluate/result_writer.py` file was found in code.
- Output path helpers are in `code/src/evaluate/run_io.py`.
- Actual JSON writing happens inside `code/src/evaluate/runner.py`.
- `benchmark_raw.json` is updated incrementally after each item and finalized at the end.
- `benchmark_summary.json` is written after summary aggregation.

## 2. Evaluation Configuration and CLI Options

The implemented evaluation CLI options are:

```text
--model
--dataset
--limit
--prompt-mode
--sparql-endpoint
--prediction-format
--pgmr-memory-dir
--pgmr-similarity-mapping
--pgmr-auto-map-threshold
--pgmr-suggestion-threshold
--pgmr-min-margin
--kg-memory-path / --kg_memory_path
--ace-playbook
--ace-playbook-dir
--ace-mode
--ace-max-bullets
```

`--model`:

- Required.
- Must be a key under `models` in `code/config/model_config.json`.
- Controls provider, model ID, local model path or OpenAI model, interface, generation settings, and optional adapter path.
- Original models and fine-tuned models are distinguished only by their model config entries. For example, QLoRA models use the same base local model path plus `adapter_path`.

`--dataset`:

- Required.
- Path to a JSON dataset file.
- Direct SPARQL runs usually use `code/data/dataset/final/benchmark.json`.
- PGMR-lite runs usually use `code/data/dataset/pgmr/final/benchmark.json`, because that file contains `gold_pgmr_sparql`.

`--limit`:

- Optional integer.
- Uses only the first N entries.
- Non-positive limits raise a `ValueError`.

`--prompt-mode`:

- Optional.
- CLI-supported values: `empire_compass`, `empire_compass_mini`, `pgmr_mini`, `pgmr`, `zero_shot`, `few_shot`, `pgmr_lite_meta`.
- Controls prompt template selection.
- `pgmr_lite_meta` builds a compact metadata prompt in the evaluation runner.
- `zero_shot` and `few_shot` are accepted but no specialized prompt templates were found in `build_final_prompt_for_question()`; they fall back to the question text.

`--sparql-endpoint`:

- Optional.
- Default: `https://www.orkg.org/triplestore`.
- If set to an empty or false value programmatically, execution metrics become non-comparable with reason `no_endpoint_configured`.
- The CLI default means normal CLI runs execute both predicted and gold queries.

`--prediction-format`:

- Optional.
- Values: `sparql`, `pgmr_lite`.
- Default: `sparql`.
- `sparql`: raw output is directly passed through SPARQL extraction.
- `pgmr_lite`: raw output is postprocessed, restored with PGMR memory, and only then executed as ORKG SPARQL.

`--pgmr-memory-dir`:

- Optional.
- Default: `code/data/orkg_memory/templates`.
- Used only for `--prediction-format pgmr_lite`.
- Expected memory files include `*_memory.json`, for example `nlp4re_memory.json` and `empirical_research_practice_memory.json`.

`--pgmr-similarity-mapping`:

- Optional flag.
- Enables conservative similarity-based mapping for missing PGMR placeholders.
- If disabled, exact placeholder and alias mapping are used, but automatic similarity mapping is not applied.

`--pgmr-auto-map-threshold`:

- Optional float, default `0.90`.
- Minimum similarity score required for automatic PGMR mapping.

`--pgmr-suggestion-threshold`:

- Optional float, default `0.75`.
- Minimum score for storing a manual mapping suggestion.
- Suggestions do not restore the query by themselves.

`--pgmr-min-margin`:

- Optional float, default `0.08`.
- Minimum score gap between best and second-best candidate for automatic mapping.

`--kg-memory-path` / `--kg_memory_path`:

- Optional.
- Default: `code/data/orkg_memory/templates`.
- Used by `uri_hallucination`, which checks predicted predicate/class references against local memory.
- If the path does not exist, URI hallucination is marked non-comparable.

`--ace-playbook`:

- Optional path to one ACE playbook JSON file.
- If `--ace-max-bullets > 0`, matching ACE context is prepended to each prompt.

`--ace-playbook-dir`:

- Optional directory for model/family-aware playbook routing.
- Used by `resolve_ace_playbook_path()` in `code/src/ace/routing.py`.

`--ace-mode`:

- Optional.
- Values: `pgmr_lite`, `direct_sparql`, `any`.
- If omitted, it is inferred from `prompt_mode`: modes containing `pgmr` use `pgmr_lite`; otherwise `direct_sparql`.

`--ace-max-bullets`:

- Optional integer.
- Default: `0`, which disables ACE prompt augmentation.
- Positive values limit the number of ACE bullets rendered into the prompt.

Direct-SPARQL outputs:

- Use `--prediction-format sparql`.
- Evaluate `extracted_query` directly after prefix insertion.
- PGMR restoration fields are `null` or empty.

PGMR-lite outputs:

- Use `--prediction-format pgmr_lite`.
- Evaluate only after successful PGMR postprocessing and restoration.
- If restoration fails, execution-based and answer-based metrics for that item become non-comparable or skipped downstream.

Original vs fine-tuned models:

- There is no separate evaluation branch for original vs fine-tuned models.
- The distinction is encoded in `code/config/model_config.json`.
- Fine-tuned T5 uses `variant: "finetuned"` and `finetuned_path`.
- QLoRA/Mistral/Qwen fine-tuned variants use `adapter_path`.

ACE-enhanced runs:

- ACE affects prompts only.
- Deterministic metrics are computed in the same way as non-ACE runs.
- Run metadata stores ACE configuration when an ACE playbook path or directory is provided.

## 3. Output Files and Their Structure

Evaluation run directories are created under:

```text
code/outputs/evaluation_runs/<model_name>/<prompt_mode>__<dataset_stem>__<timestamp>/
```

The timestamp is UTC in `YYYYMMDD_HHMMSS` format.

Implemented standard files:

- `benchmark_raw.json`
- `benchmark_summary.json`

Observed optional files:

- `README.md` files manually describing some run setups.
- `llm_judge_raw.json`, `llm_judge_summary.json`, and `benchmark_summary_with_llm_judge.json` for a post-hoc LLM judge run.

Error trace files:

- ACE trace construction is implemented in `code/src/ace/offline/traces.py`.
- No ACE error trace files were found under the inspected `code/outputs/evaluation_runs/` directories.
- Therefore: ACE trace output files in current evaluation runs are not found in code outputs.

`benchmark_raw.json`:

- Current writer structure is an object:

```json
{
  "run_metadata": {},
  "results": []
}
```

Typical `run_metadata` fields:

- `model_name`
- `dataset_path`
- `prompt_mode`
- `requested_limit`
- `run_dir`
- `output_path`
- `summary_output_path`
- `started_at_utc`
- `finished_at_utc`
- `total_items`
- `completed_items`
- `prediction_format`
- `pgmr_memory_dir` and PGMR mapping thresholds for PGMR-lite runs
- `ace` block for ACE-enhanced runs
- `cost_summary`

Typical per-item fields:

- `id`
- `question`
- `gold_query`
- `gold_pgmr_query`
- `entry_metadata`
- `prediction_format`
- `raw_model_output`
- `extracted_query`
- `has_extracted_query`
- `extraction_status`
- `pgmr_postprocessed_query`
- `pgmr_restored_query`
- `pgmr_restore_status`
- `pgmr_missing_mapping_tokens`
- `pgmr_remaining_tokens`
- `pgmr_alias_mappings`
- `pgmr_auto_mappings`
- `pgmr_mapping_suggestions`
- `pgmr_unmapped_placeholders`
- `pgmr_basic_status`
- `response_time_seconds`
- `prediction_query_form`
- `gold_query_form`
- `query_execution`
- `gold_execution`
- `validation`
- `model_usage`
- `cost`

Execution payload fields:

- `status`: `ok`, `skipped`, or `error`.
- `reason`: used for skipped execution.
- `error`: used for execution errors.
- `result_type`: usually `select` or `ask`.
- `query_with_prefixes`: the query actually sent or prepared.
- `response_json`: SPARQL JSON result when status is `ok`.

`benchmark_summary.json`:

- Current structure is:

```json
{
  "run_metadata": {},
  "summary": {}
}
```

The `summary` object contains:

- `total_items`
- `metrics`
- `error_categories`
- `response_time_seconds`
- `slices`
- PGMR resolution event counts
- `costs`

`summary.metrics` contains aggregate summaries for all core metrics. Each numeric summary normally contains:

- `metric_name`
- `value_field`
- `comparable_count`
- `valid_count`
- `non_comparable_count`
- `mean`
- sometimes `success_count`, `failure_count`, and `success_rate` when all numeric values are binary 0/1.

Aggregation uses only comparable metric objects. Non-comparable items are counted but excluded from the mean.

`slices`:

- Per-field aggregations are implemented for:
  - `family`
  - `source_dataset`
  - `query_type`
  - `answer_type`
  - `query_shape`
  - `complexity_level`

LLM judge files:

- `llm_judge_raw.json` is a JSON list of judgment records.
- `llm_judge_summary.json` is a JSON object with judge means and verdict counts.
- `benchmark_summary_with_llm_judge.json` copies `benchmark_summary.json` and adds a top-level `llm_judge` key.

## 4. Query Extraction and Query Form Metrics

### `query_extracted`

Meaning:

- Whether a prediction query was available for evaluation.

Computation:

- Implemented in `code/src/evaluate/metrics/query_extracted.py`.
- `value = 1.0` when `has_extracted_query` is true, else `0.0`.
- Always comparable.

Interpretation:

- Measures whether the pipeline could obtain an evaluable query from model output.
- It does not measure SPARQL correctness.
- A query can be extracted but still be syntactically invalid or semantically wrong.

### `extraction_status`

Meaning:

- Per-item status stored in `benchmark_raw.json`, not a separate metric module.

Direct SPARQL computation:

- `ok` if `extract_sparql_query()` returned a query.
- `empty` if no query was extracted.

PGMR-lite computation:

- `pgmr_restore:ok`
- `pgmr_restore:missing_mapping`
- `pgmr_restore:remaining_pgmr_tokens`

Interpretation:

- Helps separate ordinary extraction failure from PGMR restoration failure.

### `supported_query_form`

Meaning:

- Whether the predicted query form is supported by the execution-based evaluator.

Computation:

- Implemented in `code/src/evaluate/metrics/supported_query_form.py`.
- Supported forms are `select` and `ask`.
- If no query was extracted, it is non-comparable with reason `no_extracted_query`.
- Otherwise `value = 1.0` if the detected form is `select` or `ask`, else `0.0`.

Interpretation:

- Query extraction is a prerequisite.
- Correct query form does not imply correct answers.
- Unsupported `CONSTRUCT`, `DESCRIBE`, or `unknown` forms are not answer-compared.

### `query_form_match`

Meaning:

- Whether predicted and gold query forms match.

Computation:

- Implemented in `code/src/evaluate/metrics/query_form_match.py`.
- If either form is missing, it is non-comparable with reason `missing_query_form`.
- Otherwise `value = 1.0` if `prediction_query_form == gold_query_form`, else `0.0`.

Interpretation:

- Useful for detecting ASK-vs-SELECT mistakes.
- A matching form still does not imply semantic correctness.

### likely truncated query

- Not a per-item validation metric in `benchmark_raw.json`.
- Implemented only in the diagnostic script `code/src/evaluate/analysis/execution_error_breakdown.py`.
- `_looks_truncated()` checks unbalanced braces, unbalanced parentheses, or suspicious endings such as `AS`, `||`, `&&`, `;`, `{`, `(`.
- Category name: `likely_truncated_query`.

### invalid or unsupported query form

- Unsupported query form is implemented through `supported_query_form` and `primary_error_category`.
- Separate "invalid query form" metric not found in code.

## 5. Execution-Based Metrics

### `prediction_execution_success`

Meaning:

- Whether the predicted query executed successfully at the SPARQL endpoint.

Computation:

- Implemented in `code/src/evaluate/metrics/prediction_execution_success.py`.
- Non-comparable if no endpoint is configured.
- Non-comparable if the predicted query is missing or not `select`/`ask`.
- Otherwise `value = 1.0` if `prediction_execution["status"] == "ok"`, else `0.0`.

Interpretation:

- Measures executability, not correctness.
- A successful execution can still return the wrong answer.

### `gold_execution_success`

Meaning:

- Whether the gold query executed successfully.

Computation:

- Implemented in `code/src/evaluate/metrics/gold_execution_success.py`.
- Non-comparable if no endpoint is configured.
- Non-comparable if the gold query form is missing or unsupported.
- Otherwise `value = 1.0` if `gold_execution["status"] == "ok"`, else `0.0`.

Interpretation:

- Gold execution failure makes answer-based comparison impossible or non-comparable.
- It should be monitored separately from model failure.

Endpoint errors:

- `execute_sparql_query()` raises `RuntimeError("SPARQL request failed: ...")` for `requests` errors.
- The runner stores these as execution payloads with `status: "error"` and `error`.
- `primary_error_category` labels prediction execution errors as `prediction_execution_error` and gold errors as `gold_execution_error`.

Bad request errors:

- The main metric loop does not create a specific `endpoint_bad_request` primary category.
- `endpoint_bad_request` is implemented in:
  - `code/src/evaluate/analysis/execution_error_breakdown.py`, where HTTP 400 errors are classified.
  - `code/src/ace/offline/traces.py`, where error text containing `400` or `bad request` adds this ACE category.

Timeouts:

- Endpoint execution uses a 60-second timeout.
- No specific timeout metric or timeout category was found in the main metric code.
- Timeout-like errors would be stored as generic execution errors unless further classified by downstream diagnostics.

Comparable vs non-comparable:

- Execution metrics are comparable only when the relevant query exists, has a supported form, and an endpoint is configured.
- Answer metrics are comparable only when both normalized execution results are valid and supported.

## 6. Answer-Based Metrics

Answer-based metrics compare executed query results, not SPARQL strings. They are generally more meaningful than string matching because different SPARQL queries can be semantically equivalent or return the same result set.

### Execution result normalization

Implemented in `code/src/evaluate/answer_normalization.py`.

ASK:

- Normalized to kind `ask` with boolean `value`.

SELECT strict mode:

- Each row is a sorted tuple of bound cells.
- Each cell includes:
  - variable name,
  - value type,
  - lexical value,
  - datatype,
  - language tag.
- Rows are stored in a `frozenset`.

SELECT value-only mode:

- Same as strict mode, but variable names are omitted from each cell.

Common behavior:

- Row order is ignored.
- Variable order inside a row is ignored.
- Duplicate rows are collapsed.
- Literal datatypes and language tags are preserved.
- Numeric datatypes are normalized to `xsd:decimal` in `answer_normalization.py`.

### `answer_exact_match`

Computation:

- Implemented in `code/src/evaluate/metrics/answer_exact_match.py`.
- Uses strict normalization.
- Non-comparable if prediction or gold result is missing, error, or unsupported.
- If answer kinds differ, comparable with `value = 0.0`.
- ASK: `1.0` if booleans are identical, else `0.0`.
- SELECT: `1.0` if strict row sets are identical, else `0.0`.

Interpretation:

- Strictest answer metric.
- Sensitive to variable names for SELECT results.
- Useful as a high-confidence correctness indicator, but may under-credit semantically adequate projections with different variable names.

### `answer_precision`, `answer_recall`, `answer_f1`

Stored as summary names for the per-item metric `answer_precision_recall_f1`.

Formula for SELECT:

- `TP = |predicted_rows intersect gold_rows|`
- `precision = TP / |predicted_rows|`, or `0.0` if prediction has no rows and gold is not also empty.
- `recall = TP / |gold_rows|`, or `0.0` if gold has no rows and prediction is not also empty.
- `F1 = 2 * precision * recall / (precision + recall)`, or `0.0` if both precision and recall are zero.
- If both predicted and gold row sets are empty, precision, recall, and F1 are all `1.0`.

Formula for ASK:

- Precision, recall, and F1 are all `1.0` if booleans match, else `0.0`.

Interpretation:

- Row-level partial credit.
- Still strict about variable names in SELECT rows.

### `answer_value_exact_match`

Computation:

- Implemented in `code/src/evaluate/metrics/answer_value_exact_match.py`.
- Same exact-match logic as `answer_exact_match`, but SELECT rows ignore variable names.

Interpretation:

- More tolerant than strict exact match.
- Still compares full value rows, so row grouping must match.

### `answer_value_precision`, `answer_value_recall`, `answer_value_f1`

Stored as summary names for `answer_value_precision_recall_f1`.

Computation:

- Implemented in `code/src/evaluate/metrics/answer_value_precision_recall_f1.py`.
- Same row-level precision/recall/F1 formulas as strict `answer_precision_recall_f1`.
- SELECT rows ignore variable names.

Interpretation:

- Useful when predictions use different SELECT variable names but return equivalent rows.
- Still sensitive to row shape and grouping.

Empty results:

- For row-level precision/recall/F1, if both predicted and gold SELECT row sets are empty, precision, recall, and F1 are `1.0`.
- If only one side is empty, precision or recall becomes `0.0` as appropriate.

Non-comparable cases:

- Missing prediction, missing gold, execution errors, skipped executions, and unsupported result kinds are non-comparable.
- Non-comparable cases are excluded from summary means but counted under `non_comparable_count`.

## 7. Answer Cell Value Metrics

### `answer_cell_value_precision`, `answer_cell_value_recall`, `answer_cell_value_f1`

Stored as summary names for the per-item metric `answer_cell_value_precision_recall_f1`.

Computation:

- Implemented in `code/src/evaluate/metrics/answer_cell_value_precision_recall_f1.py`.
- Requires both prediction and gold execution payloads to have `status == "ok"`.
- Extracts unique individual cell values from the SPARQL JSON result.
- For SELECT:
  - iterates through all rows,
  - iterates through all bound values,
  - ignores variable names,
  - ignores row grouping,
  - ignores row order,
  - ignores column order,
  - collapses duplicate values.
- For ASK:
  - turns the boolean into one normalized boolean literal cell.

Value normalization:

- Values are normalized as `(value_type, lexical_value, datatype, language)`.
- `typed-literal` is normalized to `literal`.
- Boolean typed literals normalize `1`/`true` to `true`, `0`/`false` to `false`.
- Numeric typed literals are decimal-normalized.
- Datatype and language tags remain part of the compared value.

Formula:

- `TP = |predicted_values intersect gold_values|`
- `precision = TP / |predicted_values|`
- `recall = TP / |gold_values|`
- `F1 = 2 * precision * recall / (precision + recall)`
- If both value sets are empty, precision, recall, and F1 are `1.0`.

Difference from row-level answer matching:

- Row-level metrics compare complete rows.
- Cell-value metrics compare individual unique values.
- Cell-value metrics can give credit when a prediction returns correct labels, years, resource IRIs, or booleans but arranges them in different columns or rows.

What it can capture:

- Overlap in returned answer values despite projection differences.
- Partial semantic proximity in wide or differently shaped SELECT results.

What it cannot capture:

- Whether values are attached to the correct row.
- Whether the query uses the correct joins.
- Whether a value appears in the correct variable/column.
- Duplicate multiplicities.

This metric is especially useful for this thesis because some models may return semantically related values with different SELECT variables or extra label columns.

## 8. KG Reference Metrics

Implemented per-item metric function: `compute_kg_ref_match()` in `code/src/evaluate/metrics/kg_ref_match.py`.

Summary names:

- `kg_ref_precision`, `kg_ref_recall`, `kg_ref_f1`
- `predicate_ref_precision`, `predicate_ref_recall`, `predicate_ref_f1`
- `class_ref_precision`, `class_ref_recall`, `class_ref_f1`
- `resource_ref_precision`, `resource_ref_recall`, `resource_ref_f1`

Reference extraction:

- Implemented in `code/src/evaluate/query_elements.py`.
- Extracts ORKG compact references:
  - predicates: `orkgp:*`
  - classes: `orkgc:*`
  - resources: `orkgr:*`
- Also extracts full ORKG IRIs and canonicalizes them to compact references.
- Ignores Markdown code fences.
- Ignores comments.
- Masks string literals before extracting references.

Reference groups:

- `predicate_refs`
- `class_refs`
- `resource_refs`
- `all_refs`

Comparison:

- Prediction and gold references are sets.
- `matched_refs = prediction_refs intersect gold_refs`
- `missing_gold_refs = gold_refs - prediction_refs`
- `extra_predicted_refs = prediction_refs - gold_refs`

Formula:

- `precision = matched_ref_count / prediction_ref_count`
- `recall = matched_ref_count / gold_ref_count`
- `F1 = 2 * precision * recall / (precision + recall)`
- If prediction and gold both contain zero references of the selected kind, precision, recall, and F1 are `1.0`.

Non-comparable:

- Missing prediction query gives reason `prediction_query_missing`.
- Missing gold query gives reason `gold_query_missing`.

Why predicate/class/resource references are separated:

- Predicates usually encode the semantic relation and are often the most important ORKG choice.
- Classes encode template/contribution type.
- Resources encode fixed named entities.
- Separating them helps diagnose whether a model got the template family right but chose wrong properties, or vice versa.

Prefix normalization:

- Prefix names are lowercased.
- Full ORKG IRIs are converted to compact prefixed references.
- Non-ORKG prefixes such as `rdf:` and `rdfs:` are not counted as KG references.

PGMR restore timing:

- In PGMR-lite runs, KG reference metrics are computed on `extracted_query`.
- `extracted_query` is the restored ORKG-SPARQL query only when `pgmr_restore_status == "ok"`.
- Placeholder references are therefore not counted before restoration in the main KG reference metrics.

Limitations:

- Using the correct KG references does not guarantee the correct query structure.
- A model can use the right predicate IDs with wrong joins, filters, grouping, or projections.
- A model can sometimes use different references and still return related answers.

### `uri_hallucination`

Additional implemented KG-related metric.

- Implemented in `code/src/evaluate/metrics/uri_hallucination.py`.
- Checks predicted predicate and class refs against refs loaded from local memory.
- Summary reports hallucinated item count, clean item count, hallucinated ref count, and hallucinated ref rate.
- This is not in the requested KG F1 list, but it exists in code and summary outputs.

## 9. Text-Similarity Metrics

Implemented query-text metrics:

- `query_normalized_exact_match`
- `query_bleu`
- `query_rouge1_f1`
- `query_rouge2_f1`
- `query_rougeL_f1`
- `pgmr_rouge1_f1`
- `pgmr_rouge2_f1`
- `pgmr_rougeL_f1`
- `sparql_structure_match` / SQM-lite

### `query_normalized_exact_match`

- Implemented in `code/src/evaluate/metrics/query_normalized_exact_match.py`.
- Compares predicted and gold SPARQL after lightweight text normalization.
- Normalization is in `code/src/evaluate/query_text_normalization.py`:
  - remove Markdown code fences,
  - remove comments outside string literals,
  - normalize whitespace,
  - normalize and sort `PREFIX` declarations,
  - normalize `BASE`,
  - keep body order unchanged.
- This is not semantic equivalence.

### `query_bleu`

- Implemented in `code/src/evaluate/metrics/query_bleu.py`.
- Metric variant: one lightweight BLEU score with `max_order = 4`.
- It is not separate BLEU-1, BLEU-2, BLEU-3, BLEU-4.
- Uses normalized SPARQL tokens from `tokenize_normalized_sparql()`.
- Uses modified n-gram precision for orders 1 to 4.
- Uses smoothing value `1.0`.
- Uses a brevity penalty.
- Stored fields include:
  - `bleu`
  - `max_order`
  - `smoothing`
  - `modified_precisions`
  - `brevity_penalty`
  - token counts.

Implementation note:

- If any modified precision is `<= 0`, the function returns bare `0.0` rather than a metric dictionary. This is inconsistent with the rest of the metric framework. In observed full evaluation outputs, `query_bleu` appears as a normal metric object, but the edge case is present in code.

### ROUGE

- Implemented in `code/src/evaluate/metrics/query_rouge.py`.
- Variants:
  - ROUGE-1 F1
  - ROUGE-2 F1
  - ROUGE-L F1
- The repository stores F1-oriented metric names: `*_rouge1_f1`, `*_rouge2_f1`, `*_rougeL_f1`.
- Precision and recall are also stored per item, but summary means use the `f1` field.
- Computed over normalized query tokens.
- Normalization removes code fences, comments, and `PREFIX`/`BASE` lines.
- Tokens are lowercased.

`query_rouge*`:

- Computed on restored/extracted prediction SPARQL versus `gold_sparql`.

`pgmr_rouge*`:

- Computed only when PGMR metrics are enabled and a `gold_pgmr_query` exists.
- Prediction side is `pgmr_postprocessed_query`, not the restored ORKG query.
- If unavailable, the metric is non-comparable.

### SQM-lite / `sparql_structure_match`

- Implemented in `code/src/evaluate/metrics/sparql_structure_match.py`.
- Summary names:
  - `sparql_structure_precision`
  - `sparql_structure_recall`
  - `sparql_structure_f1`
- Extracts lightweight WHERE-body patterns after normalization.
- Ignores pattern order.
- Normalizes variable names to `?VAR`.
- Flattens common `OPTIONAL`/`MINUS` grouping and expands simple semicolon property lists.
- Includes `FILTER` expressions as patterns.
- Computes precision/recall/F1 over multiset pattern overlap.

Interpretation of text-similarity metrics:

- They are secondary for Text-to-SPARQL.
- High BLEU/ROUGE can hide wrong predicates, wrong filters, or wrong joins.
- Low BLEU/ROUGE can still be acceptable if a different query returns the correct answer.
- Use answer-based and execution-based metrics as primary correctness signals.

## 10. PGMR-lite Specific Metrics and Status Fields

PGMR restoration is applied when:

```bash
--prediction-format pgmr_lite
```

The runner then:

1. Applies `postprocess_pgmr_query(raw_model_output)`.
2. Builds a family-specific memory index from `--pgmr-memory-dir`.
3. Restores placeholders using exact mapping, aliases, and optionally similarity mapping.
4. Postprocesses the restored query again.
5. Detects basic query status.
6. Sets `extracted_query` only if restoration status is `ok`.

Memory files:

- Loaded from `code/data/orkg_memory/templates`.
- Current files found:
  - `empirical_research_practice_memory.json`
  - `nlp4re_memory.json`

PGMR restore status:

- `ok`: no missing mappings and no remaining PGMR tokens.
- `missing_mapping`: at least one placeholder could not be mapped.
- `remaining_pgmr_tokens`: restoration produced a query still containing `pgmr:` or `pgmrc:` tokens.

Stored PGMR fields:

- `pgmr_postprocessed_query`
- `pgmr_restored_query`
- `pgmr_restore_status`
- `pgmr_missing_mapping_tokens`
- `pgmr_remaining_tokens`
- `pgmr_alias_mappings`
- `pgmr_auto_mappings`
- `pgmr_mapping_suggestions`
- `pgmr_unmapped_placeholders`
- `pgmr_basic_status`

`pgmr_basic_status` contains:

- `starts_with_query_type`
- `has_where_block`
- `balanced_braces`
- `remaining_pgmr_tokens`
- `orkg_tokens`

### `pgmr_unmapped_placeholders`

Implemented in `code/src/evaluate/metrics/pgmr_unmapped_placeholders.py`.

Computation:

- Only enabled when `prompt_mode` or `prediction_format` contains `pgmr`.
- If not PGMR mode, non-comparable with reason `not_pgmr_mode`.
- If prediction query is missing, non-comparable with reason `prediction_query_missing`.
- Detects unresolved placeholders using conservative regexes for:
  - `{{...}}`
  - `[UNMAPPED...]`, `[UNKNOWN...]`, `[PLACEHOLDER...]`, `[TODO...]`
  - angle placeholders such as `<NLP_TASK>` but not real IRIs
  - bare tokens such as `PGMR_UNKNOWN`, `UNMAPPED`, `UNKNOWN`, `PLACEHOLDER`
- `value = 1.0` means at least one unresolved placeholder was found.
- `value = 0.0` means none was found.

Important limitation:

- In the main PGMR-lite runner, if restoration fails, `extracted_query` is set to `None`. Then this metric becomes non-comparable with `prediction_query_missing`.
- Missing mapping diagnostics are still stored in top-level fields and counted in summary PGMR resolution event counts.

PGMR summary event counts:

- `pgmr_alias_mapped_item_count`
- `pgmr_alias_mapped_placeholder_count`
- `pgmr_auto_mapped_item_count`
- `pgmr_auto_mapped_placeholder_count`
- `pgmr_suggested_item_count`
- `pgmr_suggested_placeholder_count`
- `pgmr_still_unmapped_item_count`
- `pgmr_still_unmapped_placeholder_count`

Difference between raw PGMR and restored ORKG-SPARQL:

- Raw PGMR output uses placeholder vocabulary.
- Restored ORKG-SPARQL replaces PGMR placeholders with actual ORKG compact identifiers.
- Execution and answer metrics are computed only on restored ORKG-SPARQL.
- PGMR ROUGE metrics compare raw/postprocessed PGMR output to `gold_pgmr_sparql`.

Evaluation levels:

1. PGMR generation/restoration level:
   - extraction status,
   - restore status,
   - missing mapping tokens,
   - remaining PGMR tokens,
   - PGMR ROUGE.
2. ORKG execution/answer level:
   - prediction execution success,
   - answer exact match,
   - answer F1,
   - cell-value F1,
   - KG reference F1 after restoration.

## 11. LLM Judge Metrics

An LLM judge is implemented as a post-hoc tool, not inside the deterministic evaluation runner.

Location:

```text
code/tools/evaluate/run_llm_judge.py
```

This file is the central implementation for the LLM judge workflow. It is not imported by `code/src/evaluate/runner.py`; instead, it is run separately after a normal benchmark run has already produced `benchmark_raw.json`.

CLI:

```bash
PYTHONPATH=code python code/tools/evaluate/run_llm_judge.py \
  --input code/outputs/evaluation_runs/.../benchmark_raw.json \
  --output-dir code/outputs/evaluation_runs/... \
  --judge-model gpt_4o_mini
```

Default judge model:

- `gpt_4o_mini`.
- The model key is resolved through `code/config/model_config.json` when possible.

Input to judge:

- Natural-language question.
- Template family.
- Gold SPARQL query.
- Predicted SPARQL query.

Prediction field selection:

- `--prediction-field auto` prefers:
  1. `pgmr_restored_query`
  2. `restored_query`
  3. `extracted_query`
  4. `predicted_query`
  5. `raw_model_output`
- Explicit options: `extracted_query`, `pgmr_restored_query`, `restored_query`, `raw_model_output`.

What it judges:

- Query text semantic appropriateness for the question.
- It does not use endpoint execution results.
- It is not an answer equivalence checker.

Output fields:

- `intent_score`: 0-2
- `schema_score`: 0-2
- `projection_score`: 0-2
- `constraint_score`: 0-2
- `aggregation_score`: 0-2
- `overall_score`: 0-10
- `verdict`: `correct`, `partially_correct`, or `incorrect`
- `main_issue`
- `short_rationale`
- skip fields for missing prediction/gold, dry runs, or judge errors.

Output files:

- `llm_judge_raw.json`
- `llm_judge_summary.json`
- `benchmark_summary_with_llm_judge.json` if `benchmark_summary.json` exists in the same directory.

Included in `benchmark_summary.json`:

- Not by the main evaluation runner.
- The post-hoc tool writes `benchmark_summary_with_llm_judge.json` with an added top-level `llm_judge` field.

Interpretation:

- Auxiliary analysis layer.
- Should not replace execution-based and answer-based metrics.
- Useful for diagnosing partial correctness or semantic similarity.
- May introduce model-dependent bias.

## 12. Aggregation and Reporting

Aggregation is implemented in `code/src/evaluate/summary.py`.

Numeric metric aggregation:

- `_numeric_metric_values()` collects only metric dictionaries with `comparable == true`.
- Non-comparable metrics are counted under `non_comparable_count`.
- Means are rounded to 4 decimals.
- Missing metric objects are counted as non-comparable.

Binary metric summaries:

- If all collected comparable values are `0.0` or `1.0`, summary adds:
  - `success_count`
  - `failure_count`
  - `success_rate`
- `success_rate` equals the mean of comparable binary values.

Failed executions:

- `prediction_execution_success` is comparable and `0.0` when a supported extracted prediction query is executed and endpoint status is `error`.
- Answer metrics become non-comparable when execution failed, because normalized prediction kind becomes `error`.
- Therefore failed execution does not directly count as zero for answer F1; it is excluded from answer-metric means and counted as non-comparable.

Skipped or missing predictions:

- Extraction metrics remain comparable.
- Supported-form and execution metrics may become non-comparable.
- Answer metrics become non-comparable.

Per-family aggregation:

- Implemented through `summary.slices.family`.
- The same metric summaries are also produced by:
  - `source_dataset`
  - `query_type`
  - `answer_type`
  - `query_shape`
  - `complexity_level`

Error categories:

- `summary.error_categories` counts `validation.primary_error_category`.

Cost aggregation:

- `_aggregate_costs()` in `code/src/evaluate/runner.py` aggregates prompt, completion, total, cached tokens, estimated cost, priced item count, and mean cost per priced item.
- Price lookup is implemented in `code/src/evaluate/costs.py`.

## 13. Error Categories and Diagnostics

### `primary_error_category`

Implemented in `code/src/evaluate/metrics/primary_error_category.py`.

Categories produced by the main metric runner:

- `extraction_failure`
- `unsupported_query_form`
- `not_evaluated_no_endpoint`
- `gold_query_missing`
- `gold_query_form_unsupported`
- `gold_execution_error`
- `prediction_execution_error`
- `prediction_not_executed`
- `gold_not_executed`
- `answer_mismatch`
- `success`

Detection order:

1. No extracted prediction query -> `extraction_failure`.
2. Prediction form unsupported -> `unsupported_query_form`.
3. No endpoint -> `not_evaluated_no_endpoint`.
4. Missing gold form -> `gold_query_missing`.
5. Unsupported gold form -> `gold_query_form_unsupported`.
6. Gold execution status error -> `gold_execution_error`.
7. Prediction execution status error -> `prediction_execution_error`.
8. Prediction status not `ok` -> `prediction_not_executed`.
9. Gold status not `ok` -> `gold_not_executed`.
10. Comparable answer exact match with value `0.0` -> `answer_mismatch`.
11. Otherwise -> `success`.

### Diagnostic script categories

Implemented in `code/src/evaluate/analysis/execution_error_breakdown.py`.

Additional categories include:

- `no_extracted_query`
- `unsupported_query_form`
- `query_preparation_failed`
- `likely_escaped_query_formatting`
- `likely_truncated_query`
- `likely_missing_group_by`
- `endpoint_bad_request`
- `endpoint_http_<status>`
- `prediction_execution_error_other`
- `prediction_execution_skipped`
- `answer_mismatch`
- `success`
- `unknown_prediction_status`

The script also produces:

- `category_counts`
- `top_error_signatures`
- up to three examples per category.

This output is not automatically written by the main evaluation runner; it must be run separately.

### ACE trace categories

Implemented in `code/src/ace/offline/traces.py`.

Categories include:

- `no_extracted_query`
- `unsupported_query_form`
- `query_form_mismatch`
- `prediction_execution_error`
- `gold_execution_error`
- `answer_mismatch`
- `predicate_ref_mismatch`
- `class_ref_mismatch`
- `resource_ref_mismatch`
- `pgmr_unmapped_placeholders`
- `pgmr_restore_error`
- `endpoint_bad_request`
- `endpoint_uri_too_long`

ACE traces are designed for error reflection/playbook generation, not as primary benchmark metrics.

### `answer_mismatch`

- Main category when both queries execute sufficiently for answer comparison but strict answer exact match is `0.0`.
- Indicates wrong result set under strict comparison.

### `pgmr_restore:missing_mapping`

- Stored in `extraction_status`, not `primary_error_category`.
- Occurs when PGMR restoration cannot map one or more PGMR placeholders.
- Missing tokens are stored in `pgmr_missing_mapping_tokens`.

### `pgmr_restore:remaining_pgmr_tokens`

- Stored in `extraction_status`.
- Occurs when restored query still contains PGMR tokens after mapping.

### Syntax errors

- Not a separate main metric category.
- Endpoint syntax errors usually appear as `prediction_execution_error`.
- Diagnostic scripts may further classify them as `endpoint_bad_request`, `likely_truncated_query`, or another execution error category.

## 14. Recommended Thesis Usage

These recommendations are based on what is implemented.

Main metrics:

- Execution Success: use `prediction_execution_success` as the main executability metric. It tells whether the model produced a supported query that the endpoint could run.
- Answer Exact Match: use `answer_exact_match` as a strict correctness metric, but explain that SELECT variable names are part of strict comparison.
- Answer F1: use `answer_f1` for row-level partial answer overlap.
- Answer Cell Value F1: use `answer_cell_value_f1` as a relaxed but important diagnostic metric for projection and label-column differences.
- KG Reference F1: use `kg_ref_f1` to measure whether the model selected the right ORKG references overall.
- Predicate/Class/Resource F1: report these as diagnostic submetrics, with emphasis on predicate F1 because relation choice is central in ORKG templates.
- PGMR Restore Success: report PGMR restoration status and summary counts for PGMR-lite runs. There is no single metric named `pgmr_restore_success`, so compute/report it from `pgmr_restore_status == "ok"` or use existing PGMR summary event counts.

Secondary/supporting metrics:

- `query_extracted`: useful for format adherence and pipeline viability.
- `supported_query_form` and `query_form_match`: useful for ASK/SELECT/form diagnosis.
- `query_bleu`: secondary text overlap only.
- `query_rouge1_f1`, `query_rouge2_f1`, `query_rougeL_f1`: secondary text overlap only.
- `pgmr_rouge*`: useful for PGMR-stage generation diagnosis.
- `query_normalized_exact_match`: very strict query-text metric; useful mainly to show exact query reproduction is rare.
- `sparql_structure_f1`: useful structural diagnostic, but not a substitute for answer correctness.
- `uri_hallucination`: useful for detecting unknown predicate/class refs against local memory.
- LLM judge scores: auxiliary semantic analysis only, not a replacement for deterministic metrics.
- Error category counts: useful for qualitative analysis and ACE feedback.

Metrics not to overemphasize:

- BLEU/ROUGE: they measure token overlap, not semantic query correctness.
- Normalized exact match: too strict for SPARQL because equivalent queries can differ in order, projection, aliases, or formatting.
- KG reference F1 alone: right identifiers can still be arranged in the wrong query structure.
- Execution success alone: executable queries can return wrong answers.
- Cell-value F1 alone: it can ignore incorrect row associations and over-credit broad queries that return many correct values plus many extras.
- LLM judge scores: useful but model-dependent and not deterministic.

Recommended reporting pattern:

1. Start with extraction and execution success to show pipeline viability.
2. Report strict answer exact match and row-level answer F1 as primary correctness.
3. Add answer cell-value F1 for relaxed answer overlap.
4. Report KG reference F1 and predicate/class/resource F1 to diagnose ORKG identifier selection.
5. For PGMR-lite, separately report restoration success/failures before answer metrics.
6. Use text similarity, SQM-lite, URI hallucination, LLM judge, and error categories as supporting analysis.

## 15. Commands to Inspect or Reproduce the Evaluation

Run all commands from the repository root.

Evaluation CLI help:

```bash
PYTHONPATH=code python code/src/main.py evaluate --help
```

LLM judge CLI help:

```bash
PYTHONPATH=code python code/tools/evaluate/run_llm_judge.py --help
```

List metric source files:

```bash
find code/src/evaluate/metrics -maxdepth 1 -type f -name '*.py' | sort
```

Search metric implementations:

```bash
rg -n "def compute_|metric_name|primary_error_category|rouge|bleu|pgmr" code/src/evaluate code/tools/evaluate code/tools/pgmr
```

Inspect available benchmark summaries:

```bash
find code/outputs/evaluation_runs -name benchmark_summary.json | sort
```

Inspect available raw evaluation outputs:

```bash
find code/outputs/evaluation_runs -name benchmark_raw.json | sort
```

Show raw output top-level keys:

```bash
jq 'keys' code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json
```

Show first raw item keys:

```bash
jq '.results[0] | keys' code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json
```

Show per-item validation metric keys:

```bash
jq '.results[0].validation | keys' code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json
```

Show summary metric keys:

```bash
jq '.summary.metrics | keys' code/outputs/evaluation_runs/<model>/<run>/benchmark_summary.json
```

Show all summary means:

```bash
jq '.summary.metrics | to_entries[] | {metric: .key, mean: .value.mean, comparable: .value.comparable_count, non_comparable: .value.non_comparable_count}' \
  code/outputs/evaluation_runs/<model>/<run>/benchmark_summary.json
```

Inspect PGMR restore failures:

```bash
jq '.results[] | select(.pgmr_restore_status != null and .pgmr_restore_status != "ok") | {id, pgmr_restore_status, pgmr_missing_mapping_tokens, pgmr_remaining_tokens}' \
  code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json
```

Count PGMR restore statuses:

```bash
jq -r '.results[].pgmr_restore_status // "not_pgmr"' code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json | sort | uniq -c
```

Show top primary error categories:

```bash
jq -r '.results[].validation.primary_error_category // "none"' code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json | sort | uniq -c | sort -nr
```

Build execution error breakdown:

```bash
PYTHONPATH=code python code/src/evaluate/analysis/execution_error_breakdown.py \
  code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json
```

Save execution error breakdown:

```bash
PYTHONPATH=code python code/src/evaluate/analysis/execution_error_breakdown.py \
  code/outputs/evaluation_runs/<model>/<run>/benchmark_raw.json \
  --output code/outputs/evaluation_runs/<model>/<run>/execution_error_breakdown.json
```

Per-family metric breakdown:

```bash
jq '.summary.slices.family' code/outputs/evaluation_runs/<model>/<run>/benchmark_summary.json
```

Compact per-family answer F1:

```bash
jq '.summary.slices.family | to_entries[] | {family: .key, answer_f1: .value.metrics.answer_f1.mean, comparable: .value.metrics.answer_f1.comparable_count}' \
  code/outputs/evaluation_runs/<model>/<run>/benchmark_summary.json
```

Inspect BLEU configuration in code:

```bash
sed -n '1,220p' code/src/evaluate/metrics/query_bleu.py
```

Inspect ROUGE configuration in code:

```bash
sed -n '1,260p' code/src/evaluate/metrics/query_rouge.py
```

Inspect answer normalization:

```bash
sed -n '1,260p' code/src/evaluate/answer_normalization.py
sed -n '1,260p' code/src/evaluate/metrics/answer_cell_value_precision_recall_f1.py
```

Inspect KG reference extraction:

```bash
sed -n '1,240p' code/src/evaluate/query_elements.py
sed -n '1,220p' code/src/evaluate/metrics/kg_ref_match.py
```

Inspect model configuration:

```bash
jq '.models | keys' code/config/model_config.json
jq '.models.gpt_5_4, .models.gpt_4o_mini, .models.qwen25_coder_7b_instruct' code/config/model_config.json
```

Example direct SPARQL evaluation command:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model qwen25_coder_7b_instruct \
  --dataset code/data/dataset/final/benchmark.json \
  --prompt-mode empire_compass \
  --prediction-format sparql
```

Example PGMR-lite evaluation command:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model qwen25_coder_7b_pgmr_qlora \
  --dataset code/data/dataset/pgmr/final/benchmark.json \
  --prompt-mode pgmr \
  --prediction-format pgmr_lite \
  --pgmr-memory-dir code/data/orkg_memory/templates \
  --pgmr-similarity-mapping
```

Example ACE-enhanced evaluation command:

```bash
PYTHONPATH=code python code/src/main.py evaluate \
  --model qwen25_coder_7b_instruct \
  --dataset code/data/dataset/final/benchmark.json \
  --prompt-mode empire_compass \
  --prediction-format sparql \
  --ace-playbook-dir code/data/dataset/final \
  --ace-mode direct_sparql \
  --ace-max-bullets 5
```

Run evaluation tests:

```bash
PYTHONPATH=code python -m pytest code/tests/evaluate -q
```

Current environment note from inspection: this command could not be completed because `pytest` is not installed in the active Python environment.
