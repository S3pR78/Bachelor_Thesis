from __future__ import annotations

from src.ace.reflector import reflect_trace_report


def test_reflector_generates_rule_for_unmapped_pgmr_placeholders() -> None:
    trace_report = {
        "mode": "pgmr_lite",
        "family_filter": "nlp4re",
        "traces": [
            {
                "item_id": "810",
                "family": "nlp4re",
                "mode": "pgmr_lite",
                "question": "Which outputs are used?",
                "categories": ["pgmr_unmapped_placeholders"],
                "extracted_query": "SELECT ?x WHERE { ?x pgmr:unknown_token ?y . }",
            }
        ],
    }

    delta_report = reflect_trace_report(
        trace_report=trace_report,
        trace_path="ace_error_traces.json",
        min_support=1,
    )

    categories = {
        delta["bullet"]["category"] for delta in delta_report["deltas"]
    }

    assert "pgmr_unmapped_placeholders" in categories

    placeholder_delta = next(
        delta
        for delta in delta_report["deltas"]
        if delta["bullet"]["category"] == "pgmr_unmapped_placeholders"
    )

    assert "Use only known PGMR placeholders" == placeholder_delta["bullet"]["title"]
    assert "810" in placeholder_delta["bullet"]["evidence_item_ids"]


def test_reflector_detects_missing_nlp4re_pgmr_contribution_pattern() -> None:
    trace_report = {
        "mode": "pgmr_lite",
        "family_filter": "nlp4re",
        "traces": [
            {
                "item_id": "42",
                "family": "nlp4re",
                "mode": "pgmr_lite",
                "question": "Which NLP tasks are used?",
                "categories": ["answer_mismatch"],
                "extracted_query": "SELECT ?task WHERE { ?paper pgmr:nlp_task ?task . }",
            }
        ],
    }

    delta_report = reflect_trace_report(
        trace_report=trace_report,
        trace_path="ace_error_traces.json",
        min_support=1,
    )

    missing_pattern_delta = next(
        delta
        for delta in delta_report["deltas"]
        if delta["bullet"]["category"] == "missing_contribution_pattern"
    )

    assert missing_pattern_delta["bullet"]["title"] == "Use the paper-to-contribution pattern"
    assert "pgmr:has_contribution" in missing_pattern_delta["bullet"]["positive_pattern"]
    assert "pgmrc:nlp4re_contribution" in missing_pattern_delta["bullet"]["positive_pattern"]


def test_reflector_respects_min_support() -> None:
    trace_report = {
        "mode": "pgmr_lite",
        "family_filter": "nlp4re",
        "traces": [
            {
                "item_id": "1",
                "family": "nlp4re",
                "mode": "pgmr_lite",
                "question": "Which metrics are used?",
                "categories": ["answer_mismatch"],
            }
        ],
    }

    delta_report = reflect_trace_report(
        trace_report=trace_report,
        trace_path="ace_error_traces.json",
        min_support=2,
    )

    assert delta_report["delta_count"] == 0


def test_reflector_generates_venue_filter_rule() -> None:
    trace_report = {
        "mode": "direct_sparql",
        "family_filter": "empirical_research_practice",
        "traces": [
            {
                "item_id": "venue-1",
                "family": "empirical_research_practice",
                "mode": "direct_sparql",
                "question": "Which papers were published at IEEE International Requirements Engineering Conference?",
                "categories": ["answer_mismatch"],
                "extracted_query": "SELECT ?paper WHERE { ?paper orkgp:P31 ?contribution . }",
            }
        ],
    }

    delta_report = reflect_trace_report(
        trace_report=trace_report,
        trace_path="ace_error_traces.json",
        min_support=1,
    )

    venue_delta = next(
        delta
        for delta in delta_report["deltas"]
        if delta["bullet"]["category"] == "missing_venue_filter"
    )

    assert "venue" in venue_delta["bullet"]["title"].lower()
    assert "orkgp:P135046" in venue_delta["bullet"]["positive_pattern"]
