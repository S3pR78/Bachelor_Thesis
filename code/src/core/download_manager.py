from pathlib import Path
from huggingface_hub import snapshot_download

def is_huggingface_provider(model_config: dict) -> bool:
    """
    Checks if the model provider is Hugging Face.

    Args:
        model_config (dict): The model configuration dictionary.
    Returns:
        bool: True if the provider is Hugging Face, False otherwise.
    """
    provider = model_config.get("provider", "").lower()
    return provider == "huggingface"



def ensure_huggingface_provider(model_config: dict) -> None:
    """
    Ensures that the model provider is Hugging Face.

    Args:
        model_config (dict): The model configuration dictionary.
    Raises:
        ValueError: If the provider is not Hugging Face.
    """
    if not is_huggingface_provider(model_config):
        raise ValueError("Model download is only (for now) supported when provider='huggingface'.")
    


def get_model_id(model_config: dict) -> str:
    """
    Retrieves the model ID from the model configuration.

    Args:
        model_config (dict): The model configuration dictionary.
    Returns:
        str: The model ID.
    Raises:
        ValueError: If the model ID is not specified in the configuration.
    """
    model_id = model_config.get("model_id")
    if not model_id:
        raise ValueError("Model ID must be specified in the configuration.")
    return model_id

