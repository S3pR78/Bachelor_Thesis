"""Build ACE error traces from benchmark_raw.json evaluation outputs."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


KNOWN_METRIC_KEYS = {
    "query_extracted",
    "supported_query_form",
    "query_form_match",
    "prediction_execution_success",
    "gold_execution_success",
    "answer_exact_match",
    "answer_precision",
    "answer_recall",
    "answer_f1",
    "predicate_ref_match",
    "class_ref_match",
    "resource_ref_match",
    "pgmr_unmapped_placeholders",
}


@dataclass
class AceTraceItem:
    """One evaluation item reduced to the fields useful for ACE reflection."""
    item_id: str
    family: str | None
    split: str | None
    question: str | None
    mode: str
    categories: list[str]
    metrics: dict[str, Any] = field(default_factory=dict)
    raw_model_output: str | None = None
    extracted_query: str | None = None
    restored_query: str | None = None
    gold_sparql: str | None = None
    error_text: str | None = None
    source: dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return bool(self.categories)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "family": self.family,
            "split": self.split,
            "question": self.question,
            "mode": self.mode,
            "categories": self.categories,
            "metrics": self.metrics,
            "raw_model_output": self.raw_model_output,
            "extracted_query": self.extracted_query,
            "restored_query": self.restored_query,
            "gold_sparql": self.gold_sparql,
            "error_text": self.error_text,
            "source": self.source,
        }


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _scalarize(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ["value", "score", "passed", "success", "correct", "is_correct"]:
            if key in value:
                return _scalarize(value[key])
    return value


def _as_bool(value: Any) -> bool | None:
    value = _scalarize(value)

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "ok", "success", "passed", "1"}:
            return True
        if normalized in {"false", "no", "error", "failed", "fail", "0"}:
            return False

    return None


def _as_float(value: Any) -> float | None:
    value = _scalarize(value)

    if isinstance(value, bool):
        return float(value)

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None

    return None


def _find_first_key(
    obj: Any,
    candidate_keys: list[str],
    *,
    max_depth: int = 6,
) -> Any:
    if max_depth < 0:
        return None

    normalized_candidates = {_normalize_key(key) for key in candidate_keys}

    if isinstance(obj, dict):
        for key, value in obj.items():
            if _normalize_key(str(key)) in normalized_candidates:
                return value

        for value in obj.values():
            found = _find_first_key(
                value,
                candidate_keys,
                max_depth=max_depth - 1,
            )
            if found is not None:
                return found

    elif isinstance(obj, list):
        for value in obj:
            found = _find_first_key(
                value,
                candidate_keys,
                max_depth=max_depth - 1,
            )
            if found is not None:
                return found

    return None


def _first_text(obj: Any, candidate_keys: list[str]) -> str | None:
    value = _find_first_key(obj, candidate_keys)

    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)

    text = str(value).strip()
    return text or None


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in [
        "results",
        "items",
        "records",
        "examples",
        "predictions",
        "raw_results",
        "benchmark_results",
    ]:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    for value in payload.values():
        if isinstance(value, list) and value and all(
            isinstance(item, dict) for item in value
        ):
            return value

    return [payload]


def _extract_metrics(record: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}

    for container_key in ["metrics", "metric_results", "scores", "summary_metrics"]:
        container = record.get(container_key)
        if isinstance(container, dict):
            for key, value in container.items():
                normalized = _normalize_key(str(key))
                if normalized in KNOWN_METRIC_KEYS:
                    metrics[normalized] = _scalarize(value)

    for key in KNOWN_METRIC_KEYS:
        value = _find_first_key(record, [key])
        if value is not None:
            metrics[key] = _scalarize(value)

    return metrics


def _metric_bool(metrics: dict[str, Any], key: str) -> bool | None:
    if key not in metrics:
        return None
    return _as_bool(metrics[key])


def _metric_float(metrics: dict[str, Any], key: str) -> float | None:
    if key not in metrics:
        return None
    return _as_float(metrics[key])


def _has_unmapped_pgmr(record: dict[str, Any], metrics: dict[str, Any]) -> bool:
    metric_value = _metric_float(metrics, "pgmr_unmapped_placeholders")
    if metric_value is not None and metric_value > 0:
        return True

    value = _find_first_key(
        record,
        [
            "pgmr_unmapped_placeholders",
            "unmapped_placeholders",
            "missing_token_counts",
            "missing_tokens",
        ],
    )

    if isinstance(value, dict):
        return any(_as_float(item) not in {None, 0.0} for item in value.values())

    if isinstance(value, list):
        return len(value) > 0

    if isinstance(value, str):
        return bool(value.strip())

    return False


def _restore_failed(record: dict[str, Any]) -> bool:
    status = _first_text(
        record,
        [
            "pgmr_restore_status",
            "restore_status",
            "postprocess_status",
        ],
    )

    if status:
        normalized = status.lower()
        if normalized not in {"ok", "success", "successful", "restored", "none"}:
            return True

    error = _first_text(
        record,
        [
            "pgmr_restore_error",
            "restore_error",
            "postprocess_error",
        ],
    )

    return bool(error)


def _collect_error_text(record: dict[str, Any]) -> str | None:
    texts: list[str] = []

    for key in [
        "error",
        "error_message",
        "exception",
        "prediction_error",
        "execution_error",
        "endpoint_error",
    ]:
        value = _first_text(record, [key])
        if value:
            texts.append(value)

    if not texts:
        return None

    return "\n".join(dict.fromkeys(texts))


def categorize_record(record: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
    categories: list[str] = []

    query_extracted = _metric_bool(metrics, "query_extracted")
    if query_extracted is False:
        categories.append("no_extracted_query")

    supported_form = _metric_bool(metrics, "supported_query_form")
    if supported_form is False:
        categories.append("unsupported_query_form")

    query_form_match = _metric_bool(metrics, "query_form_match")
    if query_form_match is False:
        categories.append("query_form_mismatch")

    prediction_execution = _metric_bool(metrics, "prediction_execution_success")
    if prediction_execution is False:
        categories.append("prediction_execution_error")

    gold_execution = _metric_bool(metrics, "gold_execution_success")
    if gold_execution is False:
        categories.append("gold_execution_error")

    answer_exact = _metric_bool(metrics, "answer_exact_match")
    answer_f1 = _metric_float(metrics, "answer_f1")
    if answer_exact is False or (answer_f1 is not None and answer_f1 < 0.999):
        categories.append("answer_mismatch")

    for key, category in [
        ("predicate_ref_match", "predicate_ref_mismatch"),
        ("class_ref_match", "class_ref_mismatch"),
        ("resource_ref_match", "resource_ref_mismatch"),
    ]:
        value = _metric_float(metrics, key)
        if value is not None and value < 0.999:
            categories.append(category)

    if _has_unmapped_pgmr(record, metrics):
        categories.append("pgmr_unmapped_placeholders")

    if _restore_failed(record):
        categories.append("pgmr_restore_error")

    error_text = _collect_error_text(record) or ""
    lowered_error = error_text.lower()

    if "400" in lowered_error or "bad request" in lowered_error:
        categories.append("endpoint_bad_request")

    if "414" in lowered_error or "uri too long" in lowered_error:
        categories.append("endpoint_uri_too_long")

    explicit_error_category = _first_text(
        record,
        [
            "error_category",
            "failure_category",
            "failure_reason",
        ],
    )
    if explicit_error_category:
        categories.append(_normalize_key(explicit_error_category))

    return sorted(dict.fromkeys(categories))


def build_trace_item(
    record: dict[str, Any],
    *,
    index: int,
    source_raw_path: str,
    mode: str,
) -> AceTraceItem:
    metrics = _extract_metrics(record)
    categories = categorize_record(record, metrics)

    item_id = (
        _first_text(record, ["id", "item_id", "entry_id", "source_id"])
        or f"idx_{index}"
    )

    return AceTraceItem(
        item_id=item_id,
        family=_first_text(record, ["family", "template_family"]),
        split=_first_text(record, ["split"]),
        question=_first_text(record, ["question", "natural_language_question"]),
        mode=mode,
        categories=categories,
        metrics=metrics,
        raw_model_output=_first_text(
            record,
            ["raw_model_output", "model_output", "raw_prediction", "completion"],
        ),
        extracted_query=_first_text(
            record,
            [
                "extracted_query",
                "extracted_sparql",
                "prediction_sparql",
                "predicted_sparql",
                "predicted_query",
            ],
        ),
        restored_query=_first_text(
            record,
            [
                "restored_query",
                "restored_sparql",
                "postprocessed_query",
                "postprocessed_sparql",
            ],
        ),
        gold_sparql=_first_text(record, ["gold_sparql", "gold_query"]),
        error_text=_collect_error_text(record),
        source={
            "raw_path": source_raw_path,
            "record_index": index,
        },
    )


def build_trace_report(
    *,
    raw_path: str | Path,
    mode: str,
    family: str | None = None,
    split: str | None = None,
    include_success: bool = False,
) -> dict[str, Any]:
    path = Path(raw_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = _extract_records(payload)

    traces: list[AceTraceItem] = []
    for index, record in enumerate(records):
        trace = build_trace_item(
            record,
            index=index,
            source_raw_path=str(path),
            mode=mode,
        )

        if family and trace.family != family:
            continue

        if split and trace.split != split:
            continue

        if not include_success and not trace.is_error:
            continue

        traces.append(trace)

    category_counts = Counter(
        category for trace in traces for category in trace.categories
    )

    return {
        "source_raw_path": str(path),
        "mode": mode,
        "family_filter": family,
        "split_filter": split,
        "include_success": include_success,
        "total_records_in_raw": len(records),
        "trace_count": len(traces),
        "error_trace_count": sum(1 for trace in traces if trace.is_error),
        "category_counts": dict(category_counts.most_common()),
        "traces": [trace.to_dict() for trace in traces],
    }


def save_trace_report(report: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
