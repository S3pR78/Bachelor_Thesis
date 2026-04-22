from src.core.model_loader import load_model_and_tokenizer, generate_raw_response
from src.core.openai_provider import (
    create_openai_client,
    generate_raw_response_openai,
)
from src.utils.config_loader import load_json_config, get_model_entry


CONFIG_PATH = "code/config/model_config.json"


def prepare_inference_session(model_name: str) -> dict:
    full_model_config = load_json_config(CONFIG_PATH)
    model_config = get_model_entry(full_model_config, model_name)

    provider = model_config.get("provider", "").strip().lower()

    if provider == "openai":
        env_var_name = model_config.get("api", {}).get(
            "env_var_name", "OPENAI_API_KEY"
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


def generate_response_with_session(session: dict, final_prompt: str) -> str:
    provider = session["provider"]
    model_config = session["model_config"]

    if provider == "openai":
        client = session["client"]

        completion = client.chat.completions.create(
            model=model_config.get("model_id"),
            messages=[
                {
                    "role": "developer",
                    "content": "You are an expert ORKG SPARQL query generator. "
                    "Generate precise, syntactically correct, and executable SPARQL queries "
                    "for research questions. Return the query only unless asked otherwise.",
                },
                {"role": "user", "content": final_prompt},
            ],
            max_completion_tokens=model_config.get("generation", {}).get(
                "max_output_tokens", 256
            ),
            temperature=model_config.get("generation", {}).get("temperature", 0.0),
        )

        message = completion.choices[0].message.content

        if not message or not message.strip():
            raise ValueError("Received empty response from OpenAI API.")

        return message.strip()

    return generate_raw_response(
        model=session["model"],
        tokenizer=session["tokenizer"],
        prompt=final_prompt,
        max_new_tokens=model_config.get("generation", {}).get(
            "max_new_tokens", 128
        ),
    )