import shutil
import subprocess
from pathlib import Path
from src.utils.config_loader import get_configured_path, load_json_config



def normalize_empire_compass_family(family: str) -> str:
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string.")

    normalized = family.strip().lower()

    family_aliases = {
        "nlp4re": "nlp4re",
        "empirical_research": "empirical_research",
        "empirical_research_practice": "empirical_research",
    }

    if normalized in family_aliases:
        return family_aliases[normalized]

    return normalized

def validate_query_args(args) -> None:
    if args.prompt_mode == "empire_compass" and not args.family:
        raise ValueError("The --family argument is required when using the 'empire_compass' prompt mode.")
    

"""
This function loads the configuration for the Empire Compass prompt runner from a JSON file. 
The path to the configuration file is retrieved using the get_configured_path utility function, 
which looks up the path based on a key (in this case, "empire_compass_prompt_runner_config
"""
def load_empire_compass_runner_config() -> dict:
    runner_config_path = get_configured_path("empire_compass_prompt_runner_config")
    return load_json_config(runner_config_path)



"""
This function retrieves the Empire Compass prompt profile for a given template family. 
It first validates the input family name, then loads the runner configuration to find the corresponding profile. 
If the family is not found in the configuration, it raises a ValueError with a message listing the available families. 
If the profile is found, it returns the profile as a dictionary. This profile is expected to contain information such as the path to the generated prompt file for that family, which will be used later to build the final prompt for the model.
"""
def get_empire_compass_profile_for_family(family: str) ->dict:
    if not isinstance(family,str) or not family.strip():
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
            f"Unknown Empire Compass template family '{normalized_family}'"
            f". Available families are: {available_families}."
        )

    return profile



"""
This function checks if the Empire Compass prompt file
for the specified family exists at the expected location. 
If the file is missing, it runs the Empire Compass prompt generation script using npx and ts-node to create the prompt file. 
After running the script, it verifies that the prompt file was created successfully. 
If any step fails (e.g., npx not found, script execution failure, or prompt file still missing),
it raises an appropriate error with a descriptive message.
"""
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


"""
This function is responsible for building the final prompt that will be sent 
to the model based on the user's question and the selected prompt mode. 
If the 'empire_compass' prompt mode is selected, it will ensure that the corresponding 
prompt file exists (generating it if necessary) and then build the final prompt by 
replacing the placeholder in the prompt template with the user's question. 
For other prompt modes (e.g., 'zero_shot', 'few_shot'), 
it currently just returns the question as the final prompt, but this can 
be extended in the future to apply different formatting or templates based on the selected prompt mode.
"""
def build_final_prompt_for_question(
        question: str,
        prompt_mode: str,
        family: str
) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string.")
    
    final_prompt = question.strip()

    if prompt_mode == "empire_compass":
        if not family:
            raise ValueError("family must be provided when using 'empire_compass' prompt mode.")
        
        profile = get_empire_compass_profile_for_family(family)
        prompt_output_path = Path(profile["output_txt_path"])

        print(f"Empire Compass family: {family}")
        print(f"Expected prompt path: {prompt_output_path}")



        ensure_empire_compass_prompt_exists(family, prompt_output_path)
        final_prompt = build_empire_compass_prompt(prompt_output_path, question)

    return final_prompt