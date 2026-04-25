from pathlib import Path

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, T5Tokenizer

from src.core.download_manager import get_original_model_dir


def get_model_dir(model_config: dict) -> Path:
    """
    Resolve the local model directory from the model configuration.

    Default:
      code/models/<safe_model_id>/original

    Custom variant example:
      code/models/<safe_model_id>/finetuned/pgmr_lite_v2/.../final_model
    """
    base_model_dir = get_original_model_dir(model_config).parent

    variant = str(model_config.get("variant", "original")).strip() or "original"
    model_dir = base_model_dir / variant

    if not model_dir.exists() or not model_dir.is_dir():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    return model_dir


def get_model_architecture(model_config: dict) -> str:
    architecture = model_config.get("interface")

    if not architecture:
        raise ValueError("Model interface must be specified in the configuration.")

    return architecture.strip().lower()


def load_model_and_tokenizer(model_config: dict):
    model_dir = get_model_dir(model_config)
    architecture = get_model_architecture(model_config)

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_dir,
            local_files_only=True,
            use_fast=False,
        )
    except ValueError:
        tokenizer = T5Tokenizer.from_pretrained(
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


def prepare_generation_inputs(tokenizer, prompt: str):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string.")

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
    )

    return inputs


def generate_raw_response(
    model,
    tokenizer,
    prompt: str,
    max_new_tokens: int = 128,
) -> str:
    model.eval()

    inputs = prepare_generation_inputs(tokenizer, prompt)

    output_ids = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        num_beams=4,
        do_sample=False,
        early_stopping=True,
        repetition_penalty=1.2,
        no_repeat_ngram_size=3,
    )

    return tokenizer.decode(output_ids[0], skip_special_tokens=True)
