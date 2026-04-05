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


def get_model_root(model_config: dict) -> Path:
    """
    Retrieves the model root directory from the model configuration.

    Args:
        model_config (dict): The model configuration dictionary.
    Returns:
        Path: The model root directory.
    """

    model_root = model_config.get("model_root", "models")
    if not model_root:
        model_root = "models"
    return Path(model_root)

def get_model_family_dir(model_config: dict) -> Path:
    """
    Retrieves the model family directory from the model configuration.

    Args:
        model_config (dict): The model configuration dictionary.
    Returns:
        Path: The model family directory.
    """
    model_root = get_model_root(model_config)
    model_id = get_model_id(model_config)
    safe_model_name = model_id.replace("/", "_")
    return model_root / safe_model_name

def get_original_model_dir(model_config: dict) -> Path:
    return get_model_family_dir(model_config) / "original"



def download_model(model_config: dict) -> Path:
    """
    Downloads the model specified in the model configuration.
    
    Args:
        model_config (dict): The model configuration dictionary.
    Returns:        
        Path: The path to the downloaded model directory.           
    """
    ensure_huggingface_provider(model_config)

    model_id = get_model_id(model_config)
    original_dir = get_original_model_dir(model_config)
    cache_dir = model_config.get("cache_dir")

    original_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=model_id,
        local_dir=str(original_dir),
        cache_dir=cache_dir,
    )

    return original_dir
