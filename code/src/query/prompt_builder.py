from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from src.utils.config_loader import get_configured_path, load_json_config
from src.ace.rendering import render_ace_context
from src.ace.routing import resolve_ace_playbook_path


EMPIRE_COMPASS_MODE = "empire_compass"
EMPIRE_COMPASS_MINI_MODE = "empire_compass_mini"
PGMR_MINI_MODE = "pgmr_mini"

EMPIRE_COMPASS_QUESTION_PLACEHOLDER = "[Research Question]"
MINI_QUESTION_PLACEHOLDER = "{question}"


def _get_configured_path_first(*keys: str) -> Path:
    last_error: Exception | None = None

    for key in keys:
        try:
            return get_configured_path(key)
        except KeyError as exc:
            last_error = exc

    joined_keys = ", ".join(keys)
    raise KeyError(f"None of these path_config keys exist: {joined_keys}") from last_error


def normalize_empire_compass_family(family: str) -> str:
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string.")

    normalized = family.strip().lower()
    family_aliases = {
        "nlp4re": "nlp4re",
        "empirical_research": "empirical_research",
        "empirical_research_practice": "empirical_research",
    }

    return family_aliases.get(normalized, normalized)


def validate_query_args(args) -> None:
    if args.prompt_mode in {EMPIRE_COMPASS_MODE, EMPIRE_COMPASS_MINI_MODE, PGMR_MINI_MODE} and not args.family:
        raise ValueError(
            f"The --family argument is required when using the '{args.prompt_mode}' prompt mode."
        )


def load_empire_compass_runner_config() -> dict:
    runner_config_path = _get_configured_path_first(
        "prompts.empire_compass_runner_config",
        "empire_compass_prompt_runner_config",
    )
    return load_json_config(runner_config_path)


def get_empire_compass_profile_for_family(family: str) -> dict:
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string.")

    normalized_family = normalize_empire_compass_family(family)
    runner_config = load_empire_compass_runner_config()

    profiles = runner_config.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("Runner configuration must contain a non-empty 'profiles' object.")

    profile = profiles.get(normalized_family)
    if not isinstance(profile, dict):
        available_families = ", ".join(profiles.keys())
        raise ValueError(
            f"Unknown Empire Compass template family '{normalized_family}'. "
            f"Available families are: {available_families}."
        )

    return profile


def get_empire_compass_mini_prompt_path_for_family(family: str) -> Path:
    normalized_family = normalize_empire_compass_family(family)

    if normalized_family == "nlp4re":
        return _get_configured_path_first(
            "prompts.empire_compass_mini_nlp4re_prompt",
            "empire_compass_mini_nlp4re_prompt",
        )

    if normalized_family == "empirical_research":
        return _get_configured_path_first(
            "prompts.empire_compass_mini_empirical_research_prompt",
            "empire_compass_mini_empirical_research_prompt",
        )

    raise ValueError(
        "No Empire Compass mini prompt is configured for family "
        f"'{family}' yet. Available mini families: nlp4re, empirical_research_practice."
    )



def get_pgmr_mini_prompt_path_for_family(family: str) -> Path:
    normalized = family.strip().lower()

    if normalized == "nlp4re":
        return get_configured_path("prompts.pgmr_mini_nlp4re_prompt")

    if normalized in {"empirical_research", "empirical_research_practice"}:
        return get_configured_path("prompts.pgmr_mini_empirical_research_prompt")

    raise ValueError(
        "No PGMR-mini prompt is configured for family "
        f"{family!r}. Available families: nlp4re, empirical_research_practice."
    )


def build_pgmr_mini_prompt(prompt_path: Path, family: str, question: str) -> str:
    prompt_text = load_text_file(prompt_path)
    return prompt_text.format(
        family=family,
        question=question.strip(),
    )

def ensure_empire_compass_prompt_exists(family: str, prompt_path: Path) -> None:
    if prompt_path.exists() and prompt_path.is_file():
        print("prompt file found.")
        return

    print(f"Prompt file missing. Generating Empire Compass prompt for family '{family}'...")

    runner_script_path = _get_configured_path_first(
        "prompts.empire_compass_runner_script",
        "empire_compass_runner_script",
    )
    runner_tsconfig_path = _get_configured_path_first(
        "prompts.empire_compass_runner_tsconfig",
        "empire_compass_runner_tsconfig",
    )

    repo_root = Path(__file__).resolve().parents[2]
    npx_path = shutil.which("npx")
    if not npx_path:
        raise FileNotFoundError(
            "Could not find 'npx' in PATH. "
            "Please make sure Node.js/npm is installed and 'npx' is available."
        )

    command = [
        "npx",
        "ts-node",
        "--project",
        str(runner_tsconfig_path),
        str(runner_script_path),
        family,
    ]

    subprocess.run(command, check=True, cwd=repo_root)

    if not prompt_path.exists() or not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt file was not created successfully: {prompt_path}")

    print("Prompt file generated successfully.")


def load_text_file(file_path: Path) -> str:
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def build_prompt_from_template(prompt_path: Path, question: str, placeholder: str) -> str:
    prompt_text = load_text_file(prompt_path)

    if placeholder not in prompt_text:
        raise ValueError(
            f"Prompt template does not contain expected placeholder "
            f"{placeholder}: {prompt_path}"
        )

    return prompt_text.replace(placeholder, question.strip())


def build_empire_compass_prompt(prompt_path: Path, question: str) -> str:
    return build_prompt_from_template(
        prompt_path=prompt_path,
        question=question,
        placeholder=EMPIRE_COMPASS_QUESTION_PLACEHOLDER,
    )


def build_empire_compass_mini_prompt(prompt_path: Path, question: str) -> str:
    return build_prompt_from_template(
        prompt_path=prompt_path,
        question=question,
        placeholder=MINI_QUESTION_PLACEHOLDER,
    )


def infer_ace_mode(prompt_mode: str | None) -> str:
    """Infer a default ACE playbook mode from the existing prompt mode."""
    normalized = (prompt_mode or "").strip().lower()
    if "pgmr" in normalized:
        return "pgmr_lite"
    return "direct_sparql"


def append_ace_context_to_prompt(
    *,
    prompt: str,
    family: str | None,
    prompt_mode: str | None,
    ace_playbook_path: str | None = None,
    ace_playbook_dir: str | None = None,
    ace_mode: str | None = None,
    ace_max_bullets: int = 0,
    ace_include_patterns: bool = True,
    model_name: str | None = None,
) -> str:
    """Prepend a compact ACE playbook block to an already-built prompt.

    The function is intentionally small and optional:
    if no playbook path or no bullets are requested, it returns the original prompt.
    """
    if ace_max_bullets <= 0:
        return prompt

    if not family:
        return prompt

    resolved_ace_mode = ace_mode or infer_ace_mode(prompt_mode)

    resolved_playbook_path = resolve_ace_playbook_path(
        ace_playbook_path=ace_playbook_path,
        ace_playbook_dir=ace_playbook_dir,
        family=family,
        mode=resolved_ace_mode,
        model_name=model_name,
    )

    if not resolved_playbook_path:
        return prompt

    ace_context = render_ace_context(
        playbook_path=resolved_playbook_path,
        family=family,
        mode=resolved_ace_mode,
        max_bullets=ace_max_bullets,
        include_patterns=ace_include_patterns,
    ).strip()

    if not ace_context:
        return prompt

    return f"{ace_context}\n\n{prompt.strip()}"


def build_final_prompt_for_question(
    question: str,
    prompt_mode: str | None,
    family: str | None,
    ace_playbook_path: str | None = None,
    ace_playbook_dir: str | None = None,
    ace_mode: str | None = None,
    ace_max_bullets: int = 0,
    ace_include_patterns: bool = True,
    model_name: str | None = None,
) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string.")

    if not prompt_mode:
        final_prompt = question.strip()

    elif prompt_mode == EMPIRE_COMPASS_MODE:
        if not family:
            raise ValueError(
                "family must be provided when using 'empire_compass' prompt mode."
            )

        profile = get_empire_compass_profile_for_family(family)
        prompt_output_path = Path(profile["output_txt_path"])

        print(f"Empire Compass family: {family}")
        print(f"Expected prompt path: {prompt_output_path}")

        ensure_empire_compass_prompt_exists(family, prompt_output_path)

        final_prompt = build_empire_compass_prompt(prompt_output_path, question)

    elif prompt_mode == EMPIRE_COMPASS_MINI_MODE:
        if not family:
            raise ValueError(
                "family must be provided when using 'empire_compass_mini' prompt mode."
            )

        prompt_path = get_empire_compass_mini_prompt_path_for_family(family)

        print(f"Empire Compass mini family: {family}")
        print(f"Mini prompt path: {prompt_path}")

        final_prompt = build_empire_compass_mini_prompt(prompt_path, question)

    elif prompt_mode == PGMR_MINI_MODE:
        if not family:
            raise ValueError(
                "family must be provided when using 'pgmr_mini' prompt mode."
            )

        prompt_path = get_pgmr_mini_prompt_path_for_family(family)

        print(f"PGMR mini family: {family}")
        print(f"PGMR mini prompt path: {prompt_path}")

        final_prompt = build_pgmr_mini_prompt(
            prompt_path=prompt_path,
            family=family,
            question=question,
        )

    else:
        final_prompt = question.strip()

    return append_ace_context_to_prompt(
        prompt=final_prompt,
        family=family,
        prompt_mode=prompt_mode,
        ace_playbook_path=ace_playbook_path,
        ace_playbook_dir=ace_playbook_dir,
        ace_mode=ace_mode,
        ace_max_bullets=ace_max_bullets,
        ace_include_patterns=ace_include_patterns,
        model_name=model_name,
    )
