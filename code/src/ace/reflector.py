from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.ace.playbook import AceDelta


DELTA_SCHEMA_VERSION = "ace_delta_v1"


REFLECTABLE_CATEGORIES = {
    "no_extracted_query",
    "unsupported_query_form",
    "query_form_mismatch",
    "prediction_execution_error",
    "endpoint_bad_request",
    "endpoint_uri_too_long",
    "answer_mismatch",
    "predicate_ref_mismatch",
    "class_ref_mismatch",
    "resource_ref_mismatch",
    "pgmr_unmapped_placeholders",
    "pgmr_restore_error",
    "missing_contribution_pattern",
    "missing_venue_filter",
}


def _normalize(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _prediction_text(trace: dict[str, Any]) -> str:
    for key in ["restored_query", "extracted_query", "raw_model_output"]:
        value = trace.get(key)
        if value:
            return str(value)
    return ""


def _question_text(trace: dict[str, Any]) -> str:
    return str(trace.get("question") or "")


def _detect_missing_contribution_pattern(trace: dict[str, Any]) -> bool:
    family = _normalize(trace.get("family"))
    mode = _normalize(trace.get("mode"))
    query = _prediction_text(trace).lower()

    if not family or not query:
        return False

    if family == "nlp4re" and mode == "pgmr_lite":
        nlp4re_field_tokens = [
            "pgmr:nlp",
            "pgmr:task",
            "pgmr:dataset",
            "pgmr:evaluation",
            "pgmr:metric",
            "pgmr:output",
            "pgmr:approach",
            "pgmr:has_evaluation",
        ]
        uses_family_fields = any(token in query for token in nlp4re_field_tokens)
        has_pattern = (
            "pgmr:has_contribution" in query
            and "pgmrc:nlp4re_contribution" in query
        )
        return uses_family_fields and not has_pattern

    if mode == "direct_sparql":
        uses_orkg_predicates = "orkgp:" in query
        if not uses_orkg_predicates:
            return False

        if family == "nlp4re":
            return not ("orkgp:p31" in query and "orkgc:c121001" in query)

        if family == "empirical_research_practice":
            return not ("orkgp:p31" in query and "orkgc:c27001" in query)

    return False


def _detect_missing_venue_filter(trace: dict[str, Any]) -> bool:
    question = _question_text(trace).lower()
    query = _prediction_text(trace).lower()

    if not question or not query:
        return False

    asks_for_venue = any(
        token in question
        for token in [
            "venue",
            "conference",
            "ieee international requirements engineering conference",
        ]
    )

    if not asks_for_venue:
        return False

    has_label_filter = "rdfs:label" in query and "filter" in query
    return not has_label_filter


def enrich_categories(trace: dict[str, Any]) -> list[str]:
    categories = list(trace.get("categories") or [])

    if _detect_missing_contribution_pattern(trace):
        categories.append("missing_contribution_pattern")

    if _detect_missing_venue_filter(trace):
        categories.append("missing_venue_filter")

    return sorted(dict.fromkeys(categories))


def _contribution_pattern_for(family: str, mode: str) -> tuple[str | None, str]:
    normalized_family = _normalize(family)
    normalized_mode = _normalize(mode)

    if normalized_mode == "pgmr_lite":
        if normalized_family == "nlp4re":
            return (
                "?paper pgmr:has_contribution ?contribution . "
                "?contribution a pgmrc:nlp4re_contribution .",
                "Do not attach NLP task, dataset, metric, evaluation, or output properties directly to ?paper.",
            )

        if normalized_family == "empirical_research_practice":
            return (
                "?paper pgmr:has_contribution ?contribution . "
                "?contribution a the empirical-research-practice contribution class from the PGMR memory.",
                "Do not attach empirical-research fields directly to ?paper.",
            )

    if normalized_mode == "direct_sparql":
        if normalized_family == "nlp4re":
            return (
                "?paper orkgp:P31 ?contribution . ?contribution a orkgc:C121001 .",
                "Do not access NLP4RE-specific properties without first binding ?contribution.",
            )

        if normalized_family == "empirical_research_practice":
            return (
                "?paper orkgp:P31 ?contribution . ?contribution a orkgc:C27001 .",
                "Do not access empirical-research-practice properties without first binding ?contribution.",
            )

    return (
        None,
        "Do not attach template-specific properties directly to ?paper when the template uses contributions.",
    )


def _venue_pattern_for(mode: str) -> tuple[str | None, str]:
    normalized_mode = _normalize(mode)

    if normalized_mode == "direct_sparql":
        return (
            "?contribution orkgp:P135046 ?venue . "
            "?venue rdfs:label ?venue_name . "
            'FILTER(LCASE(STR(?venue_name)) = LCASE("IEEE International Requirements Engineering Conference"))',
            "Do not omit the venue label filter when the question asks for a specific venue or conference.",
        )

    if normalized_mode == "pgmr_lite":
        return (
            "?contribution pgmr:venue ?venue . "
            "?venue rdfs:label ?venue_name . "
            'FILTER(LCASE(STR(?venue_name)) = LCASE("IEEE International Requirements Engineering Conference"))',
            "Use the venue placeholder defined in the PGMR memory/prompt; do not invent a new venue token.",
        )

    return (
        None,
        "Do not omit explicit venue filters when the question restricts results to a venue or conference.",
    )


def _build_bullet_payload(
    *,
    family: str,
    mode: str,
    category: str,
    support_count: int,
    evidence_item_ids: list[str],
    trace_path: str,
) -> dict[str, Any] | None:
    priority_bonus = min(support_count, 10)

    base_payload: dict[str, Any] = {
        "family": family or "global",
        "mode": mode or "any",
        "category": category,
        "bullet_type": "validation_lesson",
        "priority": 50 + priority_bonus,
        "enabled": True,
        "source": {
            "type": "ace_reflector",
            "trace_path": trace_path,
            "support_count": support_count,
        },
        "evidence_item_ids": evidence_item_ids,
        "helpful_count": 0,
        "harmful_count": 0,
    }

    if category == "no_extracted_query":
        return {
            **base_payload,
            "title": "Return only the final query",
            "content": "The output must be only one complete SPARQL or PGMR-lite query, without explanation, markdown prose, or analysis.",
            "avoid": "Do not answer in natural language and do not include reasoning text before the query.",
            "priority": 95 + priority_bonus,
        }

    if category == "unsupported_query_form":
        return {
            **base_payload,
            "title": "Use a supported SPARQL query form",
            "content": "Generate only supported SPARQL forms such as SELECT or ASK unless the task explicitly requires another supported form.",
            "avoid": "Do not output fragments, pseudo-code, JSON, or incomplete graph patterns.",
            "priority": 85 + priority_bonus,
        }

    if category == "query_form_mismatch":
        return {
            **base_payload,
            "title": "Match the query form to the question type",
            "content": "Use ASK for yes/no questions and SELECT for questions asking for lists, labels, years, venues, datasets, tasks, metrics, or other values.",
            "avoid": "Do not use ASK when the question asks which/what/list/count values should be returned.",
            "priority": 88 + priority_bonus,
        }

    if category in {"prediction_execution_error", "endpoint_bad_request"}:
        return {
            **base_payload,
            "title": "Generate executable complete queries",
            "content": "Ensure the query has balanced braces, declared variables, valid triple patterns, and no unfinished FILTER, OPTIONAL, or SELECT clauses.",
            "avoid": "Do not return truncated queries or isolated triple patterns without SELECT/ASK and WHERE.",
            "priority": 82 + priority_bonus,
        }

    if category == "endpoint_uri_too_long":
        return {
            **base_payload,
            "title": "Keep generated queries compact",
            "content": "Avoid unnecessarily long repeated patterns and do not duplicate the same triple patterns or filters.",
            "avoid": "Do not generate repeated long UNION or duplicated blocks unless required by the question.",
            "priority": 70 + priority_bonus,
        }

    if category == "answer_mismatch":
        return {
            **base_payload,
            "title": "Preserve all semantic constraints from the question",
            "content": "Include the requested entity type, template family, filters, and returned variable so the execution result matches the question semantics.",
            "avoid": "Do not produce a broad executable query that ignores the requested field or filter.",
            "priority": 78 + priority_bonus,
        }

    if category == "predicate_ref_mismatch":
        return {
            **base_payload,
            "title": "Use the correct predicate for the requested role",
            "content": "Choose predicates according to the semantic role in the question, such as task, dataset, metric, output, evaluation, year, venue, or contribution link.",
            "avoid": "Do not replace one template field with a similar-looking but semantically different predicate.",
            "priority": 80 + priority_bonus,
        }

    if category == "class_ref_mismatch":
        pattern, avoid = _contribution_pattern_for(family, mode)
        return {
            **base_payload,
            "title": "Use the correct template family class",
            "content": "Bind contributions with the class that belongs to the current template family before using family-specific fields.",
            "positive_pattern": pattern,
            "avoid": avoid,
            "priority": 84 + priority_bonus,
        }

    if category == "resource_ref_mismatch":
        return {
            **base_payload,
            "title": "Keep named resources and labels aligned with the question",
            "content": "When the question names a venue, task, dataset, metric, method, or resource, bind and filter the corresponding label/resource explicitly.",
            "avoid": "Do not silently replace named resources with a more general variable.",
            "priority": 76 + priority_bonus,
        }

    if category == "pgmr_unmapped_placeholders":
        return {
            **base_payload,
            "title": "Use only known PGMR placeholders",
            "content": "Use only pgmr:/pgmrc: placeholders that are defined in the PGMR prompt or memory for the current family.",
            "avoid": "Do not invent new pgmr:/pgmrc: tokens and do not mix PGMR placeholders with real ORKG IDs.",
            "priority": 92 + priority_bonus,
        }

    if category == "pgmr_restore_error":
        return {
            **base_payload,
            "title": "Generate restorable PGMR-lite",
            "content": "The PGMR-lite query must use valid placeholders, complete triple patterns, and the expected paper-to-contribution structure so it can be deterministically restored.",
            "avoid": "Do not output partial PGMR, unknown placeholders, or a mixture of PGMR and direct ORKG identifiers.",
            "priority": 90 + priority_bonus,
        }

    if category == "missing_contribution_pattern":
        pattern, avoid = _contribution_pattern_for(family, mode)
        return {
            **base_payload,
            "title": "Use the paper-to-contribution pattern",
            "content": "Connect papers to contributions before accessing template-specific fields.",
            "positive_pattern": pattern,
            "avoid": avoid,
            "priority": 96 + priority_bonus,
        }

    if category == "missing_venue_filter":
        pattern, avoid = _venue_pattern_for(mode)
        return {
            **base_payload,
            "title": "Include venue label filters when requested",
            "content": "When the question restricts results to a venue or conference, include the venue relation, label binding, and label FILTER.",
            "positive_pattern": pattern,
            "avoid": avoid,
            "priority": 86 + priority_bonus,
        }

    return None


def reflect_trace_report(
    *,
    trace_report: dict[str, Any],
    trace_path: str,
    min_support: int = 1,
    max_evidence_items: int = 5,
) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for trace in trace_report.get("traces", []):
        family = str(trace.get("family") or trace_report.get("family_filter") or "global")
        mode = str(trace.get("mode") or trace_report.get("mode") or "any")

        for category in enrich_categories(trace):
            if category not in REFLECTABLE_CATEGORIES:
                continue
            grouped[(family, mode, category)].append(trace)

    deltas: list[AceDelta] = []

    for (family, mode, category), traces in sorted(grouped.items()):
        support_count = len(traces)
        if support_count < min_support:
            continue

        evidence_item_ids = [
            str(trace.get("item_id"))
            for trace in traces[:max_evidence_items]
            if trace.get("item_id") is not None
        ]

        bullet_payload = _build_bullet_payload(
            family=family,
            mode=mode,
            category=category,
            support_count=support_count,
            evidence_item_ids=evidence_item_ids,
            trace_path=trace_path,
        )

        if bullet_payload is None:
            continue

        deltas.append(
            AceDelta.from_dict(
                {
                    "operation": "add",
                    "bullet": bullet_payload,
                    "reason": (
                        f"Validation feedback produced {support_count} trace(s) "
                        f"for category '{category}'."
                    ),
                    "evidence": {
                        "category": category,
                        "support_count": support_count,
                        "evidence_item_ids": evidence_item_ids,
                    },
                }
            )
        )

    return {
        "schema_version": DELTA_SCHEMA_VERSION,
        "source_trace_path": trace_path,
        "min_support": min_support,
        "max_evidence_items": max_evidence_items,
        "delta_count": len(deltas),
        "deltas": [delta.to_dict() for delta in deltas],
    }


def load_trace_report(path: str | Path) -> dict[str, Any]:
    trace_path = Path(path)
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ACE trace report must be a JSON object.")
    return payload


def save_delta_report(delta_report: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(delta_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
