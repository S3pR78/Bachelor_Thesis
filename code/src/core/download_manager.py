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