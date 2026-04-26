import argparse
from pathlib import Path
from src.query.query_executor import generate_query_response
from src.evaluate.runner import execute_evaluate_task
from src.pgmr.postprocess import postprocess_pgmr_query
from src.query.prompt_builder import (
    build_final_prompt_for_question,
    validate_query_args,
)
from src.train.seq2seq_trainer import run_seq2seq_training
from src.pgmr.postprocess import postprocess_pgmr_query
from src.pgmr.restore import restore_pgmr_query


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
    print("="*80)
    print("Generated response:", response)

    pgmr_query = response

    if getattr(args, "postprocess_pgmr", False) or getattr(args, "restore_pgmr", False):
        pgmr_query = postprocess_pgmr_query(response)
        print("="*80)
        print("\nPostprocessed PGMR:")
        print(pgmr_query)

    if getattr(args, "restore_pgmr", False):
        restore_result = restore_pgmr_query(
            pgmr_query=pgmr_query,
            memory_dir=Path(args.pgmr_memory_dir),
        )
        print("="*80)
        print("\nRestored ORKG SPARQL:")
        print(restore_result.restored_query)

        if restore_result.missing_mapping_tokens:
            print("\nMissing PGMR mappings:")
            for token in restore_result.missing_mapping_tokens:
                print(f"- {token}")

        if restore_result.remaining_pgmr_tokens:
            print("\nRemaining PGMR tokens:")
            for token in restore_result.remaining_pgmr_tokens:
                print(f"- {token}")




def run_train_task(args: argparse.Namespace) -> int:

    run_seq2seq_training(
        train_config_path=args.train_config,
        run_name=args.run,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        override_epochs=args.override_epochs,
        dry_run=args.dry_run,
    )

    return 0

def run_evaluate_task(args: argparse.Namespace) -> int:
    return execute_evaluate_task(args)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orkg-sparql-pipeline",
        description="CLI entry point for the ORKG pipeline."
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)
    query_parser = subparsers.add_parser("query", help="Run the query task.")
    query_parser.add_argument("--model", required=True, help="Model to use for querying.")
    query_parser.add_argument("--prompt-mode", required=False,choices=["empire_compass", "zero_shot", "few_shot"] ,help="Prompt mode to use for querying.")
    query_parser.add_argument("--family", required=False,choices=["nlp4re", "empirical_research_practice"] ,help="Template family to use for querying (e.g., 'nlp4re', 'empirical_research').")
    query_parser.add_argument("--question", required=True, help="The question to query the model with.")
    query_parser.add_argument("--postprocess-pgmr", action="store_true", help="Apply PGMR-lite postprocessing to the generated response.")
    query_parser.add_argument("--restore-pgmr", action="store_true", help="Restore PGMR-lite placeholders to ORKG predicates/classes and print mapped SPARQL.")
    query_parser.add_argument("--pgmr-memory-dir",default="code/data/orkg_memory/templates", help="Directory containing PGMR memory/mapping files.")


    query_parser.set_defaults(func=run_query_task)


    train_parser = subparsers.add_parser("train", help="Run the training task.")
    train_parser.add_argument(
        "--run",
        required=True,
        help="Training run key from train_config.json.",
    )
    train_parser.add_argument(
        "--train-config",
        type=Path,
        default=Path("code/config/train_config.json"),
        help="Path to the training configuration file.",
    )
    train_parser.add_argument(
        "--max-train-samples",
        type=int,
        default=None,
        help="Optional limit for training examples, useful for test runs.",
    )
    train_parser.add_argument(
        "--max-eval-samples",
        type=int,
        default=None,
        help="Optional limit for validation examples, useful for test runs.",
    )
    train_parser.add_argument(
        "--override-epochs",
        type=int,
        default=None,
        help="Override the number of training epochs from train_config.json.",
    )
    train_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare and print training examples without loading a model or training.",
    )
    train_parser.set_defaults(func=run_train_task)

    evaluate_parser = subparsers.add_parser("evaluate", help="Run the evaluation task.")
    evaluate_parser.add_argument("--model", required=True, help="Model to use for evaluation.")
    evaluate_parser.add_argument("--dataset", required=True, help="Dataset to use for evaluation.")
    evaluate_parser.add_argument("--limit", required=False, type=int, help="Use only the first N dataset entries for a test run.")
    evaluate_parser.add_argument( "--prompt-mode",required=False,choices=["empire_compass", "zero_shot", "few_shot", "pgmr_lite_meta"],help="Prompt mode to use for evaluation.")
    evaluate_parser.add_argument("--sparql-endpoint", required=False, default= "https://www.orkg.org/triplestore" ,help="Optional SPARQL endpoint for executing extracted queries.")
    evaluate_parser.add_argument("--prediction-format",required=False,choices=["sparql", "pgmr_lite"],default="sparql",help="Output format generated by the model before execution.",)
    evaluate_parser.add_argument("--pgmr-memory-dir",required=False,default="code/data/orkg_memory/templates",help="Memory directory used to restore PGMR-lite placeholders to ORKG identifiers.",)
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