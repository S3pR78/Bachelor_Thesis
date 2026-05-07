"""LLM reflector for true online ACE."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Callable

from src.ace.online.loop import OnlineAceReflectionInput
from src.ace.playbook import AceBullet, utc_now_iso
from src.utils.config_loader import get_model_entry, load_json_config


CompletionFn = Callable[..., dict[str, Any]]

ALLOWED_REFLECTION_CATEGORIES = {
    "missing_pattern",
    "wrong_placeholder",
    "unmapped_placeholder",
    "wrong_projection",
    "missing_constraint",
    "aggregation_error",
    "output_format",
    "wrong_template_family",
}

CONCRETE_MARKERS = (
    "pgmr:",
    "pgmrc:",
    "orkgp:",
    "orkgc:",
    "orkgr:",
    "SELECT",
    "WHERE",
    "COUNT",
    "GROUP BY",
    "HAVING",
    "?",
)

VAGUE_WORDS = (
    "clarify",
    "ensure",
    "specify",
    "improve",
    "handle",
    "consider",
    "define",
    "avoid ambiguity",
)

DEFAULT_PGMR_MEMORY_DIR = Path("code/data/orkg_memory/templates")

DEVELOPER_MESSAGE = (
    "You are an ACE Reflector for ORKG Text-to-SPARQL. "
    "Return exactly one valid JSON object for one prompt-context rule. "
    "The rule must be directly usable by a model generating SPARQL/PGMR. "
    "Do not give generic advice. "
    "Every rule must include a concrete placeholder, triple pattern, wrong-pattern avoidance, "
    "or aggregation instruction. "
    "At least one of positive_pattern or avoid must be non-null and concrete. "
    "If you cannot infer a safe concrete rule, return a rule that says to use only known canonical placeholders "
    "and name the suspicious placeholder/pattern."
)


@dataclass(frozen=True)
class OnlineReflectorConfig:
    """Configuration for the online ACE reflector."""

    reflector_model: str = "gpt_4o_mini"
    model_config_path: Path = Path("code/config/model_config.json")
    max_output_tokens: int = 1024
    temperature: float = 0.0


def _shorten(value: Any, *, max_chars: int = 1400) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + " ..."


def _memory_file_for_family(memory_dir: Path, family: str) -> Path | None:
    """Return the PGMR memory file for a supported template family."""
    normalized = str(family or "").strip().lower()
    candidates = {
        "nlp4re": memory_dir / "nlp4re_memory.json",
        "empirical_research_practice": memory_dir
        / "empirical_research_practice_memory.json",
    }
    return candidates.get(normalized)


def _memory_entries(payload: Any) -> list[dict[str, Any]]:
    """Load memory entries for the current family if available."""
    family = str(
        payload.item.get("family")
        or getattr(payload.config, "family", "")
        or ""
    )
    memory_dir_value = (
        getattr(payload.config, "pgmr_memory_dir", None)
        or getattr(payload.config, "pgmr_memory_dir_path", None)
        or DEFAULT_PGMR_MEMORY_DIR
    )
    memory_dir = Path(memory_dir_value)
    memory_file = _memory_file_for_family(memory_dir, family)
    if memory_file is None or not memory_file.exists():
        return []

    data = json.loads(memory_file.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    if isinstance(data, dict):
        for key in ("entries", "memory", "items", "placeholders"):
            value = data.get(key)
            if isinstance(value, list):
                return [entry for entry in value if isinstance(entry, dict)]
    return []


def build_allowed_pgmr_placeholder_context(payload: Any) -> dict[str, Any] | None:
    """Build compact family-specific allowed placeholder context for PGMR-lite."""
    if getattr(payload.config, "prediction_format", "") != "pgmr_lite":
        return None

    family = str(
        payload.item.get("family")
        or getattr(payload.config, "family", "")
        or ""
    )
    entries = _memory_entries(payload)

    relations: set[str] = set()
    classes: set[str] = set()
    aliases: dict[str, str] = {}

    for entry in entries:
        placeholder = str(entry.get("placeholder") or "").strip()
        if not placeholder:
            continue

        if placeholder.startswith("pgmrc:"):
            classes.add(placeholder)
        elif placeholder.startswith("pgmr:"):
            relations.add(placeholder)

        for alias in entry.get("aliases") or []:
            alias_text = str(alias).strip()
            if alias_text.startswith(("pgmr:", "pgmrc:")):
                aliases[alias_text] = placeholder

    return {
        "family": family,
        "relations": sorted(relations),
        "classes": sorted(classes),
        "aliases": dict(sorted(aliases.items())),
    }


def extract_pgmr_tokens_from_rule(rule_payload: dict[str, Any]) -> set[str]:
    """Extract pgmr:/pgmrc: tokens from reflected rule fields."""
    text = " ".join(
        str(rule_payload.get(key) or "")
        for key in ("title", "content", "positive_pattern", "avoid")
    )
    return set(re.findall(r"\bpgmrc?:[A-Za-z0-9_]+\b", text))


def invalid_pgmr_tokens_for_rule(
    rule_payload: dict[str, Any],
    allowed_context: dict[str, Any] | None,
) -> list[str]:
    """Return PGMR tokens that are not allowed for the current family."""
    if not allowed_context:
        return []

    allowed = set(allowed_context.get("relations") or [])
    allowed.update(allowed_context.get("classes") or [])
    allowed.update((allowed_context.get("aliases") or {}).keys())

    tokens = extract_pgmr_tokens_from_rule(rule_payload)
    return sorted(token for token in tokens if token not in allowed)


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from an LLM response without importing OpenAI code."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"```$", "", cleaned.strip())

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(cleaned[start : end + 1])

    if not isinstance(payload, dict):
        raise ValueError("Online reflector response must be a JSON object.")

    return payload


def _compact_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rule.get("id"),
        "title": _shorten(rule.get("title"), max_chars=160),
        "content": _shorten(rule.get("content"), max_chars=300),
        "category": rule.get("category"),
        "priority": rule.get("priority"),
        "enabled": rule.get("enabled", True),
        "positive_pattern": _shorten(rule.get("positive_pattern"), max_chars=240),
        "avoid": _shorten(rule.get("avoid"), max_chars=240),
    }


def build_online_reflection_prompt(payload: OnlineAceReflectionInput) -> str:
    """Build the compact prompt for one failed online ACE attempt."""
    item = payload.item
    generation = payload.generation
    evaluation = payload.evaluation
    allowed_pgmr_placeholders = build_allowed_pgmr_placeholder_context(payload)

    compact_payload = {
        "task": (
            "Identify the most likely reason for this failed Text-to-SPARQL "
            "attempt and propose exactly one small actionable context rule."
        ),
        "constraints": [
            "Return valid JSON only.",
            "Return exactly one rule object, not a list.",
            "Keep the rule short, template-specific, and actionable.",
            "Do not include full execution result tables.",
            "Do not invent ORKG predicates, classes, or PGMR placeholders.",
            "The rule must be usable as prompt context for future generations.",
            "The rule MUST include at least one concrete element:",
            "- a pgmr:/pgmrc: placeholder or triple pattern",
            "- or a concrete SPARQL triple pattern",
            "- or a concrete avoid instruction naming a wrong placeholder/pattern",
            "- or a concrete aggregation instruction (COUNT/GROUP BY/HAVING).",
            "Before writing the rule, identify the reusable error pattern, but do not output long chain-of-thought.",
            "Return a short diagnosis object with evidence from gold and prediction.",
            "The diagnosis must be concise and factual, not a hidden reasoning trace.",
            "Focus on reusable error patterns, not only the current item.",
            "At least one of positive_pattern or avoid must be non-null and concrete.",
            "Do not write vague advice using only words like clarify, ensure, specify, define, improve, handle, or consider.",
            "If the error is an unmapped PGMR placeholder, create an avoid rule naming that placeholder and suggest the closest canonical placeholder only if it is visible from gold, prediction, context, or allowed_pgmr_placeholders.",
            "If the question asks 'how many', 'how often', 'most frequent', 'at least', 'per', or 'proportion', the rule should mention COUNT/GROUP BY/HAVING when relevant.",
            "If the prediction selected the wrong columns, the rule should name the expected SELECT variables or answer entity.",
            "If the prediction used the wrong template family, the rule should name the correct contribution/class pattern.",
            "Choose exactly one category from:",
            "- missing_pattern",
            "- wrong_placeholder",
            "- unmapped_placeholder",
            "- wrong_projection",
            "- missing_constraint",
            "- aggregation_error",
            "- output_format",
            "- wrong_template_family",
            "Rules should generalize to a reusable question pattern, not only fix the current item.",
            "Do not mention the current item id in the rule content or title.",
            "Do not create rules that only rename one variable for one question unless the variable choice reflects a reusable answer pattern.",
            "Prefer rules phrased as: 'For questions asking about X, use pattern Y and avoid Z.'",
            "The rule should be specific enough to contain concrete placeholders or patterns, but general enough to apply to future similar questions.",
            "Do not overfit to the exact wording of the current question.",
            "Positive patterns should include the minimal graph path from ?contribution to the requested answer variable whenever possible.",
            "Do not output only an isolated rdfs:label triple unless the path to that variable is already explicit in the rule content.",
            "Prefer complete minimal PGMR/SPARQL paths over single final label triples.",
            "For contribution patterns, always use ?paper pgmr:has_contribution ?contribution .",
            "Never use ?contribution pgmr:has_contribution ?contribution .",
            "Do not create generic fallback rules such as 'Use concrete query pattern' or '?s ?p ?o'.",
            "If no safe concrete family-specific rule can be inferred, return a rule that avoids the observed wrong placeholder/pattern using only placeholders from allowed_pgmr_placeholders.",
            "For contribution patterns, always use ?paper pgmr:has_contribution ?contribution .",
            "Never use ?contribution pgmr:has_contribution ?x .",
            "Never use ?contribution pgmr:has_contribution ?contribution .",
            "Do not use pgmr:has_contribution to connect contribution to datasets, approaches, or evaluations. Use the specific relation such as pgmr:nlp_dataset, pgmr:implemented_approach, or pgmr:evaluation.",
            "In PGMR-lite mode, use only placeholders from allowed_pgmr_placeholders.",
            "Prefer canonical placeholders exactly as listed in allowed_pgmr_placeholders.",
            "Do not invent pgmr:/pgmrc: placeholders.",
            "Never suggest placeholders that are not listed in allowed_pgmr_placeholders.",
            "If a predicted placeholder is not listed, create an avoid rule naming it and replace it only with a listed placeholder.",
            "Do not treat variables starting with ? as PGMR placeholders. Variables such as ?evaluation, ?scheme, or ?releaseFormat are not placeholders.",
            "A PGMR placeholder starts with pgmr: or pgmrc:.",
            "If the issue is a wrong variable selected in SELECT, use category wrong_projection.",
            "If the issue is a wrong predicate placeholder, use category wrong_placeholder and name the wrong pgmr:/pgmrc: placeholder or wrong triple pattern.",
            "For wrong_placeholder rules, avoid must not be only a variable name like ?evaluation. It must include a wrong pgmr:/pgmrc: placeholder or a wrong triple pattern.",
            "Bad rule examples:",
            "- 'Clarify baseline comparison requirements.'",
            "- 'Ensure document types are clearly defined.'",
            "- 'Specify extraction conditions.'",
            "- 'Define the relationship more explicitly.'",
            "Bad overly specific rule example:",
            "- 'For this question, use SELECT DISTINCT ?baseline_type ?baseline_typeLabel.'",
            "Bad wrong_placeholder example:",
            "- 'Avoid ?releaseFormat.'",
            "Bad positive_pattern example:",
            "- '?baseline_type rdfs:label ?baseline_typeLabel .'",
            "Good rule examples:",
            "- 'For NLP4RE dataset questions, include ?contribution pgmr:nlp_dataset ?dataset and do not answer only with evaluation properties.'",
            "- 'Use pgmr:nlp_data_type for NLP data type questions. Do not invent pgmr:nlp_data_type_type.'",
            "- 'For questions asking how many or how often, use COUNT and GROUP BY over the requested entity.'",
            "- 'In PGMR-lite mode, return only pgmr:/pgmrc: placeholders and never real orkgp:/orkgc: IDs.'",
            "- 'For NLP4RE evaluation metric questions, include ?contribution pgmr:evaluation ?evaluation . ?evaluation pgmr:evaluation_metric ?metric .'",
            "- 'For NLP4RE questions asking for baseline types or baseline comparisons, use the evaluation-to-baseline-type pattern and project ?baseline_type and optionally ?baseline_typeLabel.'",
            "Good wrong_placeholder example:",
            "- 'Avoid pgmr:format for release formats; use ?release pgmr:release_format ?releaseFormat .'",
            "Good positive_pattern example:",
            "- '?contribution pgmr:evaluation ?evaluation . ?evaluation pgmr:baseline_comparison ?baseline . ?baseline pgmr:baseline_comparison_type ?baseline_type . OPTIONAL { ?baseline_type rdfs:label ?baseline_typeLabel . }'",
        ],
        "mode_specific_requirements": {
            "pgmr_lite": [
                "Use pgmr:/pgmrc: placeholders, not real orkgp:/orkgc: IDs.",
                "Use only placeholders listed in allowed_pgmr_placeholders.",
                "Prefer canonical placeholders exactly as listed in allowed_pgmr_placeholders.",
                "Do not invent new placeholders.",
                "If a placeholder looks unmapped, create an avoid rule naming it.",
            ]
            if payload.config.prediction_format == "pgmr_lite"
            else [],
            "direct_sparql": [
                "Use concrete ORKG predicates/classes/resources.",
                "Do not use pgmr:/pgmrc: placeholders in direct SPARQL mode.",
            ]
            if payload.config.prediction_format == "sparql"
            else [],
        },
        "allowed_pgmr_placeholders": allowed_pgmr_placeholders,
        "run_context": {
            "generator_model": payload.config.model,
            "reflector_model": payload.config.reflect_model,
            "prompt_mode": payload.config.prompt_mode,
            "prediction_format": payload.config.prediction_format,
            "family": item.get("family") or payload.config.family,
            "iteration": payload.iteration,
        },
        "failed_item": {
            "item_id": item.get("id"),
            "question": _shorten(item.get("question")),
            "family": item.get("family"),
            "gold_sparql": _shorten(item.get("gold_sparql")),
            "gold_pgmr_sparql": _shorten(item.get("gold_pgmr_sparql")),
            "predicted_or_restored_sparql": _shorten(
                generation.get("pgmr_restored_query")
                or generation.get("selected_prediction_query")
                or generation.get("extracted_query")
                or generation.get("extracted_pgmr_query")
                or generation.get("raw_model_output")
            ),
            "raw_model_output": _shorten(
                generation.get("raw_model_output"), max_chars=900
            ),
            "pgmr_unmapped_placeholders": generation.get("pgmr_unmapped_placeholders")
            or evaluation.get("pgmr_unmapped_placeholders"),
        },
        "metrics_and_errors": {
            "query_extracted": evaluation.get("query_extracted"),
            "prediction_execution_success": evaluation.get(
                "prediction_execution_success"
            ),
            "gold_execution_success": evaluation.get("gold_execution_success"),
            "answer_exact_match": evaluation.get("answer_exact_match"),
            "answer_f1": evaluation.get("answer_f1"),
            "kg_ref_f1": evaluation.get("kg_ref_f1"),
            "predicate_ref_f1": evaluation.get("predicate_ref_f1"),
            "error_category": evaluation.get("error_category"),
            "error_text": _shorten(evaluation.get("error_text"), max_chars=500),
        },
        "current_context_rules": [
            _compact_rule(rule)
            for rule in payload.context_rules
            if isinstance(rule, dict)
        ],
        "output_schema": {
            "id": "short_stable_id_or_empty",
            "family": item.get("family") or payload.config.family,
            "mode": payload.config.prediction_format,
            "category": (
                "one of: missing_pattern, wrong_placeholder, unmapped_placeholder, "
                "wrong_projection, missing_constraint, aggregation_error, "
                "output_format, wrong_template_family"
            ),
            "title": "Short imperative title",
            "content": (
                "One concise, concrete, reusable rule to add to the prompt context. "
                "It must mention a placeholder, pattern, wrong pattern, expected SELECT entity, "
                "or aggregation instruction."
            ),
            "positive_pattern": (
                "A concrete PGMR/SPARQL pattern. Prefer the minimal path from ?contribution "
                "to the requested answer variable, not only an isolated rdfs:label triple. "
                "May be null only if avoid is concrete."
            ),
            "avoid": (
                "A concrete wrong placeholder/pattern to avoid. "
                "May be null only if positive_pattern is concrete."
            ),
            "diagnosis": {
                "error_type": "one of the allowed categories",
                "evidence_from_gold": "Short factual evidence from the gold query.",
                "evidence_from_prediction": "Short factual evidence from the prediction.",
                "generalizable_pattern": "The reusable question/query pattern this rule should cover.",
            },
            "priority": 80,
            "enabled": True,
            "source_item_id": str(item.get("id")),
            "source_iteration": payload.iteration,
            "created_at_utc": "filled_by_caller_if_empty",
        },
    }

    return json.dumps(compact_payload, indent=2, ensure_ascii=False)


def normalize_category(value: Any) -> str:
    """Normalize reflector category to one of the allowed online ACE categories."""
    category = str(value or "").strip().lower()
    category = re.sub(r"[\s-]+", "_", category)
    if category in ALLOWED_REFLECTION_CATEGORIES:
        return category
    return "missing_pattern"


def normalize_online_rule(
    rule_payload: dict[str, Any],
    *,
    family: str,
    mode: str,
    source_item_id: str,
    source_iteration: int,
) -> dict[str, Any]:
    """Normalize and validate one online reflector rule."""
    raw_title = str(rule_payload.get("title") or "").strip()
    raw_content = str(rule_payload.get("content") or "").strip()
    raw_positive_pattern = rule_payload.get("positive_pattern")
    raw_avoid = rule_payload.get("avoid")

    fallback_text = (
        str(raw_positive_pattern or "").strip()
        or str(raw_avoid or "").strip()
        or "Use the detected pattern for this template and avoid the failing variant."
    )
    title = raw_title or "Use concrete query pattern"
    content = raw_content or fallback_text

    normalized = {
        **rule_payload,
        "family": str(rule_payload.get("family") or family),
        "mode": str(rule_payload.get("mode") or mode),
        "category": normalize_category(rule_payload.get("category")),
        "title": title,
        "content": content,
        "positive_pattern": raw_positive_pattern,
        "avoid": raw_avoid,
        "priority": int(rule_payload.get("priority", 80)),
        "enabled": bool(rule_payload.get("enabled", True)),
        "source_item_id": str(rule_payload.get("source_item_id") or source_item_id),
        "source_iteration": int(
            rule_payload.get("source_iteration", source_iteration)
        ),
        "created_at_utc": str(rule_payload.get("created_at_utc") or utc_now_iso()),
    }

    if normalized["positive_pattern"] is not None:
        normalized["positive_pattern"] = (
            str(normalized["positive_pattern"]).strip() or None
        )
    if normalized["avoid"] is not None:
        normalized["avoid"] = str(normalized["avoid"]).strip() or None

    source = dict(normalized.get("source", {}))
    source.update(
        {
            "type": "online_llm_reflector",
            "source_item_id": normalized["source_item_id"],
            "source_iteration": normalized["source_iteration"],
        }
    )

    diagnosis = normalized.get("diagnosis")
    if isinstance(diagnosis, dict):
        source["diagnosis"] = {
            "error_type": str(diagnosis.get("error_type") or ""),
            "evidence_from_gold": str(diagnosis.get("evidence_from_gold") or ""),
            "evidence_from_prediction": str(
                diagnosis.get("evidence_from_prediction") or ""
            ),
            "generalizable_pattern": str(
                diagnosis.get("generalizable_pattern") or ""
            ),
        }
        # Keep diagnosis in source so AceBullet does not need a new top-level field.
        normalized.pop("diagnosis", None)

    normalized["source"] = source

    return AceBullet.from_dict(normalized).to_dict()


def _normalized_rule_text(rule_payload: dict[str, Any]) -> str:
    text = " ".join(
        str(rule_payload.get(key) or "")
        for key in ("title", "content", "positive_pattern", "avoid")
    ).lower()
    return " ".join(text.split())


def _has_triple_pattern(text: str) -> bool:
    # Simple concrete-triple heuristic. It catches patterns such as:
    # ?contribution pgmr:nlp_dataset ?dataset .
    return bool(
        re.search(
            r"\?[a-zA-Z_]\w*\s+[a-zA-Z_][\w:.-]*\s+\?[a-zA-Z_]\w*\s*\.?",
            text,
        )
    )


def _is_variable_only(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(re.fullmatch(r"\?[A-Za-z_]\w*", text))


def _is_bad_variable_only_placeholder_rule(rule_payload: dict[str, Any]) -> bool:
    category = normalize_category(rule_payload.get("category"))
    if category != "wrong_placeholder":
        return False
    return _is_variable_only(rule_payload.get("avoid"))

def _has_bad_contribution_self_loop(rule_payload: dict[str, Any]) -> bool:
    """Reject invalid contribution self-loop patterns."""
    text = _normalized_rule_text(rule_payload)
    return bool(
        re.search(
            r"\?contribution\s+pgmr:has_contribution\s+\?contribution",
            text,
            flags=re.IGNORECASE,
        )
    )


def _is_generic_fallback_rule(rule_payload: dict[str, Any]) -> bool:
    """Reject generic fallback rules that do not encode a reusable template pattern."""
    title = str(rule_payload.get("title") or "").strip().lower()
    content = str(rule_payload.get("content") or "").strip().lower()
    positive = str(rule_payload.get("positive_pattern") or "").strip().lower()

    generic_titles = {
        "use concrete query pattern",
        "use explicit query structure",
        "add concrete query pattern",
    }

    if title in generic_titles:
        return True

    if "?s ?p ?o" in content or "?s ?p ?o" in positive:
        return True

    if "add at least one concrete triple pattern" in content:
        return True

    return False


def is_concrete_online_rule(rule_payload: dict[str, Any]) -> bool:
    """Return true when a reflected rule contains concrete prompt-usable content."""
    if _is_bad_variable_only_placeholder_rule(rule_payload):
        return False

    if _has_bad_contribution_self_loop(rule_payload):
        return False

    if _is_generic_fallback_rule(rule_payload):
        return False

    text = _normalized_rule_text(rule_payload)

    has_pgmr = ("pgmr:" in text) or ("pgmrc:" in text)
    has_orkg = ("orkgp:" in text) or ("orkgc:" in text) or ("orkgr:" in text)
    has_variable = "?" in text
    has_triple = _has_triple_pattern(text)
    has_agg = any(
        token in text for token in ("count(", "count ", "group by", "having")
    )
    has_concrete_avoid = ("do not" in text or "avoid" in text) and (
        has_pgmr or has_orkg or has_triple or has_variable
    )

    has_marker = has_pgmr or has_orkg or has_triple or has_agg or has_concrete_avoid
    vague_hits = [word for word in VAGUE_WORDS if word in text]
    only_vague = bool(vague_hits) and not has_marker

    return has_marker and not only_vague


def _usage_to_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def get(name: str, fallback: str | None = None) -> int:
        value = getattr(usage, name, None)
        if value is None and isinstance(usage, dict):
            value = usage.get(name)
        if value is None and fallback:
            value = getattr(usage, fallback, None)
            if value is None and isinstance(usage, dict):
                value = usage.get(fallback)
        return int(value or 0)

    prompt_tokens = get("prompt_tokens", "input_tokens")
    completion_tokens = get("completion_tokens", "output_tokens")
    total_tokens = get("total_tokens")
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def resolve_openai_model(
    model_selector: str,
    *,
    config_path: Path,
) -> tuple[str, str]:
    """Resolve a model config key to an OpenAI model id and API key variable."""
    if config_path.exists():
        try:
            config = load_json_config(config_path)
            entry = get_model_entry(config, model_selector)
            provider = str(entry.get("provider", "")).lower()
            if provider and provider != "openai":
                raise ValueError(
                    f"Reflector model '{model_selector}' is not an OpenAI model."
                )
            api = entry.get("api", {}) if isinstance(entry.get("api"), dict) else {}
            return (
                str(entry.get("model_id") or model_selector),
                str(
                    api.get("api_key_env")
                    or api.get("env_var_name")
                    or "OPENAI_API_KEY"
                ),
            )
        except KeyError:
            pass

    return model_selector, "OPENAI_API_KEY"


def call_openai_chat_completion(
    *,
    model_id: str,
    prompt: str,
    max_output_tokens: int,
    temperature: float,
    developer_message: str,
    env_var_name: str,
) -> dict[str, Any]:
    """Call OpenAI chat completions and return text plus token usage."""
    from src.core.openai_provider import create_openai_client

    client = create_openai_client(env_var_name=env_var_name)
    request_kwargs: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {"role": "developer", "content": developer_message},
            {"role": "user", "content": prompt},
        ],
        "max_completion_tokens": max_output_tokens,
        "response_format": {"type": "json_object"},
    }

    if float(temperature) != 0.0:
        request_kwargs["temperature"] = temperature

    completion = client.chat.completions.create(**request_kwargs)
    raw_text = completion.choices[0].message.content
    if not raw_text or not raw_text.strip():
        raise ValueError("Online ACE reflector returned an empty response.")

    return {
        "text": raw_text.strip(),
        "usage": _usage_to_dict(getattr(completion, "usage", None)),
    }


class OnlineAceReflector:
    """OpenAI-backed online ACE reflector."""

    def __init__(
        self,
        config: OnlineReflectorConfig | None = None,
        *,
        completion_fn: CompletionFn | None = None,
    ) -> None:
        self.config = config or OnlineReflectorConfig()
        self.completion_fn = completion_fn or call_openai_chat_completion

    def reflect(self, payload: OnlineAceReflectionInput) -> dict[str, Any]:
        """Return one normalized rule and usage metadata for a failed attempt."""
        prompt = build_online_reflection_prompt(payload)
        model_id, env_var_name = resolve_openai_model(
            self.config.reflector_model,
            config_path=self.config.model_config_path,
        )
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        last_raw_text = ""

        last_parsed: dict[str, Any] | None = None
        rejection_reason = "unknown"

        for attempt in range(2):
            attempt_prompt = prompt
            if attempt == 1:
                attempt_prompt += (
                    "\n\nRegenerate once: the previous rule was rejected. "
                    "Return one concrete and reusable rule with explicit allowed pgmr:/pgmrc: placeholders, "
                    "a complete minimal triple pattern, a concrete avoid pattern, or COUNT/GROUP BY/HAVING. "
                    "At least one of positive_pattern or avoid must be non-null. "
                    "Use only placeholders listed in allowed_pgmr_placeholders."
                )

            response = self.completion_fn(
                model_id=model_id,
                prompt=attempt_prompt,
                max_output_tokens=self.config.max_output_tokens,
                temperature=self.config.temperature,
                developer_message=DEVELOPER_MESSAGE,
                env_var_name=env_var_name,
            )
            usage = _usage_to_dict(response.get("usage"))
            for key in total_usage:
                total_usage[key] += usage[key]

            raw_text = str(response.get("text") or "").strip()
            if not raw_text:
                raise ValueError("Online ACE reflector returned an empty response.")
            last_raw_text = raw_text

            parsed = extract_json_object(raw_text)
            last_parsed = parsed
            if not is_concrete_online_rule(parsed):
                if attempt == 0:
                    rejection_reason = "missing concrete PGMR/SPARQL details"
                    continue
                rejection_reason = "missing concrete PGMR/SPARQL details"
                continue

            allowed_pgmr_placeholders = build_allowed_pgmr_placeholder_context(payload)
            invalid_tokens = invalid_pgmr_tokens_for_rule(
                parsed, allowed_pgmr_placeholders
            )
            if invalid_tokens:
                if attempt == 0:
                    rejection_reason = (
                        "invalid PGMR placeholders: " + ", ".join(invalid_tokens)
                    )
                    prompt += (
                        "\n\nRegenerate once: the previous rule used invalid PGMR placeholders "
                        f"for this family: {', '.join(invalid_tokens)}. "
                        "Use only placeholders listed in allowed_pgmr_placeholders."
                    )
                    continue
                rejection_reason = (
                    "invalid PGMR placeholders: " + ", ".join(invalid_tokens)
                )
                continue

            rule = normalize_online_rule(
                parsed,
                family=str(
                    payload.item.get("family") or payload.config.family or "global"
                ),
                mode=payload.config.prediction_format,
                source_item_id=str(payload.item.get("id") or ""),
                source_iteration=payload.iteration,
            )
            return {
                "rule": rule,
                "usage": total_usage,
                "model": self.config.reflector_model,
                "model_id": model_id,
                "raw_response": last_raw_text,
            }

        fallback_rule = normalize_online_rule(
            self._build_fallback_rule_payload(
                payload=payload,
                last_parsed=last_parsed,
                rejection_reason=rejection_reason,
            ),
            family=str(payload.item.get("family") or payload.config.family or "global"),
            mode=payload.config.prediction_format,
            source_item_id=str(payload.item.get("id") or ""),
            source_iteration=payload.iteration,
        )
        return {
            "rule": fallback_rule,
            "usage": total_usage,
            "model": self.config.reflector_model,
            "model_id": model_id,
            "raw_response": last_raw_text,
            "fallback_used": True,
            "fallback_reason": rejection_reason,
        }

    @staticmethod
    def _build_fallback_rule_payload(
        *,
        payload: OnlineAceReflectionInput,
        last_parsed: dict[str, Any] | None,
        rejection_reason: str,
    ) -> dict[str, Any]:
        parsed = last_parsed or {}
        category = normalize_category(parsed.get("category"))
        title = str(parsed.get("title") or "").strip() or "Use concrete query pattern"
        content_prefix = str(parsed.get("content") or "").strip()
        concrete_suffix = (
            "Use explicit query structure: add at least one concrete triple pattern "
            "like ?s ?p ?o . or add COUNT(?x) with GROUP BY when the question asks for counts."
        )
        content = f"{content_prefix} {concrete_suffix}".strip()
        avoid = (
            "Do not output vague guidance without placeholders, triple patterns, or COUNT/GROUP BY."
        )
        return {
            "family": str(payload.item.get("family") or payload.config.family or "global"),
            "mode": payload.config.prediction_format,
            "category": category,
            "title": title,
            "content": content,
            "avoid": avoid,
            "priority": int(parsed.get("priority", 80) or 80),
            "enabled": bool(parsed.get("enabled", True)),
            "source": {
                "type": "online_llm_reflector_fallback",
                "fallback_reason": rejection_reason,
            },
        }
