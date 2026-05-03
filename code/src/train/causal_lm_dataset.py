from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch.utils.data import Dataset


def build_causal_lm_prompt(tokenizer: Any, prompt: str) -> str:
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("prompt must be non-empty.")

    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )

    return f"User: {prompt}\nAssistant: "


def _build_target_ids(
    tokenizer: Any,
    target: str,
    max_target_length: int,
) -> list[int]:
    if max_target_length <= 0:
        raise ValueError("max_target_length must be positive.")

    target = target.strip()
    if not target:
        raise ValueError("target must be non-empty.")

    eos_id = tokenizer.eos_token_id
    target_ids = tokenizer(
        target,
        add_special_tokens=False,
    )["input_ids"]

    if eos_id is not None and max_target_length > 1:
        target_ids = target_ids[: max_target_length - 1]
        target_ids.append(eos_id)
    else:
        target_ids = target_ids[:max_target_length]

    return target_ids


def tokenize_prompt_target_example(
    *,
    tokenizer: Any,
    prompt: str,
    target: str,
    max_prompt_length: int,
    max_target_length: int,
) -> dict[str, list[int]]:
    if max_prompt_length <= 0:
        raise ValueError("max_prompt_length must be positive.")

    prompt_text = build_causal_lm_prompt(tokenizer, prompt)

    prompt_ids = tokenizer(
        prompt_text,
        add_special_tokens=False,
    )["input_ids"]

    # Keep the end of the prompt if it is too long, because the question is
    # normally near the end of the training prompt.
    if len(prompt_ids) > max_prompt_length:
        prompt_ids = prompt_ids[-max_prompt_length:]

    target_ids = _build_target_ids(
        tokenizer=tokenizer,
        target=target,
        max_target_length=max_target_length,
    )

    input_ids = prompt_ids + target_ids
    attention_mask = [1] * len(input_ids)

    # Important: no loss on prompt tokens, only on the target query.
    labels = [-100] * len(prompt_ids) + target_ids.copy()

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


class CausalLMPromptTargetDataset(Dataset):
    def __init__(
        self,
        *,
        examples: list[dict[str, str]],
        tokenizer: Any,
        max_prompt_length: int,
        max_target_length: int,
    ) -> None:
        self.items = [
            tokenize_prompt_target_example(
                tokenizer=tokenizer,
                prompt=example["input_text"],
                target=example["target_text"],
                max_prompt_length=max_prompt_length,
                max_target_length=max_target_length,
            )
            for example in examples
        ]

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.items[index]


@dataclass
class CausalLMMaskedCollator:
    tokenizer: Any

    def __call__(self, features: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
        pad_token_id = self.tokenizer.pad_token_id
        if pad_token_id is None:
            pad_token_id = self.tokenizer.eos_token_id

        if pad_token_id is None:
            raise ValueError("Tokenizer needs either pad_token_id or eos_token_id.")

        max_length = max(len(feature["input_ids"]) for feature in features)

        batch_input_ids = []
        batch_attention_mask = []
        batch_labels = []

        for feature in features:
            length = len(feature["input_ids"])
            pad_length = max_length - length

            batch_input_ids.append(feature["input_ids"] + [pad_token_id] * pad_length)
            batch_attention_mask.append(feature["attention_mask"] + [0] * pad_length)
            batch_labels.append(feature["labels"] + [-100] * pad_length)

        return {
            "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(batch_attention_mask, dtype=torch.long),
            "labels": torch.tensor(batch_labels, dtype=torch.long),
        }