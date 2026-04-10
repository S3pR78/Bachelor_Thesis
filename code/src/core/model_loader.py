from pathlib import Path

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from src.core.download_manager import get_original_model_dir


def get_model_dir(model_config: dict) -> Path:
    """
    Retrieves the local model directory from the model configuration.
    """
    model_dir = get_original_model_dir(model_config)

    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    return model_dir


def get_model_architecture(model_config: dict) -> str:
    """
    Retrieves the model architecture from the model configuration.
    """
    architecture = model_config.get("architecture")

    if not architecture:
        raise ValueError("Model architecture must be specified in the configuration.")

    return architecture.strip().lower()


def load_model_and_tokenizer(model_config: dict):
    """
    Loads the tokenizer and model based on the configured architecture.
    """
    model_dir = get_model_dir(model_config)
    architecture = get_model_architecture(model_config)

    tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,
    )

    if architecture == "seq2seq":
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_dir,
            local_files_only=True,
        )
    else:
        raise ValueError(
            f"Unsupported model architecture: {architecture}. "
            "Currently supported: seq2seq"
        )

    return tokenizer, model


def prepare_generation_inputs(
        tokenizer,
        prompt: str,
):
    """
    Prepares the input tensors for generation based on the provided prompt.

    Args:
        tokenizer: The tokenizer to use for encoding the prompt.
        prompt (str): The input prompt for generation.  
    """

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string.")

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True
    )

    return inputs



def generate_raw_response(
        model,
        tokenizer,
        prompt: str,
        max_new_tokens: int = 128,
) -> str:
    """
    Generates a raw response from the model based on the provided prompt.

    Args:
        model: The language model to use for generation.
        tokenizer: The tokenizer to use for encoding the prompt and decoding the response.
        prompt (str): The input prompt for generation.
        max_new_tokens (int): The maximum number of new tokens to generate.
    Returns:
        str: The generated response as a string.
    """

    model.eval()
    
    inputs = prepare_generation_inputs(tokenizer, prompt)

    output_ids = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
    )

    return tokenizer.decode(output_ids[0], skip_special_tokens=True)