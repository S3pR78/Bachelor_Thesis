import json
from pathlib import Path
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
    "answer_exact_match": "Answer exact match",
    "answer_precision": "Answer precision",
    "answer_recall": "Answer recall",
    "answer_f1": "Answer F1",
}

SLICE_ORDER = [
    "family",
    "source_dataset",
    "query_type",
    "answer_type",
    "query_shape",
    "complexity_level",
]


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


def build_run_label(filename: str, payload: dict[str, Any]) -> str:
    run_metadata = payload.get("run_metadata", {}) or {}

    model = run_metadata.get("model_name")
    prompt_mode = run_metadata.get("prompt_mode")
    dataset = run_metadata.get("dataset_path")

    parts = []
    if model:
        parts.append(str(model))
    if prompt_mode:
        parts.append(str(prompt_mode))

    if parts:
        return " / ".join(parts)

    return filename


def extract_loaded_runs(uploaded_files) -> list[dict[str, Any]]:
    runs = []

    for uploaded in uploaded_files:
        try:
            payload = load_summary(uploaded)
        except Exception as exc:
            st.error(f"{uploaded.name} konnte nicht gelesen werden: {exc}")
            continue

        run_metadata = payload.get("run_metadata", {}) or {}
        summary = payload.get("summary", {}) or {}

        runs.append(
            {
                "filename": uploaded.name,
                "label": build_run_label(uploaded.name, payload),
                "payload": payload,
                "run_metadata": run_metadata,
                "summary": summary,
                "metrics": summary.get("metrics", {}) or {},
            }
        )

    return runs


def build_metrics_table(metrics: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for key, label in PERCENT_METRICS.items():
        metric = metrics.get(key, {}) or {}
        rows.append(
            {
                "Metric": label,
                "Mean": percent(metric.get("mean")),
                "Comparable items": metric.get("comparable_count", 0),
                "Non-comparable items": metric.get("non_comparable_count", 0),
                "Success": metric.get("success_count", "—"),
                "Failure": metric.get("failure_count", "—"),
            }
        )
    return pd.DataFrame(rows)


def build_comparison_metrics_table(runs: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []

    for metric_key, metric_label in PERCENT_METRICS.items():
        row = {"Metric": metric_label}

        for run in runs:
            metric = (run["metrics"].get(metric_key) or {})
            row[run["label"]] = percent(metric.get("mean"))

        rows.append(row)

    return pd.DataFrame(rows)


def build_comparison_metrics_numeric(runs: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []

    for metric_key, metric_label in PERCENT_METRICS.items():
        for run in runs:
            metric = (run["metrics"].get(metric_key) or {})
            value = percent_number(metric.get("mean"))

            rows.append(
                {
                    "Run": run["label"],
                    "Metric": metric_label,
                    "Score": value,
                }
            )

    return pd.DataFrame(rows)


def build_delta_table(runs: list[dict[str, Any]], baseline_label: str) -> pd.DataFrame:
    baseline_run = next((run for run in runs if run["label"] == baseline_label), None)
    if baseline_run is None:
        return pd.DataFrame()

    rows = []

    for metric_key, metric_label in PERCENT_METRICS.items():
        baseline_value = percent_number(
            (baseline_run["metrics"].get(metric_key) or {}).get("mean")
        )

        row = {
            "Metric": metric_label,
            f"Baseline ({baseline_label})": "—" if baseline_value is None else f"{baseline_value:.1f}%",
        }

        for run in runs:
            if run["label"] == baseline_label:
                continue

            value = percent_number((run["metrics"].get(metric_key) or {}).get("mean"))

            if value is None or baseline_value is None:
                row[f"Δ {run['label']}"] = "—"
            else:
                delta = value - baseline_value
                row[f"Δ {run['label']}"] = f"{delta:+.1f} pp"

        rows.append(row)

    return pd.DataFrame(rows)


def build_error_table(error_categories: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {"Error category": key, "Count": value}
        for key, value in (error_categories or {}).items()
    ]
    if not rows:
        rows = [{"Error category": "none", "Count": 0}]
    return pd.DataFrame(rows)


def build_error_comparison_table(runs: list[dict[str, Any]]) -> pd.DataFrame:
    all_error_categories = set()

    for run in runs:
        error_categories = run["summary"].get("error_categories", {}) or {}
        all_error_categories.update(error_categories.keys())

    rows = []

    for category in sorted(all_error_categories):
        row = {"Error category": category}
        for run in runs:
            error_categories = run["summary"].get("error_categories", {}) or {}
            row[run["label"]] = error_categories.get(category, 0)
        rows.append(row)

    if not rows:
        rows = [{"Error category": "none", **{run["label"]: 0 for run in runs}}]

    return pd.DataFrame(rows)


def build_slice_table(slice_payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for slice_value, payload in (slice_payload or {}).items():
        metrics = payload.get("metrics", {}) or {}
        response_time = payload.get("response_time_seconds", {}) or {}
        error_categories = payload.get("error_categories", {}) or {}
        top_error = max(error_categories.items(), key=lambda x: x[1])[0] if error_categories else "—"

        rows.append(
            {
                "Value": slice_value,
                "Items": payload.get("item_count", 0),
                "Query extracted": percent((metrics.get("query_extracted") or {}).get("mean")),
                "Prediction execution": percent((metrics.get("prediction_execution_success") or {}).get("mean")),
                "Exact match": percent((metrics.get("answer_exact_match") or {}).get("mean")),
                "Answer F1": percent((metrics.get("answer_f1") or {}).get("mean")),
                "Avg response time (s)": number(response_time.get("mean_seconds"), 3),
                "Top error": top_error,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["Items", "Value"], ascending=[False, True]).reset_index(drop=True)
    return df


def build_slice_comparison_table(
    runs: list[dict[str, Any]],
    selected_slice: str,
    selected_metric: str,
) -> pd.DataFrame:
    all_values = set()

    for run in runs:
        slices = run["summary"].get("slices", {}) or {}
        slice_payload = slices.get(selected_slice, {}) or {}
        all_values.update(slice_payload.keys())

    rows = []

    for value in sorted(all_values):
        row = {"Slice value": value}

        for run in runs:
            slices = run["summary"].get("slices", {}) or {}
            slice_payload = slices.get(selected_slice, {}) or {}
            payload = slice_payload.get(value, {}) or {}

            item_count = payload.get("item_count", 0)
            metrics = payload.get("metrics", {}) or {}
            metric = metrics.get(selected_metric, {}) or {}

            row[f"{run['label']} items"] = item_count
            row[f"{run['label']} score"] = percent(metric.get("mean"))

        rows.append(row)

    return pd.DataFrame(rows)


def render_overview_single(run_metadata: dict[str, Any], summary: dict[str, Any]) -> None:
    st.subheader("Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Model", run_metadata.get("model_name", "—"))
    col2.metric("Prompt mode", run_metadata.get("prompt_mode", "—"))
    col3.metric("Total items", summary.get("total_items", run_metadata.get("total_items", 0)))
    col4.metric(
        "Avg response time",
        f"{number((summary.get('response_time_seconds') or {}).get('mean_seconds'), 3)} s",
    )

    with st.expander("Run metadata", expanded=False):
        st.json(run_metadata)


def render_overview_comparison(runs: list[dict[str, Any]]) -> None:
    st.subheader("Runs")

    rows = []
    for run in runs:
        run_metadata = run["run_metadata"]
        summary = run["summary"]

        rows.append(
            {
                "Run": run["label"],
                "Filename": run["filename"],
                "Model": run_metadata.get("model_name", "—"),
                "Prompt mode": run_metadata.get("prompt_mode", "—"),
                "Total items": summary.get("total_items", run_metadata.get("total_items", 0)),
                "Avg response time (s)": number(
                    (summary.get("response_time_seconds") or {}).get("mean_seconds"),
                    3,
                ),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_health_bar(metrics: dict[str, Any]) -> None:
    st.subheader("Quick read")

    quick = pd.DataFrame(
        {
            "Metric": [
                "Query extracted",
                "Supported form",
                "Query form match",
                "Prediction execution",
                "Answer exact match",
                "Answer F1",
            ],
            "Score": [
                (metrics.get("query_extracted") or {}).get("mean", 0.0),
                (metrics.get("supported_query_form") or {}).get("mean", 0.0),
                (metrics.get("query_form_match") or {}).get("mean", 0.0),
                (metrics.get("prediction_execution_success") or {}).get("mean", 0.0),
                (metrics.get("answer_exact_match") or {}).get("mean", 0.0),
                (metrics.get("answer_f1") or {}).get("mean", 0.0),
            ],
        }
    )

    st.bar_chart(quick.set_index("Metric"))


def render_comparison_view(runs: list[dict[str, Any]]) -> None:
    render_overview_comparison(runs)

    st.subheader("Overall metric comparison")
    comparison_df = build_comparison_metrics_table(runs)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    numeric_df = build_comparison_metrics_numeric(runs)
    numeric_df = numeric_df.dropna(subset=["Score"])

    if not numeric_df.empty:
        selected_chart_metric = st.selectbox(
            "Metric für Chart auswählen",
            list(PERCENT_METRICS.values()),
            index=list(PERCENT_METRICS.values()).index("Answer F1")
            if "Answer F1" in PERCENT_METRICS.values()
            else 0,
        )

        chart_df = numeric_df[numeric_df["Metric"] == selected_chart_metric]
        chart_df = chart_df.set_index("Run")[["Score"]]
        st.bar_chart(chart_df)

    st.subheader("Delta comparison")
    baseline_label = st.selectbox(
        "Baseline auswählen",
        [run["label"] for run in runs],
        index=0,
    )
    delta_df = build_delta_table(runs, baseline_label)
    st.dataframe(delta_df, use_container_width=True, hide_index=True)

    st.subheader("Error category comparison")
    error_comparison_df = build_error_comparison_table(runs)
    st.dataframe(error_comparison_df, use_container_width=True, hide_index=True)

    st.subheader("Slice comparison")
    all_slice_keys = set()
    for run in runs:
        slices = run["summary"].get("slices", {}) or {}
        all_slice_keys.update(slices.keys())

    available_slice_keys = [key for key in SLICE_ORDER if key in all_slice_keys]
    available_slice_keys += sorted(all_slice_keys - set(available_slice_keys))

    if not available_slice_keys:
        st.info("Keine Slice-Daten vorhanden.")
        return

    selected_slice = st.selectbox("Slice auswählen", available_slice_keys)

    selected_metric_label = st.selectbox(
        "Slice-Metrik auswählen",
        list(PERCENT_METRICS.values()),
        index=list(PERCENT_METRICS.values()).index("Answer F1")
        if "Answer F1" in PERCENT_METRICS.values()
        else 0,
    )

    selected_metric_key = next(
        key for key, label in PERCENT_METRICS.items()
        if label == selected_metric_label
    )

    slice_comparison_df = build_slice_comparison_table(
        runs=runs,
        selected_slice=selected_slice,
        selected_metric=selected_metric_key,
    )

    st.dataframe(slice_comparison_df, use_container_width=True, hide_index=True)


def render_single_view(run: dict[str, Any]) -> None:
    run_metadata = run["run_metadata"]
    summary = run["summary"]
    metrics = run["metrics"]

    render_overview_single(run_metadata, summary)
    render_health_bar(metrics)

    left, right = st.columns([2, 1])

    with left:
        st.subheader("Overall metrics")
        st.dataframe(build_metrics_table(metrics), use_container_width=True, hide_index=True)

    with right:
        st.subheader("Error categories")
        error_df = build_error_table(summary.get("error_categories", {}))
        st.dataframe(error_df, use_container_width=True, hide_index=True)
        if not error_df.empty:
            chart_df = error_df.set_index("Error category")
            st.bar_chart(chart_df)

    st.subheader("Slice analysis")
    slices = summary.get("slices", {}) or {}
    available_slice_keys = [key for key in SLICE_ORDER if key in slices] or list(slices.keys())

    if available_slice_keys:
        selected_slice = st.selectbox("Slice auswählen", available_slice_keys)
        slice_df = build_slice_table(slices.get(selected_slice, {}))
        st.dataframe(slice_df, use_container_width=True, hide_index=True)
    else:
        st.info("Keine Slice-Daten vorhanden.")

    with st.expander("Raw summary JSON", expanded=False):
        st.json(run["payload"])


def main() -> None:
    st.title("Benchmark Summary Viewer")
    st.caption(
        "Lädt eine oder mehrere benchmark_summary.json Dateien. "
        "Bei mehreren Dateien werden die Runs miteinander verglichen."
    )

    uploaded_files = st.file_uploader(
        "Eine oder mehrere benchmark_summary.json hochladen",
        type=["json"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("Lade hier eine oder mehrere benchmark_summary.json Dateien hoch.")
        return

    runs = extract_loaded_runs(uploaded_files)

    if not runs:
        st.error("Keine gültige Summary-Datei konnte geladen werden.")
        return

    # Falls Labels doppelt sind, Dateiname anhängen.
    seen = {}
    for run in runs:
        label = run["label"]
        seen[label] = seen.get(label, 0) + 1

    duplicates = {label for label, count in seen.items() if count > 1}
    for run in runs:
        if run["label"] in duplicates:
            run["label"] = f"{run['label']} ({run['filename']})"

    if len(runs) == 1:
        render_single_view(runs[0])
    else:
        render_comparison_view(runs)

        with st.expander("Raw summaries", expanded=False):
            selected_run = st.selectbox(
                "Raw JSON für Run anzeigen",
                [run["label"] for run in runs],
            )
            run = next(run for run in runs if run["label"] == selected_run)
            st.json(run["payload"])


if __name__ == "__main__":
    main()