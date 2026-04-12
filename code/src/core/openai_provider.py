import os
from dotenv import load_dotenv


def get_openai_api_key(env_var_name:str = "OPENAI_API_KEY") -> str:
    load_dotenv()  # Load environment variables from .env file
    api_key = os.getenv(env_var_name)


    if not api_key or not api_key.strip():
        raise ValueError(f"API key not found in environment variable '{env_var_name}'")
    return api_key.strip()