import argparse
import subprocess
from src.core.model_loader import load_model_and_tokenizer, generate_raw_response
from pathlib import Path
import shutil
from src.core.openai_provider import generate_raw_response_openai

from src.utils.config_loader import (
    load_json_config,
    get_model_entry,
    get_configured_path,
)

CONFIG_PATH = 'code/config/model_config.json'

def run_query_task(args: argparse.Namespace) -> int:
    validate_query_args(args)
    final_prompt = args.question

    if args.prompt_mode == "empire_compass":
        profile = get_empire_compass_profile_for_family(args.family)
        prompt_output_path = Path(profile["output_txt_path"])

        print(f"Empire Compass family: {args.family}")
        print(f"Expected prompt path: {prompt_output_path}")
        ensure_empire_compass_prompt_exists(args.family, prompt_output_path)
        final_prompt = build_empire_compass_prompt(prompt_output_path, args.question)

    print("Running query task with args:", args)
    
    full_model_config = load_json_config(CONFIG_PATH)
    model_config = get_model_entry(full_model_config, args.model)

    provider = model_config.get("provider", "").strip().lower()
    if provider == "openai":
        response = generate_raw_response_openai(
            model_id = model_config.get("model_id"),
            prompt=final_prompt,
            max_output_tokens=model_config.get("generation", {}).get("max_new_tokens", 256),
            temperature=model_config.get("generation", {}).get("temperature", 0.0),
            env_var_name=model_config.get("api", {}).get("env_var_name", "OPENAI_API_KEY")
        )   
        print("Generated response:", response)
        return 0
    else:
        tokenizer, model = load_model_and_tokenizer(model_config)
        # prompt_token_count = get_prompt_token_count(tokenizer, final_prompt)
        # print(f"Prompt token count: {prompt_token_count}")

        # if prompt_token_count > 512 :
        #     raise ValueError(
        #         f"Prompt is too long ({prompt_token_count} tokens). "
        #         "Please shorten the question or choose a different prompt mode."
        #     )
        
        response = generate_raw_response(
            model=model,
            tokenizer=tokenizer,
            prompt=final_prompt,
            max_new_tokens=model_config.get("generation", {}).get("max_new_tokens", 128)
        )

    print("Generated response:", response)
    return 0

def run_train_task(args: argparse.Namespace) -> int:
    print("Running training task with args:", args)

    return 0

def run_evaluate_task(args: argparse.Namespace) -> int:
    print("Running evaluation task with args:", args)
    return 0


def validate_query_args(args: argparse.Namespace) -> None:
    if args.prompt_mode == "empire_compass" and not args.family:
        raise ValueError("The --family argument is required when using the 'empire_compass' prompt mode.")
    


def load_empire_compass_runner_config() -> dict:
    runner_config_path = get_configured_path("empire_compass_prompt_runner_config")
    return load_json_config(runner_config_path)


def get_empire_compass_profile_for_family(family: str) ->dict:
    if not isinstance(family,str) or not family.strip():
        raise ValueError("family must be a non-empty string.")
    
    normalized_family = family.strip().lower()
    runner_config = load_empire_compass_runner_config()

    profiles = runner_config.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("Runner configuration must contain a non-empty 'profiles' object.")

    profile = profiles.get(normalized_family)
    if not isinstance(profile, dict):
        available_families = ", ".join(profiles.keys())
        raise ValueError(
            f"Unknown Empire Compass template family '{normalized_family}'"
            f". Available families are: {available_families}."
        )

    return profile

# now is this function actually useless. maybe remove it!!
def ensure_prompt_file_exists(prompt_path: Path) -> None:
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. "
            "Generate the Empire Compass prompt first."           
        )

    if not prompt_path.is_file():
        raise FileNotFoundError(
            f"Prompt path exists but is not a file: {prompt_path}"
        )

def ensure_empire_compass_prompt_exists(family: str, prompt_path: Path) -> None:
    if prompt_path.exists() and prompt_path.is_file():
        print("prompt file found.")
        return

    print(f"Prompt file missing. Generating Empire Compass prompt for family '{family}'...")

    runner_script_path = get_configured_path("empire_compass_runner_script")
    runner_tsconfig_path = get_configured_path("empire_compass_runner_tsconfig")

    repo_root = Path(__file__).resolve().parents[2]

    npx_path = shutil.which("npx")

    if not npx_path:
        raise FileNotFoundError(
            "Could not find 'npx' in PATH. "
            "Please make sure Node.js/npm is installed on this machine "
            "and that 'npx' is available in the active shell environment."
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
        raise FileNotFoundError(
            f"Prompt file was not created successfully: {prompt_path}"
        )
    print("Prompt file generated successfully.")



def load_text_file(file_path: Path) ->str:
    return file_path.read_text(encoding="utf-8")

def build_empire_compass_prompt(prompt_path: Path, question: str) ->str:
    prompt_text = load_text_file(prompt_path)

    placeholder = "[Research Question]"

    if placeholder not in prompt_text:
        raise ValueError(
            f"Empire Compass prompt does not contain the expectd placeholder "
            f"{placeholder}: {prompt_path}"
        )
    
    return prompt_text.replace(placeholder, question.strip())


def get_prompt_token_count(tokenizer, prompt:str) -> int:
    encoded = tokenizer(prompt, return_tensors="pt", truncation=False)
    return int(encoded["input_ids"].shape[1])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orkg-sparql-pipeline",
        description="CLI entry point for the ORKG pipeline."
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)
    query_parser = subparsers.add_parser("query", help="Run the query task.")
    query_parser.add_argument("--model", required=True, help="Model to use for querying.")
    query_parser.add_argument("--prompt-mode", required=False,choices=["empire_compass", "zero_shot", "few_shot"] ,help="Prompt mode to use for querying.")
    query_parser.add_argument("--family", required=False,choices=["nlp4re", "empirical_research"] ,help="Template family to use for querying (e.g., 'nlp4re', 'empirical_research').")
    query_parser.add_argument("--question", required=True, help="The question to query the model with.")


    query_parser.set_defaults(func=run_query_task)


    train_parser = subparsers.add_parser("train", help="Run the training task.")
    train_parser.add_argument("--model", required=True, help="Model to use for training.")
    train_parser.set_defaults(func=run_train_task)
    # training method and training data can be added as arguments here, e.g., --method, --data

    evaluate_parser = subparsers.add_parser("evaluate", help="Run the evaluation task.")
    evaluate_parser.add_argument("--model", required=True, help="Model to use for evaluation.")
    evaluate_parser.set_defaults(func=run_evaluate_task)
    # evaluation files can be added as arguments here, e.g., --predictions, --references
    
    return parser



def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return

    args.func(args)
    return 0



if __name__ == "__main__":
    raise SystemExit(main())