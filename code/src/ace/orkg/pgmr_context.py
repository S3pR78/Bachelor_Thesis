from __future__ import annotations

from pathlib import Path


PGMR_PROMPT_PATHS = {
    "empirical_research_practice": Path("code/prompts/pgmr/empirical_research_prompt.txt"),
    "nlp4re": Path("code/prompts/pgmr/nlp4re_prompt.txt"),
}


def extract_allowed_placeholders(prompt_text: str) -> list[str]:
    """Extract allowed PGMR-lite placeholders from a family PGMR prompt."""
    placeholders: list[str] = []
    in_block = False

    for line in prompt_text.splitlines():
        stripped = line.strip()

        if stripped.lower().startswith("allowed core pgmr-lite placeholders"):
            in_block = True
            continue

        if not in_block:
            continue

        if stripped.startswith(("family:", "question:", "query:")):
            break

        if stripped.startswith(("pgmr:", "pgmrc:")):
            placeholders.append(stripped)

    return placeholders


def allowed_pgmr_placeholders_for_family(family: str) -> set[str]:
    """Return all allowed PGMR-lite placeholders/classes for a family."""
    path = PGMR_PROMPT_PATHS.get(family)
    if not path or not path.exists():
        return set()

    prompt_text = path.read_text(encoding="utf-8")
    return set(extract_allowed_placeholders(prompt_text))


def relevant_pgmr_placeholders(
    family: str,
    question: str,
    *,
    max_items: int = 35,
) -> list[str]:
    """Select a compact family/question-specific subset of allowed placeholders.

    This is used as ACE prompt context. It does not validate queries; it gives
    Reflector/Curator enough domain memory to write concrete PGMR-lite rules
    without inventing placeholders outside the family prompt/memory.
    """
    path = PGMR_PROMPT_PATHS.get(family)
    if not path or not path.exists():
        return []

    prompt_text = path.read_text(encoding="utf-8")
    all_placeholders = extract_allowed_placeholders(prompt_text)

    question_l = question.lower()
    selected: list[str] = []

    core_placeholders = {
        "pgmr:has_contribution",
        "pgmrc:empirical_research_practice_contribution",
        "pgmrc:nlp4re_contribution",
    }
    for placeholder in all_placeholders:
        if placeholder in core_placeholders:
            selected.append(placeholder)

    keyword_map = {
        # empirical_research_practice
        "threat": [
            "threat",
            "validity",
            "external",
            "internal",
            "construct",
            "conclusion",
            "reliability",
            "generalizability",
            "repeatability",
            "content_validity",
            "descriptive_validity",
            "theoretical_validity",
        ],
        "validity": [
            "threat",
            "validity",
            "external",
            "internal",
            "construct",
            "conclusion",
            "reliability",
            "generalizability",
            "repeatability",
        ],
        "year": ["publication_year"],
        "time": ["publication_year"],
        "over time": ["publication_year"],
        "venue": ["venue_serie"],
        "research question": [
            "research_question",
            "question",
            "question_type",
            "research_question_answer",
        ],
        "answer": [
            "research_question_answer",
            "hidden_in_text",
            "highlighted_in_text",
        ],
        "data collection": [
            "data_collection",
            "data",
            "data_type",
            "method",
            "method_type",
            "method_name",
        ],
        "data analysis": [
            "data_analysis",
            "inferential_statistics",
            "descriptive_statistics",
            "machine_learning",
        ],
        "method": ["method", "method_type", "method_name"],
        "statistic": [
            "statistics",
            "statistical",
            "descriptive",
            "inferential",
            "count",
            "percent",
            "mean",
            "median",
            "standard_deviation",
        ],
        "hypothesis": ["hypothesis", "hypothesis_statement", "hypothesis_type"],
        "machine learning": ["machine_learning", "algorithm", "metric"],

        # shared-ish / metrics
        "metric": [
            "metric",
            "evaluation_metric",
            "accuracy",
            "precision",
            "recall",
            "f_score",
        ],
        "accuracy": ["accuracy", "metric"],
        "precision": ["precision", "metric"],
        "recall": ["recall", "metric"],

        # nlp4re
        "re task": ["re_task"],
        "requirements engineering": ["re_task"],
        "nlp task": [
            "nlp_task",
            "nlp_task_type",
            "nlp_task_input",
            "nlp_task_output",
        ],
        "task": [
            "re_task",
            "nlp_task",
            "nlp_task_type",
            "nlp_task_input",
            "nlp_task_output",
        ],
        "dataset": [
            "nlp_dataset",
            "nlp_data",
            "data_source",
            "data_type",
            "dataset_location",
        ],
        "data source": [
            "nlp_data_source",
            "nlp_data_source_type",
            "number_of_data_sources",
        ],
        "annotation": ["annotation", "annotator", "agreement", "guideline"],
        "guideline": ["guideline", "annotation_scheme"],
        "agreement": [
            "annotator_agreement",
            "intercoder_reliability_metric",
            "measured_agreement",
        ],
        "approach": ["implemented_approach", "approach_type", "algorithm_used"],
        "tool": ["implemented_approach", "release", "documentation"],
        "algorithm": ["algorithm", "algorithm_used"],
        "evaluation": [
            "evaluation",
            "evaluation_metric",
            "validation_procedure",
            "baseline_comparison",
        ],
        "validation": ["validation_procedure"],
        "baseline": [
            "baseline_comparison",
            "baseline_comparison_type",
            "baseline_comparison_detail",
        ],
        "license": ["license", "license_type"],
        "release": ["release", "release_format", "release_location_type"],
        "url": ["url"],
    }

    wanted_tokens: set[str] = set()
    for keyword, tokens in keyword_map.items():
        if keyword in question_l:
            wanted_tokens.update(tokens)

    for placeholder in all_placeholders:
        placeholder_l = placeholder.lower()
        if any(token in placeholder_l for token in wanted_tokens):
            selected.append(placeholder)

    deduped: list[str] = []
    seen: set[str] = set()
    for placeholder in selected:
        if placeholder not in seen:
            seen.add(placeholder)
            deduped.append(placeholder)

    return deduped[:max_items]


def pgmr_prompt_context(family: str, question: str) -> str:
    placeholders = relevant_pgmr_placeholders(family, question)
    if not placeholders:
        return "No PGMR-lite placeholder context loaded."

    return (
        "Relevant allowed PGMR-lite placeholders for this family/question:\n"
        + "\n".join(f"- {placeholder}" for placeholder in placeholders)
        + "\nUse only these or other placeholders from the same family prompt/memory mapping. "
        "Do not invent new pgmr:/pgmrc: names."
    )
