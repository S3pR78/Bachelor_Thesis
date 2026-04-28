from __future__ import annotations

from typing import Any

from src.core.model_loader import load_model_and_tokenizer, generate_raw_response
from src.core.openai_provider import (
    create_openai_client,
)
from src.utils.config_loader import load_json_config, get_model_entry

CONFIG_PATH = "code/config/model_config.json"


def prepare_inference_session(model_name: str) -> dict:
    full_model_config = load_json_config(CONFIG_PATH)
    model_config = get_model_entry(full_model_config, model_name)
    provider = model_config.get("provider", "").strip().lower()

    if provider == "openai":
        env_var_name = model_config.get("api", {}).get(
            "env_var_name",
            "OPENAI_API_KEY",
        )
        client = create_openai_client(env_var_name=env_var_name)
        return {
            "provider": "openai",
            "model_name": model_name,
            "model_config": model_config,
            "client": client,
            "env_var_name": env_var_name,
        }

    tokenizer, model = load_model_and_tokenizer(model_config)
    return {
        "provider": provider,
        "model_name": model_name,
        "model_config": model_config,
        "tokenizer": tokenizer,
        "model": model,
    }


def _extract_openai_usage(completion: Any) -> dict[str, Any] | None:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return None

    if hasattr(usage, "model_dump"):
        return usage.model_dump()

    if isinstance(usage, dict):
        return usage

    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
        "completion_tokens": getattr(usage, "completion_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
    }


def generate_response_with_session(session: dict, final_prompt: str) -> dict[str, Any]:
    provider = session["provider"]
    model_config = session["model_config"]

    if provider == "openai":
        client = session["client"]

        completion = client.chat.completions.create(
            model=model_config.get("model_id"),
            messages=[
                {
                    "role": "developer",
                    "content": (
                        "You are an expert ORKG SPARQL query generator. "
                        "Generate precise, syntactically correct, and executable SPARQL queries "
                        "for research questions. "
                        "Return the query only unless asked otherwise."
                    ),
                },
                {"role": "user", "content": final_prompt},
            ],
            max_completion_tokens=model_config.get("generation", {}).get(
                "max_output_tokens",
                model_config.get("generation", {}).get("max_new_tokens", 512),
            ),
            temperature=model_config.get("generation", {}).get("temperature", 0.0),
        )

        message = completion.choices[0].message.content
        if not message or not message.strip():
            raise ValueError("Received empty response from OpenAI API.")

        return {
            "text": message.strip(),
            "usage": _extract_openai_usage(completion),
        }

    text = generate_raw_response(
        model=session["model"],
        tokenizer=session["tokenizer"],
        prompt=final_prompt,
        max_new_tokens=model_config.get("generation", {}).get(
            "max_new_tokens",
            128,
        ),
        do_sample=model_config.get("generation", {}).get("do_sample", False),
        temperature=model_config.get("generation", {}).get("temperature", 0.0),
    )

    return {
        "text": text,
        "usage": None,
    }