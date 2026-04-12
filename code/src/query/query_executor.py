from src.core.model_loader import load_model_and_tokenizer, generate_raw_response
from src.core.openai_provider import generate_raw_response_openai
from src.utils.config_loader import load_json_config, get_model_entry


CONFIG_PATH = "code/config/model_config.json"


def generate_query_response(model_name: str, final_prompt: str) -> str:
    full_model_config = load_json_config(CONFIG_PATH)
    model_config = get_model_entry(full_model_config, model_name)

    provider = model_config.get("provider", "").strip().lower()

    if provider == "openai":
        return generate_raw_response_openai(
            model_id=model_config.get("model_id"),
            prompt=final_prompt,
            max_output_tokens=model_config.get("generation", {}).get(
                "max_output_tokens", 256
            ),
            temperature=model_config.get("generation", {}).get("temperature", 0.0),
            env_var_name=model_config.get("api", {}).get(
                "env_var_name", "OPENAI_API_KEY"
            ),
        )

    tokenizer, model = load_model_and_tokenizer(model_config)

    return generate_raw_response(
        model=model,
        tokenizer=tokenizer,
        prompt=final_prompt,
        max_new_tokens=model_config.get("generation", {}).get(
            "max_new_tokens", 128
        ),
    )