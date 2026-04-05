from pathlib import Path
from src.core.download_manager import get_original_model_path
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

def get_model_dir(model_config: dict) -> Path:
    """
    Retrieves the model directory from the model configuration.

    Args:
        model_config (dict): The model configuration dictionary.
    Returns: 
        the model directory.    
    """
    model_dir = get_original_model_path(model_config)
    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")
    return model_dir




def load_model_and_tokenizer(model_config: dict):
    """Loads the model and tokenizer based on the model configuration."""
    model_dir = get_model_dir(model_config)

    tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,
    )

    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_dir,
        local_files_only=True,
    )

    return tokenizer, model