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


def number(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "—"


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


def build_error_table(error_categories: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {"Error category": key, "Count": value}
        for key, value in (error_categories or {}).items()
    ]
    if not rows:
        rows = [{"Error category": "none", "Count": 0}]
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


def render_overview(run_metadata: dict[str, Any], summary: dict[str, Any]) -> None:
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


def main() -> None:
    st.title("Benchmark Summary Viewer")
    st.caption("Lädt eine benchmark_summary.json und zeigt die wichtigsten Ergebnisse verständlich an.")

    uploaded = st.file_uploader(
        "benchmark_summary.json hochladen",
        type=["json"],
        accept_multiple_files=False,
    )

    if uploaded is None:
        st.info("Lade hier deine benchmark_summary.json hoch.")
        return

    try:
        payload = load_summary(uploaded)
    except Exception as exc:
        st.error(f"Datei konnte nicht gelesen werden: {exc}")
        return

    run_metadata = payload.get("run_metadata", {}) or {}
    summary = payload.get("summary", {}) or {}
    metrics = summary.get("metrics", {}) or {}

    render_overview(run_metadata, summary)
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
        st.json(payload)


if __name__ == "__main__":
    main()
