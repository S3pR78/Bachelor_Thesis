import argparse
from src.utils.config_loader import load_json_config
from src.core.model_loader import load_model_and_tokenizer, generate_raw_response

CONFIG_PATH = 'code/config/model_config.json'

def run_query_task(args: argparse.Namespace) -> int:
    print("Running query task with args:", args)
    return 0

def run_train_task(args: argparse.Namespace) -> int:
    print("Running training task with args:", args)
    return 0

def run_evaluate_task(args: argparse.Namespace) -> int:
    print("Running evaluation task with args:", args)
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orkg-sparql-pipeline",
        description="CLI entry point for the ORKG pipeline."
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    query_parser = subparsers.add_parser("query", help="Run the query task.")
    query_parser.add_argument("--model", required=True, help="Model to use for querying.")
    query_parser.add_argument("--template", required=False, help="Template being used. (e.g., 'nlp4re' or 'empirical_research')")
    query_parser.add_argument("--question", required=True, help="The question to query.")
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


def run_query(args: argparse.Namespace):
    model_config = load_json_config(config_path=CONFIG_PATH)

    tokenizer, model = load_model_and_tokenizer(model_config)

    response = generate_raw_response(
        model=model,
        tokenizer=tokenizer,
        prompt=args.question,
        max_new_tokens=128
    )

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