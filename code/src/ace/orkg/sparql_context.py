from __future__ import annotations


def sparql_prompt_context(family: str, question: str) -> str:
    """Return compact Direct-SPARQL/Empire-Compass guidance for ACE.

    This is used only when prediction_format is SPARQL/direct_sparql. Unlike
    PGMR-lite, Direct SPARQL rules may mention ORKG predicates/classes/resources
    and short family-valid triple fragments. Full copied queries are still not
    allowed in playbook rules.
    """
    question_l = question.lower()

    if family == "empirical_research_practice":
        hints = [
            "Direct SPARQL context for empirical_research_practice.",
            "Rules may mention short ORKG triple fragments when reusable and family-valid.",
            "Required contribution pattern: ?paper orkgp:P31 ?contribution . ?contribution a orkgc:C27001 .",
            "Use ?paper and ?paperLabel when the question asks for papers/studies.",
            "Contribution-level properties should be reached through ?contribution, not attached directly to ?paper unless the template supports it.",
        ]

        if "venue" in question_l:
            hints.append("Venue constraints should be reached through the contribution-level venue relation and compared via venue labels when needed.")
        if "research question" in question_l or "answer" in question_l:
            hints.append("Keep research-question nodes and research-question-answer/highlight nodes separate; project the requested entity.")
        if "data collection" in question_l or "method" in question_l:
            hints.append("Data collection method questions should use the contribution -> data collection -> method path.")
        if "data analysis" in question_l or "statistic" in question_l:
            hints.append("Data-analysis/statistics questions should use the contribution -> data analysis -> nested statistics/method path.")
        if "threat" in question_l or "validity" in question_l:
            hints.append("Threats-to-validity questions should use the contribution -> threats-to-validity structure and project/filter the requested threat type.")
        if "year" in question_l or "time" in question_l or "over time" in question_l:
            hints.append("Publication year should be bound from the paper-level publication year relation.")

        return "\n".join(f"- {hint}" for hint in hints)

    if family == "nlp4re":
        hints = [
            "Direct SPARQL context for nlp4re.",
            "Rules may mention short ORKG triple fragments when reusable and family-valid.",
            "Use the nlp4re contribution/template structure to reach requested entities from the contribution node.",
            "Use ?paper and ?paperLabel when the question asks for papers/studies.",
            "When the question asks for tasks, datasets, approaches, evaluations, or metrics, project the requested entity and label, not only paper/contribution.",
        ]

        if "re task" in question_l or "requirements engineering" in question_l:
            hints.append("RE task questions should bind and project the RE task entity when it is the requested answer.")
        if "nlp task" in question_l or "task" in question_l:
            hints.append("NLP task questions should keep NLP task, type, input, and output roles distinct.")
        if "dataset" in question_l or "data source" in question_l:
            hints.append("Dataset questions should use the contribution -> NLP dataset -> nested dataset field path.")
        if "annotation" in question_l or "guideline" in question_l or "agreement" in question_l:
            hints.append("Annotation questions should use the contribution -> annotation process -> nested annotation field path.")
        if "approach" in question_l or "tool" in question_l or "algorithm" in question_l:
            hints.append("Approach/tool questions should use the contribution -> implemented approach -> nested approach/release/algorithm path.")
        if "evaluation" in question_l or "metric" in question_l or "baseline" in question_l:
            hints.append("Evaluation questions should use the contribution -> evaluation -> metric/validation/baseline path.")
        if "year" in question_l or "time" in question_l:
            hints.append("Publication/data time questions should distinguish paper publication year from dataset production time.")

        return "\n".join(f"- {hint}" for hint in hints)

    return (
        "- No family-specific Direct-SPARQL context loaded.\n"
        "- Keep rules scoped to the current family and avoid copying full queries."
    )
