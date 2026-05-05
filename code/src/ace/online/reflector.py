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


DEVELOPER_MESSAGE = (
    "You are an ACE Reflector for ORKG Text-to-SPARQL. "
    "Return exactly one concise context rule as valid JSON only."
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
    }


def build_online_reflection_prompt(payload: OnlineAceReflectionInput) -> str:
    """Build the compact prompt for one failed online ACE attempt."""
    item = payload.item
    generation = payload.generation
    evaluation = payload.evaluation

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
        ],
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
            "predicted_or_restored_sparql": _shorten(
                generation.get("pgmr_restored_query")
                or generation.get("selected_prediction_query")
                or generation.get("extracted_query")
                or generation.get("raw_model_output")
            ),
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
            "category": "short_category",
            "title": "Short imperative title",
            "content": "One concise rule to add to the prompt context.",
            "positive_pattern": "Helpful SPARQL/PGMR pattern or null",
            "avoid": "Short anti-pattern or null",
            "priority": 80,
            "enabled": True,
            "source_item_id": str(item.get("id")),
            "source_iteration": payload.iteration,
            "created_at_utc": "filled_by_caller_if_empty",
        },
    }

    return json.dumps(compact_payload, indent=2, ensure_ascii=False)


def normalize_online_rule(
    rule_payload: dict[str, Any],
    *,
    family: str,
    mode: str,
    source_item_id: str,
    source_iteration: int,
) -> dict[str, Any]:
    """Normalize and validate one online reflector rule."""
    normalized = {
        **rule_payload,
        "family": str(rule_payload.get("family") or family),
        "mode": str(rule_payload.get("mode") or mode),
        "category": str(rule_payload.get("category") or "answer_mismatch"),
        "title": str(rule_payload.get("title") or "").strip(),
        "content": str(rule_payload.get("content") or "").strip(),
        "priority": int(rule_payload.get("priority", 80)),
        "enabled": bool(rule_payload.get("enabled", True)),
        "source_item_id": str(rule_payload.get("source_item_id") or source_item_id),
        "source_iteration": int(
            rule_payload.get("source_iteration", source_iteration)
        ),
        "created_at_utc": str(rule_payload.get("created_at_utc") or utc_now_iso()),
    }

    source = dict(normalized.get("source", {}))
    source.update(
        {
            "type": "online_llm_reflector",
            "source_item_id": normalized["source_item_id"],
            "source_iteration": normalized["source_iteration"],
        }
    )
    normalized["source"] = source

    # Validate required fields and create a stable ID if the model leaves it empty.
    return AceBullet.from_dict(normalized).to_dict()


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
                str(api.get("api_key_env") or api.get("env_var_name") or "OPENAI_API_KEY"),
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
        response = self.completion_fn(
            model_id=model_id,
            prompt=prompt,
            max_output_tokens=self.config.max_output_tokens,
            temperature=self.config.temperature,
            developer_message=DEVELOPER_MESSAGE,
            env_var_name=env_var_name,
        )

        raw_text = str(response.get("text") or "").strip()
        if not raw_text:
            raise ValueError("Online ACE reflector returned an empty response.")

        parsed = extract_json_object(raw_text)
        rule = normalize_online_rule(
            parsed,
            family=str(payload.item.get("family") or payload.config.family or "global"),
            mode=payload.config.prediction_format,
            source_item_id=str(payload.item.get("id") or ""),
            source_iteration=payload.iteration,
        )

        return {
            "rule": rule,
            "usage": _usage_to_dict(response.get("usage")),
            "model": self.config.reflector_model,
            "model_id": model_id,
            "raw_response": raw_text,
        }
