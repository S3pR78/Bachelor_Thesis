from __future__ import annotations

from typing import Any

SUPPORTED_QUERY_FORMS = {"select", "ask"}


def build_metric(
    metric_name: str,
    metric_type: str,
    comparable: bool,
    value: float | None,
    reason: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metric": metric_name,
        "type": metric_type,
        "comparable": comparable,
        "value": round(float(value), 4) if value is not None else None,
    }

    if reason is not None:
        payload["reason"] = reason

    payload.update(extra)
    return payload


def round_metric_payload(metric_payload: dict[str, Any]) -> dict[str, Any]:
    rounded = dict(metric_payload)

    for key in ("value", "precision", "recall", "f1"):
        value = rounded.get(key)
        if isinstance(value, (int, float)):
            rounded[key] = round(float(value), 4)

    return rounded
