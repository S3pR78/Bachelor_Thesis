from __future__ import annotations

from pathlib import Path

from src.ace.playbook import AcePlaybook
from src.query.prompt_builder import build_final_prompt_for_question


def test_build_final_prompt_prepends_ace_context_for_plain_question(tmp_path: Path) -> None:
    playbook_path = tmp_path / "playbook.json"
    playbook = AcePlaybook.from_dict(
        {
            "schema_version": "ace_playbook_v1",
            "family": "nlp4re",
            "mode": "pgmr_lite",
            "bullets": [
                {
                    "family": "global",
                    "mode": "any",
                    "category": "output_format",
                    "title": "Return only query",
                    "content": "Do not add explanations.",
                    "priority": 100,
                },
                {
                    "family": "nlp4re",
                    "mode": "pgmr_lite",
                    "category": "contribution_pattern",
                    "title": "Use contribution pattern",
                    "content": "Connect paper to contribution first.",
                    "positive_pattern": "?paper pgmr:has_contribution ?contribution .",
                    "priority": 90,
                },
            ],
        }
    )
    playbook.save(playbook_path)

    prompt = build_final_prompt_for_question(
        question="Which evaluation metrics are used in NLP4RE studies?",
        prompt_mode=None,
        family="nlp4re",
        ace_playbook_path=str(playbook_path),
        ace_mode="pgmr_lite",
        ace_max_bullets=2,
    )

    assert prompt.startswith("ACE playbook rules")
    assert "Return only query" in prompt
    assert "Use contribution pattern" in prompt
    assert "Which evaluation metrics are used in NLP4RE studies?" in prompt


def test_build_final_prompt_without_ace_stays_unchanged() -> None:
    prompt = build_final_prompt_for_question(
        question="Which datasets are used?",
        prompt_mode=None,
        family="nlp4re",
    )

    assert prompt == "Which datasets are used?"
