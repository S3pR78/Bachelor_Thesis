import argparse
from src.core.model_loader import load_model_and_tokenizer, generate_raw_response
from src.core.openai_provider import generate_raw_response_openai

from src.utils.config_loader import (
    load_json_config,
    get_model_entry,
)

from src.query.prompt_builder import (
    build_final_prompt_for_question,
    validate_query_args,
)

CONFIG_PATH = 'code/config/model_config.json'

"""
This function runs the query task based on the provided command-line arguments.
It first validates the arguments, then builds the final prompt based on the question and selected prompt mode.
It loads the model configuration from a JSON file and determines which provider to use (e.g., OpenAI or a local model).
If the provider is OpenAI, it calls the function to generate a response using the OpenAI API. If the provider is not OpenAI, 
it loads the local model and tokenizer, and generates
a response using the local model. Finally, it prints the generated response and returns 0 to indicate successful execution.
"""
def run_query_task(args: argparse.Namespace) -> int:
    validate_query_args(args)

    final_prompt = build_final_prompt_for_question(
        question=args.question,
        prompt_mode=args.prompt_mode,
        family=args.family,
    )

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


# def get_prompt_token_count(tokenizer, prompt:str) -> int:
#     encoded = tokenizer(prompt, return_tensors="pt", truncation=False)
#     return int(encoded["input_ids"].shape[1])


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