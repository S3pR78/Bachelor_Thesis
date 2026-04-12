import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_OPENAI_DEVELOPER_MESSAGE = (
    "You are an expert ORKG SPARQL query generator. "
    "Generate precise, syntactically correct, and executable SPARQL queries "
    "for research questions. Return the query only unless asked otherwise."
)


def get_openai_api_key(env_var_name: str = "OPENAI_API_KEY") -> str:
    repo_root = Path(__file__).resolve().parents[3]
    dotenv_path = repo_root / ".env"

    load_dotenv(dotenv_path=dotenv_path)

    api_key = os.getenv(env_var_name)

    if not api_key or not api_key.strip():
        raise ValueError(
            f"OpenAI API key not found in environment variable '{env_var_name}'. "
            "Please set it in the .env file or your environment variables."
        )

    return api_key.strip()


def create_openai_client(env_var_name: str = "OPENAI_API_KEY") -> OpenAI:
    api_key = get_openai_api_key(env_var_name=env_var_name)
    return OpenAI(api_key=api_key)


def generate_raw_response_openai(
    model_id: str,
    prompt: str,
    max_output_tokens: int = 256,
    temperature: float = 0.0,
    developer_message: Optional[str] = None,
    env_var_name: str = "OPENAI_API_KEY",
) -> str:
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model_id must be a non-empty string.")

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string.")

    client = create_openai_client(env_var_name=env_var_name)

    effective_developer_message = developer_message
    if effective_developer_message is None:
        effective_developer_message = DEFAULT_OPENAI_DEVELOPER_MESSAGE

    messages = []

    if effective_developer_message and effective_developer_message.strip():
        messages.append(
            {"role": "developer", "content": effective_developer_message.strip()}
        )

    messages.append({"role": "user", "content": prompt.strip()})

    completion = client.chat.completions.create(
        model=model_id.strip(),
        messages=messages,
        max_tokens=max_output_tokens,
        temperature=temperature,
    )

    message = completion.choices[0].message.content

    if not message or not message.strip():
        raise ValueError("Received empty response from OpenAI API.")

    return message.strip()