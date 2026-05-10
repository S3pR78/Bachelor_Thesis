from __future__ import annotations

from ace.orkg.memory_context import memory_domain_context


def normalize_scope(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def domain_prompt_context(family: str, prediction_format: str, question: str) -> str:
    """Return compact family/format/question-specific ORKG context.

    PGMR-lite receives placeholder/memory context.
    Direct SPARQL receives canonical ORKG URI context.
    """
    return memory_domain_context(family, prediction_format, question)


def reflection_instruction(prediction_format: str) -> str:
    normalized_format = normalize_scope(prediction_format)

    if normalized_format == "pgmr_lite":
        return (
            "For PGMR-lite, the reusable insight should mention relevant allowed "
            "family placeholders or placeholder chains when the issue involves "
            "structure, projection, filters, joins, or missing mappings. Avoid generic "
            "advice such as 'include intermediate nodes', 'add filters', or 'use optional "
            "clauses' unless the insight states the concrete PGMR-lite path or answer-variable role. "
            "Never mention real ORKG IDs in final PGMR-lite rules."
        )

    if normalized_format in {"sparql", "direct_sparql"}:
        return (
            "For Direct SPARQL, reusable insights may mention short family-valid ORKG "
            "triple fragments, predicates, classes, resources, projection variables, "
            "and join paths. Do not use PGMR-lite placeholders in final SPARQL rules. "
            "Do not copy full gold/reference queries."
        )

    return "Create only conservative reusable Text-to-SPARQL insights for this prediction format."
