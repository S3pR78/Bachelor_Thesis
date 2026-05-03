from __future__ import annotations

from pathlib import Path

from src.ace.routing import resolve_ace_playbook_path, safe_name


def test_safe_name_normalizes_model_ids() -> None:
    assert safe_name("Qwen/Qwen2.5-Coder-7B-Instruct") == "qwen_qwen2_5_coder_7b_instruct"


def test_resolve_prefers_explicit_playbook_path(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.json"
    resolved = resolve_ace_playbook_path(
        ace_playbook_path=str(explicit),
        ace_playbook_dir=str(tmp_path),
        family="nlp4re",
        mode="pgmr_lite",
        model_name="qwen",
    )

    assert resolved == str(explicit)


def test_resolve_prefers_model_specific_playbook(tmp_path: Path) -> None:
    model_dir = tmp_path / "qwen_pgmr_finetuned"
    model_dir.mkdir()

    model_specific = model_dir / "nlp4re_pgmr_lite_playbook.json"
    shared = tmp_path / "nlp4re_pgmr_lite_playbook.json"

    model_specific.write_text("{}", encoding="utf-8")
    shared.write_text("{}", encoding="utf-8")

    resolved = resolve_ace_playbook_path(
        ace_playbook_dir=str(tmp_path),
        family="nlp4re",
        mode="pgmr_lite",
        model_name="qwen_pgmr_finetuned",
    )

    assert resolved == str(model_specific)


def test_resolve_falls_back_to_shared_playbook(tmp_path: Path) -> None:
    shared = tmp_path / "nlp4re_pgmr_lite_playbook.json"
    shared.write_text("{}", encoding="utf-8")

    resolved = resolve_ace_playbook_path(
        ace_playbook_dir=str(tmp_path),
        family="nlp4re",
        mode="pgmr_lite",
        model_name="missing_model",
    )

    assert resolved == str(shared)
