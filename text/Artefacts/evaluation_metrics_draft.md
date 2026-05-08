## Evaluation Pipeline and Metrics

The evaluation in this thesis is designed to measure not only whether a model can generate syntactically usable SPARQL, but also whether the generated query returns the intended ORKG answer and uses the correct template-specific identifiers. This is necessary because Text-to-SPARQL over ORKG templates is not a pure text generation task. A prediction must follow the expected query form, use the correct ORKG predicates, classes, and resources, execute successfully against the ORKG endpoint, and return the same information as the reference query.

Evaluation is started through the repository's `evaluate` command. For each benchmark item, the pipeline loads the natural-language question and the gold SPARQL query, builds the final prompt according to the selected prompt mode, calls the configured model, stores the raw model output, extracts or restores an evaluable SPARQL query, executes both the predicted and gold queries against the configured ORKG SPARQL endpoint, and computes validation metrics. The item-level results are written to `benchmark_raw.json`, while aggregated results are written to `benchmark_summary.json`.

The same evaluation pipeline is used for direct SPARQL and PGMR-lite runs, but the prediction post-processing differs. In direct SPARQL mode, the model output is cleaned and the first detected `SELECT`, `ASK`, `CONSTRUCT`, or `DESCRIBE` query is extracted. Standard ORKG prefixes are prepended when needed. In PGMR-lite mode, the model first produces a query with PGMR placeholders. This query is post-processed and restored to ORKG compact identifiers before it can be executed. If restoration fails because a placeholder cannot be mapped, the prediction is treated as not executable for the execution- and answer-based metrics, while the missing mappings are stored as diagnostic information.

The execution-based evaluator supports `SELECT` and `ASK` queries. For `ASK` queries, the result is normalized to a boolean value. For `SELECT` queries, result rows are normalized as sets, so row order and duplicate rows do not affect the comparison. The strict row-level comparison still preserves variable names, which is important because wrong or incomplete projections are a recurring error type in this task.

### Metrics used in the thesis

Table 1 summarizes the metrics reported in this thesis. The table gives the thesis-facing metric name, the corresponding repository metric or output field, and the role of the metric. The detailed interpretation follows in the subsequent subsections.

| Thesis metric name | Repository metric / field | Category | Short interpretation |
| --- | --- | --- | --- |
| **Executable Query Rate** | `prediction_execution_success` | Main deterministic metric | Proportion of predicted queries that execute successfully against the ORKG SPARQL endpoint. |
| **Strict Answer Match** | `answer_exact_match` | Main deterministic metric | Strict equality between normalized predicted and gold execution results; includes variable names for `SELECT` queries. |
| **Answer Value F1** | `answer_cell_value_f1` | Main deterministic metric | F1 over individual answer cell values, ignoring variable names, column order, row order, and row grouping. |
| **KG Reference F1** | `kg_ref_f1` | Main deterministic metric | F1 over ORKG predicates, classes, and resources used in the predicted and gold SPARQL queries. |
| **SPARQL Structure F1** | `sparql_structure_f1` | Structural diagnostic metric | F1 over lightweight normalized WHERE-body patterns with normalized variable names and order-insensitive pattern matching. |
| **Query BLEU** | `query_bleu` | Textual diagnostic metric | One BLEU score over normalized SPARQL tokens with maximum n-gram order 4, smoothing, and brevity penalty. |
| **Query ROUGE-2 F1** | `query_rouge2_f1` | Textual diagnostic metric | Bigram-based ROUGE F1 over normalized SPARQL tokens. |
| **Query ROUGE-L F1** | `query_rougeL_f1` | Textual diagnostic metric | Longest-common-subsequence ROUGE F1 over normalized SPARQL tokens. |
| **Mean Response Time** | `response_time_seconds.mean` | Practical metric | Average model response time per benchmark item. |
| **LLM Judge Overall Score** | `overall_score` | Auxiliary LLM judge metric | Reference-guided semantic score from 0 to 10. |
| **LLM Judge Verdict** | `verdict` | Auxiliary LLM judge metric | Categorical judgment: `correct`, `partially_correct`, or `incorrect`. |
| **Intent Score** | `intent_score` | Auxiliary LLM judge metric | Score from 0 to 2 for whether the prediction captures the question intent. |
| **Schema Score** | `schema_score` | Auxiliary LLM judge metric | Score from 0 to 2 for correct ORKG template, predicate, and class usage. |
| **Projection Score** | `projection_score` | Auxiliary LLM judge metric | Score from 0 to 2 for whether the selected variables answer the question. |
| **Main Issue** | `main_issue` | Qualitative error-analysis field | Short qualitative signal describing the main judged problem; not treated as a deterministic metric. |

### Main deterministic metrics

The first main metric is **Executable Query Rate**, corresponding to the repository metric `prediction_execution_success`. It measures the proportion of predicted queries that can be executed successfully against the ORKG SPARQL endpoint. This metric captures a basic practical requirement: a generated query must be syntactically and operationally valid enough to run. However, executability does not imply correctness. A query may execute successfully while using the wrong predicate, missing a filter, selecting the wrong variable, or returning an unrelated result set. Therefore, this metric is interpreted as a necessary but not sufficient condition for successful Text-to-SPARQL generation.

The second main metric is **Strict Answer Match**, corresponding to `answer_exact_match`. It compares the normalized execution result of the predicted query with the normalized execution result of the gold query. For `ASK` queries, the boolean values are compared directly. For `SELECT` queries, the comparison is strict at the row level and includes the variable names. This makes the metric a high-confidence correctness signal: if a prediction receives a positive strict answer match, it returned the same structured answer as the gold query under the repository's normalization rules. At the same time, this strictness can penalize predictions that return relevant values but use different variable names or a slightly different projection.

The third main metric is **Answer Value F1**, corresponding to `answer_cell_value_f1`. In contrast to strict row-level comparison, this metric compares individual answer cell values. It ignores variable names, column order, row order, and row grouping. This is useful for ORKG template queries because many model predictions return semantically relevant resources or labels but differ from the gold query in projection details. For example, a model may return a label column instead of a resource variable, or include an additional label column together with the correct resource. In such cases, strict answer matching can be too harsh, while value-level overlap provides a more informative partial-credit signal. Its limitation is that it can over-credit broad or wrongly joined queries: because it ignores row associations, a query that returns many relevant values in the wrong combinations may still receive a relatively high value-level F1 score.

The fourth main metric is **KG Reference F1**, corresponding to `kg_ref_f1`. This metric compares the ORKG references used in the predicted and gold SPARQL queries. These references include ORKG predicates, classes, and resources. It therefore measures whether the model is grounded in the correct ORKG schema and template vocabulary. This is especially relevant for the two template families studied in this thesis, because many errors are caused not by malformed SPARQL but by selecting the wrong ORKG property or class. Nevertheless, KG Reference F1 does not prove full query correctness. A query may use the right identifiers but connect them in the wrong structure, omit required filters, or project the wrong variables.

### Structural and textual diagnostic metrics

In addition to answer- and identifier-based metrics, the evaluation reports structural and textual diagnostics. These metrics are not treated as primary correctness measures, but they help explain model behavior when answer metrics alone are insufficient.

**SPARQL Structure F1**, corresponding to `sparql_structure_f1`, compares lightweight normalized WHERE-body patterns. The metric ignores pattern order and normalizes variable names. This makes it less brittle than exact query text comparison and useful for measuring whether the predicted query follows a similar structural pattern to the gold query. For example, it can help distinguish a query that is structurally close but uses a wrong predicate from a query that has a completely different shape. However, it is still not a semantic-equivalence metric: two structurally different queries can return the same answer, and two structurally similar queries can return different answers.

**Query BLEU**, corresponding to `query_bleu`, is a lightweight BLEU score over normalized SPARQL tokens with a maximum n-gram order of four. It is one combined BLEU score, not separate BLEU-1, BLEU-2, BLEU-3, and BLEU-4 scores. The implementation uses modified n-gram precision, smoothing, and a brevity penalty. **Query ROUGE-2 F1**, corresponding to `query_rouge2_f1`, measures bigram-based ROUGE F1 over normalized SPARQL tokens. **Query ROUGE-L F1**, corresponding to `query_rougeL_f1`, measures longest-common-subsequence overlap. These metrics provide textual similarity diagnostics, but they are secondary in this thesis. A high BLEU or ROUGE score can still hide wrong predicates, wrong joins, or missing filters, while a low score can occur for a semantically equivalent query written in a different order or style.

For practical efficiency, the evaluation also reports **Mean Response Time**, based on the `response_time_seconds` aggregation in the evaluation outputs. This value measures the average model response time per benchmark item. It is not a quality metric, but it is relevant for comparing the practical usability of different approaches, especially when comparing small fine-tuned models, larger local instruction models, and API-based baselines.

### LLM judge as auxiliary semantic analysis

The deterministic metrics are the primary evaluation basis of this thesis. However, a post-hoc LLM judge is included as an auxiliary analysis layer. The motivation is that some gold queries contain domain- and template-specific modeling decisions that are not fully explicit in the natural-language question. Although the dataset and paraphrased examples were reviewed, the wording of some questions can still underspecify the full ORKG query structure. In such cases, strict comparison against the gold query may mark a prediction as wrong even when it captures a plausible interpretation of the question.

A representative example is the question: "How often are which empirical methods used?" The gold query selects `?paper` and `?dc_method_type_label`, restricts the contribution to the Empirical Research Practice class, includes the year relation, restricts the venue to the IEEE International Requirements Engineering Conference, follows the data-collection path to the method type, and filters out `"no collection"` values. Several of these modeling decisions are template-specific: the question does not explicitly mention the venue constraint, the exact data-collection path, or the exclusion filter. A model prediction may therefore be partially reasonable from the natural-language wording while still differing from the gold query. The LLM judge is used to analyze such cases qualitatively, not to replace deterministic metrics.

The implemented judge is a post-hoc tool rather than part of the main evaluation loop. It reads an existing `benchmark_raw.json` file and writes `llm_judge_raw.json`, `llm_judge_summary.json`, and optionally `benchmark_summary_with_llm_judge.json`. In automatic prediction-field mode, it prefers restored SPARQL queries in the order `pgmr_restored_query`, `restored_query`, `extracted_query`, `predicted_query`, and finally `raw_model_output`. The judge receives the natural-language question, the template family, the gold SPARQL query, and the predicted or restored SPARQL query. It does not receive execution result tables, so it evaluates only the query text.

The judge outputs **LLM Judge Overall Score** (`overall_score`) on a 0--10 scale and **LLM Judge Verdict** (`verdict`) with the labels `correct`, `partially_correct`, and `incorrect`. The overall score is based on five 0--2 rubric dimensions: **Intent Score** (`intent_score`), **Schema Score** (`schema_score`), **Projection Score** (`projection_score`), **Constraint Score** (`constraint_score`), and **Aggregation Score** (`aggregation_score`). The thesis focuses especially on Intent Score, Schema Score, and Projection Score. Intent Score measures whether the predicted query captures the main question intent. Schema Score measures whether the query uses the correct ORKG template family, classes, and properties. Projection Score measures whether the selected variables answer the question, which is important because wrong or overloaded `SELECT` projections were a recurring challenge. The field **Main Issue** (`main_issue`) is used as a qualitative error-analysis signal rather than as a deterministic metric.

The following excerpt from the implemented judge prompt is included because it defines the actual rubric used in the repository:

```text
Your task is not exact string matching.
Judge whether the predicted SPARQL query is semantically appropriate for the question.

Important:
The gold query is a reference, but it may contain more SELECT variables than the question strictly requires.
Do not penalize the predicted query only because it selects fewer or different variables if the selected variables are semantically sufficient for the question.

Evaluate only the query text. Do not assume access to execution results.

intent_score: 0-2
- 0 = wrong topic or wrong task
- 1 = partially captures the question intent
- 2 = captures the main question intent

schema_score: 0-2
- 0 = wrong ORKG template family or mostly wrong properties/classes
- 1 = partially correct ORKG structure
- 2 = central ORKG classes/properties are correct

projection_score: 0-2
- 0 = SELECT variables do not answer the question
- 1 = SELECT variables are partly useful but incomplete or overloaded
- 2 = SELECT variables are semantically appropriate for the question

constraint_score: 0-2
- 0 = important constraints are missing or wrong
- 1 = some constraints are correct, others missing
- 2 = relevant constraints are correct

aggregation_score: 0-2
- 0 = aggregation is wrong or missing when clearly required
- 1 = aggregation is partly appropriate or ambiguous
- 2 = aggregation is correct, or aggregation is correctly not needed

verdict must be exactly one of:
- correct
- partially_correct
- incorrect
```

This judge design is related to the broader idea of LLM-as-a-judge evaluation. Zheng et al. describe LLM judges as a scalable and explainable alternative to costly human evaluation and distinguish pairwise comparison, single-answer grading, and reference-guided grading. The implementation in this thesis is closest to reference-guided single-answer grading because the judge scores one predicted query with access to a gold SPARQL reference. At the same time, LLM-based judgments are treated cautiously. Prior work reports limitations such as position bias, verbosity bias, self-enhancement bias, and limited reasoning ability. Therefore, judge scores are used only as auxiliary evidence for semantic error analysis and not as a replacement for endpoint execution and deterministic answer comparison.

### Secondary diagnostics and excluded metrics

Several implemented metrics are useful for debugging but are not used as primary thesis metrics. `query_extracted` measures whether any evaluable query could be extracted from the model output; `supported_query_form` checks whether the prediction is a supported `SELECT` or `ASK` query; and `query_form_match` detects mismatches such as predicting an `ASK` query for a `SELECT` gold query. These metrics help diagnose format and query-form failures, but they do not measure semantic correctness. Similarly, `gold_execution_success` is monitored to detect benchmark or endpoint problems, but it is not a model-quality metric.

The repository also contains more fine-grained diagnostic information such as predicate, class, and resource reference scores, URI hallucination checks, PGMR restoration statuses, unresolved-placeholder diagnostics, and error categories such as missing extracted queries, unsupported query forms, endpoint errors, likely truncated queries, and answer mismatches. These diagnostics are valuable for error analysis and for improving prompts or ACE playbooks, but they are not reported as the main final results because they either describe pipeline conditions, PGMR restoration behavior, or specific error subtypes rather than overall model quality.

Overall, the final evaluation combines complementary perspectives. Executable Query Rate measures whether predictions can be run. Strict Answer Match gives a conservative correctness signal. Answer Value F1 captures relaxed answer overlap when projections differ. KG Reference F1 measures ORKG schema grounding. SPARQL Structure F1 and query-level BLEU/ROUGE provide structural and textual diagnostics. Mean Response Time captures practical efficiency. Finally, the LLM judge adds a qualitative semantic layer for cases where natural-language questions do not fully specify all template-specific modeling decisions. This combination is better suited to practical Text-to-SPARQL over ORKG templates than relying on any single metric alone.

### Reference used for the LLM judge discussion

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. NeurIPS 2023 Datasets and Benchmarks Track.
