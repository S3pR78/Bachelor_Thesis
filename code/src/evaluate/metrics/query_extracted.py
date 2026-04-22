from __future__ import annotations

from src.evaluate.metrics.common import build_metric


def compute_query_extracted(has_extracted_query: bool) -> dict:
    return build_metric(
        metric_name="query_extracted",
        metric_type="structural",
        comparable=True,
        value=1.0 if has_extracted_query else 0.0,
    )
