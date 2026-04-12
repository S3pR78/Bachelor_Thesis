import argparse
from src.query.query_executor import generate_query_response
from src.evaluate.run_paths import ensure_evaluate_run_dir
from src.query.prompt_builder import (
    build_final_prompt_for_question,
    validate_query_args,
)
from src.evaluate.dataset_loader import (
    select_entry_fields,
    load_evaluate_entries,
)


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

    response = generate_query_response(
        model_name=args.model,
        final_prompt=final_prompt,
    )

    print("Generated response:", response)
    return 0




def run_train_task(args: argparse.Namespace) -> int:
    print("Running training task with args:", args)
    return 0


def run_evaluate_task(args: argparse.Namespace) -> int:
    print("Running evaluation task with args:", args)

    entries = load_evaluate_entries(
        dataset_path=args.dataset,
        limit=args.limit,
    )

    run_dir = ensure_evaluate_run_dir(
        model_name=args.model,
        dataset_path=args.dataset,
        prompt_mode=None,
    )

    print(f"Run directory: {run_dir}")
    print(f"Loaded entries for this run: {len(entries)}")

    print(f"Loaded entries for this run: {len(entries)}")

    for index, entry in enumerate(entries, start=1):
        selected = select_entry_fields(
            entry,
            ["uid", "question", "gold_sparql"],
        )

        entry_id = selected["uid"] or f"item_{index}"
        question = selected["question"]
        gold_query = selected["gold_sparql"]

        print(f"[{index}/{len(entries)}] id={entry_id}")
        print(f"  question={question!r}")
        print(f"  has_gold_query={gold_query is not None}")

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
    evaluate_parser.add_argument("--dataset", required=True, help="Dataset to use for evaluation.")
    evaluate_parser.add_argument("--limit", required=False, type=int, help="Use only the first N dataset entries for a test run.")
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