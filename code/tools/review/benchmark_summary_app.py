from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Benchmark Summary Viewer", layout="wide")

PERCENT_METRICS = {
    "query_extracted": "Query extracted",
    "supported_query_form": "Supported query form",
    "query_form_match": "Query form match",
    "prediction_execution_success": "Prediction execution",
    "gold_execution_success": "Gold execution",
    "query_normalized_exact_match": "Query normalized exact match",
    "query_bleu": "Query BLEU",
    "sparql_structure_precision": "SPARQL structure precision",
    "sparql_structure_recall": "SPARQL structure recall",
    "sparql_structure_f1": "SPARQL structure F1",
    "answer_exact_match": "Answer exact match",
    "answer_precision": "Answer precision",
    "answer_recall": "Answer recall",
    "answer_f1": "Answer F1",
    "answer_value_exact_match": "Answer value exact match",
    "answer_value_precision": "Answer value precision",
    "answer_value_recall": "Answer value recall",
    "answer_value_f1": "Answer value F1",
    "kg_ref_precision": "KG ref precision",
    "kg_ref_recall": "KG ref recall",
    "kg_ref_f1": "KG ref F1",
    "predicate_ref_precision": "Predicate ref precision",
    "predicate_ref_recall": "Predicate ref recall",
    "predicate_ref_f1": "Predicate ref F1",
    "class_ref_precision": "Class ref precision",
    "class_ref_recall": "Class ref recall",
    "class_ref_f1": "Class ref F1",
    "resource_ref_precision": "Resource ref precision",
    "resource_ref_recall": "Resource ref recall",
    "resource_ref_f1": "Resource ref F1",
}

METRIC_GROUPS = {
    "Extraction / execution": [
        "query_extracted",
        "supported_query_form",
        "query_form_match",
        "prediction_execution_success",
        "gold_execution_success",
    ],
    "Query text / structure": [
        "query_normalized_exact_match",
        "query_bleu",
        "sparql_structure_precision",
        "sparql_structure_recall",
        "sparql_structure_f1",
    ],
    "Strict answer-based": [
        "answer_exact_match",
        "answer_precision",
        "answer_recall",
        "answer_f1",
    ],
    "Value-only answer-based": [
        "answer_value_exact_match",
        "answer_value_precision",
        "answer_value_recall",
        "answer_value_f1",
    ],
    "KG references": [
        "kg_ref_precision",
        "kg_ref_recall",
        "kg_ref_f1",
        "predicate_ref_precision",
        "predicate_ref_recall",
        "predicate_ref_f1",
        "class_ref_precision",
        "class_ref_recall",
        "class_ref_f1",
        "resource_ref_precision",
        "resource_ref_recall",
        "resource_ref_f1",
    ],
}

QUICK_READ_METRICS = [
    "query_extracted",
    "supported_query_form",
    "query_form_match",
    "prediction_execution_success",
    "query_normalized_exact_match",
    "sparql_structure_f1",
    "answer_exact_match",
    "answer_f1",
    "answer_value_f1",
    "predicate_ref_f1",
    "class_ref_f1",
]

SLICE_ORDER = [
    "family",
    "source_dataset",
    "query_type",
    "answer_type",
    "query_shape",
    "complexity_level",
]

METRIC_FILTER_PREFIX = "metric_filter__"

METRIC_HELP_MD = """
## Metric and summary field help

This viewer displays aggregated metrics from `benchmark_summary.json`.

### General table fields

- **Mean**: average score over comparable items.
- **Comparable items**: number of items for which the metric could be computed.
- **Non-comparable items**: number of items where the metric was not applicable or could not be computed.
- **Success**: number of items with score `1.0`, where this interpretation is meaningful.
- **Failure**: number of items with score `0.0`, where this interpretation is meaningful.

Some diagnostic metrics, such as URI hallucination and PGMR unmapped placeholders, are not normal success metrics. They are shown separately in the diagnostic section.

### 1. Extraction and query form

- **Query extracted**: whether a SPARQL query could be extracted from the model output.
- **Supported query form**: whether the extracted query uses a supported form, mainly `SELECT` or `ASK`.
- **Query form match**: whether the predicted query form matches the gold query form.

These metrics answer: *Did the model produce something that can be evaluated as SPARQL?*

### 2. Execution

- **Prediction execution**: whether the predicted query runs against the ORKG endpoint.
- **Gold execution**: whether the gold query runs against the ORKG endpoint.

These metrics answer: *Is the query executable?*

### 3. Strict answer-based metrics

- **Answer exact match**: whether the executed predicted answer exactly equals the executed gold answer.
- **Answer precision / recall / F1**: row-level overlap between predicted and gold answers.

Strict answer metrics include SELECT variable names.

### 4. Value-only answer metrics

These compare returned values while ignoring SELECT variable names.

They answer: *Is the answer content correct even if variable names differ?*

### 5. Query text and structure

- **Query normalized exact match**: exact match after lightweight SPARQL text normalization.
- **Query BLEU**: token-level similarity between predicted and gold SPARQL.
- **SPARQL structure F1 / SQM-lite**: structural overlap of extracted WHERE patterns.

### 6. KG reference metrics

- **KG ref F1**: overlap of all ORKG references.
- **Predicate ref F1**: overlap of `orkgp:*` predicate IDs.
- **Class ref F1**: overlap of `orkgc:*` class IDs.
- **Resource ref F1**: overlap of `orkgr:*` resource IDs.

These metrics answer: *Does the model use the correct ORKG IDs?*

### 7. URI hallucination

Checks whether predicted ORKG predicate/class references are unknown to the local ORKG/PGMR memory.

Important: this is a local-memory check, not a proof that the ID does not exist anywhere in ORKG.

### 8. PGMR unmapped placeholders

Only meaningful for PGMR-lite runs. It detects unresolved placeholders such as:

```text
{{NLP_TASK_PROPERTY}}
<NLP_TASK>
[UNMAPPED]
PGMR_UNKNOWN_PROPERTY
UNMAPPED_PREDICATE
```

For direct SPARQL runs, this metric is marked as `not_pgmr_mode`.

### Cost summary fields

Cost information is run-level metadata, not an item-quality metric.

- **Total prompt tokens**: total input tokens sent to the model.
- **Total completion tokens**: total output tokens generated by the model.
- **Total tokens**: prompt + completion tokens.
- **Total cached tokens**: prompt tokens served from cache, if reported by the provider.
- **Total estimated cost USD**: estimated API cost using the local price table.
- **Priced items**: number of result items where pricing was available.
- **Unpriced items**: number of result items with token usage but no known pricing entry.
- **Mean cost per priced item USD**: average cost over priced items only.

If `priced_items` is `0` while tokens are non-zero, the run has token usage but the model name was not found in the local cost table.
"""

METRIC_INTERPRETATION_MD = """
## How to interpret high and low values

### Values where high is good

For these metrics, higher is better:

- Query extracted
- Supported query form
- Query form match
- Prediction execution
- Gold execution
- Answer exact match
- Answer precision / recall / F1
- Answer value exact match
- Answer value precision / recall / F1
- Query normalized exact match
- Query BLEU
- SPARQL structure precision / recall / F1
- KG ref precision / recall / F1
- Predicate ref precision / recall / F1
- Class ref precision / recall / F1
- Resource ref precision / recall / F1

### Values where high is bad

For these diagnostic metrics, higher means more problems:

- URI hallucination item rate
- Mean hallucinated ref rate
- Total hallucinated refs
- PGMR unmapped item rate
- Total unmapped placeholders

### Typical interpretation patterns

#### High query extraction, low prediction execution
The model usually outputs something that looks like SPARQL, but many queries are invalid, truncated, malformed, or rejected by the endpoint.

#### High prediction execution, low answer F1
The queries run, but they return wrong answers. This usually points to semantic errors, wrong joins, wrong filters, wrong predicates, or wrong classes.

#### High class ref F1, low predicate ref F1
The model often chooses the correct template family, but it confuses the concrete ORKG properties.

#### High predicate ref F1, low answer F1
The model uses many correct ORKG IDs, but the query structure may still be wrong.

#### High answer value F1, low strict answer F1
The returned values are often correct, but variable names differ.

#### High BLEU, low answer F1
The query text is similar to gold, but a small semantic difference may break the answer.

#### Low BLEU, high answer F1
The query text differs from gold, but it still returns the correct answer.

#### High SQM-lite F1, low predicate ref F1
The structure is similar to the gold query, but the ORKG identifiers differ.

#### High URI hallucination
The model produces ORKG IDs that are not present in the local memory.

#### High PGMR unmapped placeholder rate
Only relevant for PGMR-lite. The intermediate representation was not fully grounded into executable SPARQL.

#### `not_pgmr_mode` in PGMR metrics
Expected for direct SPARQL runs such as `empire_compass`. It means the PGMR-specific metric is not applicable.
"""


def load_summary(file_obj) -> dict[str, Any]:
    return json.load(file_obj)


def percent(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "—"


def percent_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value) * 100
    except Exception:
        return None


def number(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "—"


def integer(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)


def get_summary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    if isinstance(summary, dict):
        return summary
    return payload


def extract_cost_summary(run_metadata: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    for candidate in [
        run_metadata.get("cost_summary"),
        summary.get("cost_summary"),
        summary.get("costs"),
    ]:
        if isinstance(candidate, dict):
            return candidate
    return {}


def build_run_label(filename: str, payload: dict[str, Any]) -> str:
    run_metadata = payload.get("run_metadata", {}) or {}
    parts = []
    for key in ["model_name", "prompt_mode"]:
        value = run_metadata.get(key)
        if value:
            parts.append(str(value))
    dataset = run_metadata.get("dataset_path")
    if dataset:
        parts.append(str(dataset).split("/")[-1])
    return " / ".join(parts) if parts else filename


def extract_loaded_runs(uploaded_files) -> list[dict[str, Any]]:
    runs = []
    for uploaded in uploaded_files:
        try:
            payload = load_summary(uploaded)
        except Exception as exc:
            st.error(f"{uploaded.name} konnte nicht gelesen werden: {exc}")
            continue
        run_metadata = payload.get("run_metadata", {}) or {}
        summary = get_summary_payload(payload)
        runs.append(
            {
                "filename": uploaded.name,
                "label": build_run_label(uploaded.name, payload),
                "payload": payload,
                "run_metadata": run_metadata,
                "summary": summary,
                "metrics": summary.get("metrics", {}) or {},
                "cost_summary": extract_cost_summary(run_metadata, summary),
            }
        )
    return runs


def _set_all_metric_checkboxes(value: bool) -> None:
    for metric_key in PERCENT_METRICS:
        st.session_state[f"{METRIC_FILTER_PREFIX}{metric_key}"] = value


def _sync_select_all_checkbox() -> None:
    _set_all_metric_checkboxes(bool(st.session_state.get("metric_filter_select_all", True)))


def _sync_individual_metric_checkboxes() -> None:
    st.session_state["metric_filter_select_all"] = all(
        bool(st.session_state.get(f"{METRIC_FILTER_PREFIX}{metric_key}", True))
        for metric_key in PERCENT_METRICS
    )


def initialize_metric_filter_state() -> None:
    if st.session_state.get("metric_filter_initialized"):
        return
    st.session_state["metric_filter_select_all"] = True
    _set_all_metric_checkboxes(True)
    st.session_state["metric_filter_initialized"] = True


def render_metric_filter_sidebar() -> list[str]:
    initialize_metric_filter_state()
    st.sidebar.header("Metric filter")
    st.sidebar.caption("checkboxes to select which metrics to display in the tables and charts. Metrics are grouped by category, but you can select any combination of metrics across groups.")
    st.sidebar.checkbox("Select all metrics", key="metric_filter_select_all", on_change=_sync_select_all_checkbox)

    selected_metric_keys: list[str] = []
    for group_name, metric_keys in METRIC_GROUPS.items():
        with st.sidebar.expander(group_name, expanded=True):
            for metric_key in metric_keys:
                st.checkbox(
                    PERCENT_METRICS[metric_key],
                    key=f"{METRIC_FILTER_PREFIX}{metric_key}",
                    on_change=_sync_individual_metric_checkboxes,
                )
                if st.session_state.get(f"{METRIC_FILTER_PREFIX}{metric_key}", False):
                    selected_metric_keys.append(metric_key)
    if not selected_metric_keys:
        st.sidebar.warning("at least one metric must be selected")
    return selected_metric_keys


def build_metrics_table(metrics: dict[str, Any], selected_metric_keys: list[str]) -> pd.DataFrame:
    rows = []
    for key in selected_metric_keys:
        metric = metrics.get(key, {}) or {}
        rows.append(
            {
                "Metric": PERCENT_METRICS[key],
                "Mean": percent(metric.get("mean")),
                "Comparable items": metric.get("comparable_count", 0),
                "Non-comparable items": metric.get("non_comparable_count", 0),
                "Success": metric.get("success_count", "—"),
                "Failure": metric.get("failure_count", "—"),
            }
        )
    return pd.DataFrame(rows)


def build_comparison_metrics_table(runs: list[dict[str, Any]], selected_metric_keys: list[str]) -> pd.DataFrame:
    rows = []
    for metric_key in selected_metric_keys:
        row = {"Metric": PERCENT_METRICS[metric_key]}
        for run in runs:
            row[run["label"]] = percent((run["metrics"].get(metric_key) or {}).get("mean"))
        rows.append(row)
    return pd.DataFrame(rows)


def build_comparison_metrics_numeric(runs: list[dict[str, Any]], selected_metric_keys: list[str]) -> pd.DataFrame:
    rows = []
    for metric_key in selected_metric_keys:
        for run in runs:
            rows.append(
                {
                    "Run": run["label"],
                    "Metric": PERCENT_METRICS[metric_key],
                    "Score": percent_number((run["metrics"].get(metric_key) or {}).get("mean")),
                }
            )
    return pd.DataFrame(rows)


def build_delta_table(runs: list[dict[str, Any]], baseline_label: str, selected_metric_keys: list[str]) -> pd.DataFrame:
    baseline_run = next((run for run in runs if run["label"] == baseline_label), None)
    if baseline_run is None:
        return pd.DataFrame()
    rows = []
    for metric_key in selected_metric_keys:
        baseline_value = percent_number((baseline_run["metrics"].get(metric_key) or {}).get("mean"))
        row = {
            "Metric": PERCENT_METRICS[metric_key],
            f"Baseline ({baseline_label})": "—" if baseline_value is None else f"{baseline_value:.1f}%",
        }
        for run in runs:
            if run["label"] == baseline_label:
                continue
            value = percent_number((run["metrics"].get(metric_key) or {}).get("mean"))
            row[f"Δ {run['label']}"] = "—" if value is None or baseline_value is None else f"{value - baseline_value:+.1f} pp"
        rows.append(row)
    return pd.DataFrame(rows)


def build_error_table(error_categories: dict[str, Any]) -> pd.DataFrame:
    rows = [{"Error category": key, "Count": value} for key, value in (error_categories or {}).items()]
    return pd.DataFrame(rows or [{"Error category": "none", "Count": 0}])


def build_error_comparison_table(runs: list[dict[str, Any]]) -> pd.DataFrame:
    all_error_categories = set()
    for run in runs:
        all_error_categories.update((run["summary"].get("error_categories", {}) or {}).keys())
    rows = []
    for category in sorted(all_error_categories):
        row = {"Error category": category}
        for run in runs:
            row[run["label"]] = (run["summary"].get("error_categories", {}) or {}).get(category, 0)
        rows.append(row)
    return pd.DataFrame(rows or [{"Error category": "none", **{run["label"]: 0 for run in runs}}])


def build_cost_table(cost_summary: dict[str, Any]) -> pd.DataFrame:
    if not cost_summary:
        return pd.DataFrame([{"Field": "Cost summary", "Value": "No cost summary available"}])
    rows = [
        ("Total prompt tokens", cost_summary.get("total_prompt_tokens")),
        ("Total completion tokens", cost_summary.get("total_completion_tokens")),
        ("Total tokens", cost_summary.get("total_tokens")),
        ("Total cached tokens", cost_summary.get("total_cached_tokens")),
        ("Total estimated cost USD", cost_summary.get("total_estimated_cost_usd")),
        ("Priced items", cost_summary.get("priced_items")),
        ("Unpriced items", cost_summary.get("unpriced_items")),
        ("Mean cost per priced item USD", cost_summary.get("mean_cost_per_priced_item_usd")),
    ]
    return pd.DataFrame([{"Field": label, "Value": "—" if value is None else value} for label, value in rows])


def build_cost_comparison_table(runs: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for run in runs:
        cost = run.get("cost_summary") or {}
        rows.append(
            {
                "Run": run["label"],
                "Total prompt tokens": cost.get("total_prompt_tokens", "—"),
                "Total completion tokens": cost.get("total_completion_tokens", "—"),
                "Total tokens": cost.get("total_tokens", "—"),
                "Total cached tokens": cost.get("total_cached_tokens", "—"),
                "Total estimated cost USD": cost.get("total_estimated_cost_usd", "—"),
                "Priced items": cost.get("priced_items", "—"),
                "Unpriced items": cost.get("unpriced_items", "—"),
                "Mean cost per priced item USD": cost.get("mean_cost_per_priced_item_usd", "—"),
            }
        )
    return pd.DataFrame(rows)


def build_diagnostic_table(metrics: dict[str, Any]) -> pd.DataFrame:
    rows = []
    uri = metrics.get("uri_hallucination")
    if isinstance(uri, dict):
        rows.append(
            {
                "Diagnostic": "URI hallucination",
                "Comparable items": uri.get("comparable_count", 0),
                "Non-comparable items": uri.get("non_comparable_count", 0),
                "Affected item rate": percent(uri.get("hallucinated_item_rate")),
                "Affected items": uri.get("hallucinated_item_count", "—"),
                "Clean items": uri.get("clean_item_count", "—"),
                "Total findings": uri.get("total_hallucinated_ref_count", "—"),
                "Mean finding count": number(uri.get("mean_hallucinated_ref_count"), 4),
                "Mean finding rate": percent(uri.get("mean_hallucinated_ref_rate")),
            }
        )
    pgmr = metrics.get("pgmr_unmapped_placeholders")
    if isinstance(pgmr, dict):
        rows.append(
            {
                "Diagnostic": "PGMR unmapped placeholders",
                "Comparable items": pgmr.get("comparable_count", 0),
                "Non-comparable items": pgmr.get("non_comparable_count", 0),
                "Affected item rate": percent(pgmr.get("unmapped_item_rate")),
                "Affected items": pgmr.get("unmapped_item_count", "—"),
                "Clean items": pgmr.get("clean_item_count", "—"),
                "Total findings": pgmr.get("total_unmapped_placeholder_count", "—"),
                "Mean finding count": number(pgmr.get("mean_unmapped_placeholder_count"), 4),
                "Mean finding rate": "—",
                "Not PGMR mode": pgmr.get("not_pgmr_mode_count", "—"),
            }
        )
    return pd.DataFrame(rows)


def build_diagnostic_comparison_table(runs: list[dict[str, Any]]) -> pd.DataFrame:
    specs = [
        ("URI hallucination item rate", "uri_hallucination", "hallucinated_item_rate", percent),
        ("URI mean hallucinated ref rate", "uri_hallucination", "mean_hallucinated_ref_rate", percent),
        ("URI total hallucinated refs", "uri_hallucination", "total_hallucinated_ref_count", lambda v: "—" if v is None else str(v)),
        ("PGMR unmapped item rate", "pgmr_unmapped_placeholders", "unmapped_item_rate", percent),
        ("PGMR total unmapped placeholders", "pgmr_unmapped_placeholders", "total_unmapped_placeholder_count", lambda v: "—" if v is None else str(v)),
        ("PGMR not-PGMR-mode count", "pgmr_unmapped_placeholders", "not_pgmr_mode_count", lambda v: "—" if v is None else str(v)),
    ]
    rows = []
    for label, metric_key, field_key, formatter in specs:
        row = {"Diagnostic": label}
        for run in runs:
            row[run["label"]] = formatter((run["metrics"].get(metric_key) or {}).get(field_key))
        rows.append(row)
    return pd.DataFrame(rows)


def build_slice_table(slice_payload: dict[str, Any], selected_metric_keys: list[str]) -> pd.DataFrame:
    rows = []
    for slice_value, payload in (slice_payload or {}).items():
        metrics = payload.get("metrics", {}) or {}
        response_time = payload.get("response_time_seconds", {}) or {}
        error_categories = payload.get("error_categories", {}) or {}
        top_error = max(error_categories.items(), key=lambda x: x[1])[0] if error_categories else "—"
        row = {"Value": slice_value, "Items": payload.get("item_count", 0)}
        for key in selected_metric_keys:
            row[PERCENT_METRICS[key]] = percent((metrics.get(key) or {}).get("mean"))
        row["Avg response time (s)"] = number(response_time.get("mean_seconds"), 3)
        row["Top error"] = top_error
        rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["Items", "Value"], ascending=[False, True]).reset_index(drop=True)
    return df


def build_slice_comparison_table(runs: list[dict[str, Any]], selected_slice: str, selected_metric: str) -> pd.DataFrame:
    all_values = set()
    for run in runs:
        all_values.update(((run["summary"].get("slices", {}) or {}).get(selected_slice, {}) or {}).keys())
    rows = []
    for value in sorted(all_values):
        row = {"Slice value": value}
        for run in runs:
            payload = (((run["summary"].get("slices", {}) or {}).get(selected_slice, {}) or {}).get(value, {}) or {})
            metric = (payload.get("metrics", {}) or {}).get(selected_metric, {}) or {}
            row[f"{run['label']} items"] = payload.get("item_count", 0)
            row[f"{run['label']} score"] = percent(metric.get("mean"))
        rows.append(row)
    return pd.DataFrame(rows)


def render_help_section() -> None:
    with st.expander("Metric help: what do the parameters mean?", expanded=False):
        st.markdown(METRIC_HELP_MD)
    with st.expander("Metric interpretation: what does high/low mean?", expanded=False):
        st.markdown(METRIC_INTERPRETATION_MD)


def render_cost_summary_single(cost: dict[str, Any]) -> None:
    st.subheader("Cost summary")
    if not cost:
        st.info("No cost summary available in this benchmark_summary.json.")
        return
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total tokens", integer(cost.get("total_tokens")))
    col2.metric("Cached tokens", integer(cost.get("total_cached_tokens")))
    col3.metric("Estimated cost USD", number(cost.get("total_estimated_cost_usd"), 6))
    col4.metric("Priced items", integer(cost.get("priced_items")))
    st.dataframe(build_cost_table(cost), use_container_width=True, hide_index=True)
    if int(cost.get("total_tokens") or 0) > 0 and int(cost.get("priced_items") or 0) == 0:
        st.warning("Token usage exists, but no priced items were found. This usually means the model name is missing from the local pricing table.")


def render_overview_single(run: dict[str, Any]) -> None:
    metadata = run["run_metadata"]
    summary = run["summary"]
    st.subheader("Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Model", metadata.get("model_name", "—"))
    col2.metric("Prompt mode", metadata.get("prompt_mode", "—"))
    col3.metric("Total items", summary.get("total_items", metadata.get("total_items", 0)))
    col4.metric("Avg response time", f"{number((summary.get('response_time_seconds') or {}).get('mean_seconds'), 3)} s")
    with st.expander("Run metadata", expanded=False):
        st.json(metadata)
    render_cost_summary_single(run.get("cost_summary") or {})


def render_overview_comparison(runs: list[dict[str, Any]]) -> None:
    st.subheader("Runs")
    rows = []
    for run in runs:
        metadata = run["run_metadata"]
        summary = run["summary"]
        cost = run.get("cost_summary") or {}
        rows.append(
            {
                "Run": run["label"],
                "Filename": run["filename"],
                "Model": metadata.get("model_name", "—"),
                "Prompt mode": metadata.get("prompt_mode", "—"),
                "Total items": summary.get("total_items", metadata.get("total_items", 0)),
                "Avg response time (s)": number((summary.get("response_time_seconds") or {}).get("mean_seconds"), 3),
                "Total tokens": cost.get("total_tokens", "—"),
                "Estimated cost USD": cost.get("total_estimated_cost_usd", "—"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_health_bar(metrics: dict[str, Any], selected_metric_keys: list[str]) -> None:
    st.subheader("Quick read")
    quick_keys = [key for key in QUICK_READ_METRICS if key in selected_metric_keys]
    if not quick_keys:
        st.info("Keine Quick-read-Metriken ausgewählt.")
        return
    rows = []
    for key in quick_keys:
        value = (metrics.get(key) or {}).get("mean")
        rows.append({"Metric": PERCENT_METRICS[key], "Score": 0.0 if value is None else float(value)})
    st.bar_chart(pd.DataFrame(rows).set_index("Metric"))


def render_diagnostics(metrics: dict[str, Any]) -> None:
    df = build_diagnostic_table(metrics)
    if df.empty:
        return
    st.subheader("Diagnostic metrics")
    st.dataframe(df, use_container_width=True, hide_index=True)
    for key, label in [("uri_hallucination", "URI hallucination details"), ("pgmr_unmapped_placeholders", "PGMR unmapped placeholder details")]:
        metric = metrics.get(key)
        if isinstance(metric, dict):
            with st.expander(label, expanded=False):
                st.json(metric)


def render_comparison_view(runs: list[dict[str, Any]], selected_metric_keys: list[str]) -> None:
    render_overview_comparison(runs)
    st.subheader("Cost comparison")
    st.dataframe(build_cost_comparison_table(runs), use_container_width=True, hide_index=True)
    st.subheader("Overall metric comparison")
    st.dataframe(build_comparison_metrics_table(runs, selected_metric_keys), use_container_width=True, hide_index=True)

    numeric_df = build_comparison_metrics_numeric(runs, selected_metric_keys).dropna(subset=["Score"])
    if not numeric_df.empty:
        selected_chart_metric = st.selectbox("Metric für Chart auswählen", list(dict.fromkeys(numeric_df["Metric"].tolist())), index=0)
        st.bar_chart(numeric_df[numeric_df["Metric"] == selected_chart_metric].set_index("Run")[["Score"]])
    else:
        st.info("Keine numerischen Metriken für den Chart ausgewählt.")

    st.subheader("Diagnostic metric comparison")
    st.dataframe(build_diagnostic_comparison_table(runs), use_container_width=True, hide_index=True)

    st.subheader("Delta comparison")
    baseline_label = st.selectbox("Baseline auswählen", [run["label"] for run in runs], index=0)
    st.dataframe(build_delta_table(runs, baseline_label, selected_metric_keys), use_container_width=True, hide_index=True)

    st.subheader("Error category comparison")
    st.dataframe(build_error_comparison_table(runs), use_container_width=True, hide_index=True)

    st.subheader("Slice comparison")
    all_slice_keys = set()
    for run in runs:
        all_slice_keys.update((run["summary"].get("slices", {}) or {}).keys())
    available_slice_keys = [key for key in SLICE_ORDER if key in all_slice_keys]
    available_slice_keys += sorted(all_slice_keys - set(available_slice_keys))
    if not available_slice_keys:
        st.info("Keine Slice-Daten vorhanden.")
        return
    if not selected_metric_keys:
        st.info("Keine Metrik für Slice-Vergleich ausgewählt.")
        return
    selected_slice = st.selectbox("Slice auswählen", available_slice_keys)
    selected_metric_label = st.selectbox("Slice-Metrik auswählen", [PERCENT_METRICS[key] for key in selected_metric_keys], index=0)
    selected_metric_key = next(key for key, label in PERCENT_METRICS.items() if label == selected_metric_label)
    st.dataframe(build_slice_comparison_table(runs, selected_slice, selected_metric_key), use_container_width=True, hide_index=True)


def render_single_view(run: dict[str, Any], selected_metric_keys: list[str]) -> None:
    summary = run["summary"]
    metrics = run["metrics"]
    render_overview_single(run)
    render_health_bar(metrics, selected_metric_keys)
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Overall metrics")
        st.dataframe(build_metrics_table(metrics, selected_metric_keys), use_container_width=True, hide_index=True)
    with right:
        st.subheader("Error categories")
        error_df = build_error_table(summary.get("error_categories", {}))
        st.dataframe(error_df, use_container_width=True, hide_index=True)
        if not error_df.empty:
            st.bar_chart(error_df.set_index("Error category"))
    render_diagnostics(metrics)
    st.subheader("Slice analysis")
    slices = summary.get("slices", {}) or {}
    available_slice_keys = [key for key in SLICE_ORDER if key in slices] or list(slices.keys())
    if available_slice_keys:
        selected_slice = st.selectbox("Slice auswählen", available_slice_keys)
        st.dataframe(build_slice_table(slices.get(selected_slice, {}), selected_metric_keys), use_container_width=True, hide_index=True)
    else:
        st.info("Keine Slice-Daten vorhanden.")
    with st.expander("Raw summary JSON", expanded=False):
        st.json(run["payload"])


def main() -> None:
    st.title("Benchmark Summary Viewer")
    st.caption("Lädt eine oder mehrere benchmark_summary.json Dateien. Bei mehreren Dateien werden die Runs miteinander verglichen.")
    render_help_section()
    selected_metric_keys = render_metric_filter_sidebar()
    uploaded_files = st.file_uploader("Eine oder mehrere benchmark_summary.json hochladen", type=["json"], accept_multiple_files=True)
    if not uploaded_files:
        st.info("Lade hier eine oder mehrere benchmark_summary.json Dateien hoch.")
        return
    runs = extract_loaded_runs(uploaded_files)
    if not runs:
        st.error("Keine gültige Summary-Datei konnte geladen werden.")
        return
    seen: dict[str, int] = {}
    for run in runs:
        seen[run["label"]] = seen.get(run["label"], 0) + 1
    duplicates = {label for label, count in seen.items() if count > 1}
    for run in runs:
        if run["label"] in duplicates:
            run["label"] = f"{run['label']} ({run['filename']})"
    if len(runs) == 1:
        render_single_view(runs[0], selected_metric_keys)
    else:
        render_comparison_view(runs, selected_metric_keys)
        with st.expander("Raw summaries", expanded=False):
            selected_run = st.selectbox("Raw JSON für Run anzeigen", [run["label"] for run in runs])
            st.json(next(run for run in runs if run["label"] == selected_run)["payload"])


if __name__ == "__main__":
    main()