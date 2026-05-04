from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    T5Tokenizer,
)

from src.core.download_manager import get_original_model_dir


def normalize_model_id(model_id: str) -> str:
    """Convert Hugging Face model ids into local folder names."""
    return model_id.replace("/", "_")


def get_model_dir(model_config: dict) -> Path:
    """Resolve local model directory.

    Priority:
    1. paths.model_path or top-level model_path
    2. paths.finetuned_path when variant == "finetuned"
    3. default: paths.model_root / normalized(model_id) / variant
    """
    paths = model_config.get("paths", {})

    explicit_path = model_config.get("model_path") or paths.get("model_path")
    if explicit_path:
        model_dir = Path(explicit_path)
    else:
        variant = model_config.get("variant", "original")

        if variant == "finetuned" and paths.get("finetuned_path"):
            model_dir = Path(paths["finetuned_path"])
        else:
            model_root = Path(paths.get("model_root", "code/models"))
            model_id = model_config["model_id"]
            model_dir = model_root / normalize_model_id(model_id) / variant

    if not model_dir.exists() or not model_dir.is_dir():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    return model_dir


def get_adapter_dir(model_config: dict) -> Path | None:
    """Resolve optional PEFT adapter directory from model configuration."""
    adapter_path = model_config.get("adapter_path")
    if adapter_path is None:
        adapter_path = model_config.get("paths", {}).get("adapter_path")

    if not adapter_path:
        return None

    path = Path(adapter_path)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Adapter directory not found: {path}")

    return path


def _attach_peft_adapter(model, adapter_dir: Path):
    """Attach a LoRA/QLoRA adapter to an already loaded base model."""
    try:
        from peft import PeftModel
    except ImportError as exc:
        raise ImportError(
            "Loading LoRA/QLoRA adapters requires peft. "
            "Install it with: pip install peft"
        ) from exc

    return PeftModel.from_pretrained(
        model,
        str(adapter_dir),
        local_files_only=True,
    )


def get_model_architecture(model_config: dict) -> str:
    architecture = model_config.get("interface")
    if not architecture:
        raise ValueError("Model interface must be specified in the configuration.")
    return architecture.strip().lower()


def _get_generation_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _get_torch_dtype() -> torch.dtype:
    # float16 keeps 7B causal LMs feasible on one GPU.
    # On CPU we keep float32 for compatibility.
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32


def _load_tokenizer(model_dir: Path):
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_dir,
            local_files_only=True,
            use_fast=True,
        )
    except ValueError:
        tokenizer = T5Tokenizer.from_pretrained(
            model_dir,
            local_files_only=True,
        )

    # Decoder-only models often do not define a pad token.
    # For generation, eos-as-pad is the common safe fallback.
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    return tokenizer


def _load_seq2seq_model(model_dir: Path):
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_dir,
        local_files_only=True,
    )
    model.to(_get_generation_device())
    return model


def _load_causal_lm_model(model_dir: Path, adapter_dir: Path | None = None):
    dtype = _get_torch_dtype()

    # Preferred path for 7B models. device_map="auto" needs accelerate.
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_dir,
            local_files_only=True,
            torch_dtype=dtype,
            device_map="auto",
            low_cpu_mem_usage=True,
        )
    except (ImportError, ValueError) as exc:
        print(f"Warning: loading causal_lm without device_map='auto'. Reason: {exc}")
        model = AutoModelForCausalLM.from_pretrained(
            model_dir,
            local_files_only=True,
            torch_dtype=dtype,
        )
        model.to(_get_generation_device())

    if adapter_dir is not None:
        model = _attach_peft_adapter(model, adapter_dir)

    return model


def load_model_and_tokenizer(model_config: dict):
    model_dir = get_model_dir(model_config)
    adapter_dir = get_adapter_dir(model_config)
    architecture = get_model_architecture(model_config)

    tokenizer = _load_tokenizer(model_dir)

    if architecture == "seq2seq":
        model = _load_seq2seq_model(model_dir)
    elif architecture == "causal_lm":
        model = _load_causal_lm_model(model_dir, adapter_dir=adapter_dir)
    else:
        raise ValueError(
            f"Unsupported model architecture: {architecture}. "
            "Currently supported: seq2seq, causal_lm"
        )

    return tokenizer, model


def _format_prompt_for_model(tokenizer, model, prompt: str) -> str:
    is_encoder_decoder = bool(getattr(model.config, "is_encoder_decoder", False))

    if is_encoder_decoder:
        return prompt

    # For Qwen/Mistral/Llama instruct models, use the model's chat template
    # when available. This makes the prompt format closer to how the model
    # was instruction-tuned.
    if getattr(tokenizer, "chat_template", None):
        messages = [{"role": "user", "content": prompt}]
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    return prompt


def prepare_generation_inputs(tokenizer, model, prompt: str) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string.")

    formatted_prompt = _format_prompt_for_model(tokenizer, model, prompt)

    inputs = tokenizer(
        formatted_prompt,
        return_tensors="pt",
        truncation=True,
    )
    import os

    if os.environ.get("DEBUG_TOKEN_LENGTH") == "1":
        print("[TOKEN DEBUG] formatted prompt chars:", len(formatted_prompt))
        print("[TOKEN DEBUG] input_ids shape:", tuple(inputs["input_ids"].shape))
        print("[TOKEN DEBUG] tokenized input length:", inputs["input_ids"].shape[-1])
        print("[TOKEN DEBUG] tokenizer.model_max_length:", getattr(tokenizer, "model_max_length", None))
        print("[TOKEN DEBUG] model is_encoder_decoder:", bool(getattr(model.config, "is_encoder_decoder", False)))

    # Works for normal .to(device) models and for most device_map="auto" cases.
    first_param_device = next(model.parameters()).device
    return {key: value.to(first_param_device) for key, value in inputs.items()}


def generate_raw_response(
    model,
    tokenizer,
    prompt: str,
    max_new_tokens: int = 128,
    do_sample: bool = False,
    temperature: float = 0.0,
) -> str:
    model.eval()

    is_encoder_decoder = bool(getattr(model.config, "is_encoder_decoder", False))
    inputs = prepare_generation_inputs(tokenizer, model, prompt)

    generation_kwargs: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "do_sample": do_sample,
        "pad_token_id": tokenizer.pad_token_id,
    }

    if is_encoder_decoder:
        generation_kwargs["num_beams"] = 4

    if do_sample and temperature > 0:
        generation_kwargs["temperature"] = temperature

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            **generation_kwargs,
        )

    if is_encoder_decoder:
        decoded_ids = output_ids[0]
    else:
        # Decoder-only models return prompt + generated continuation.
        # Remove the prompt tokens so only the model answer remains.
        prompt_length = inputs["input_ids"].shape[-1]
        decoded_ids = output_ids[0][prompt_length:]

    return tokenizer.decode(decoded_ids, skip_special_tokens=True).strip()
