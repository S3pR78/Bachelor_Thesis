import argparse
from pathlib import Path

from src.ace.offline.llm_pipeline import (
    add_arguments as add_ace_llm_arguments,
    execute_llm_assisted_ace,
)
from src.ace.online.cli import (
    add_arguments as add_online_ace_arguments,
    execute_online_ace,
)


def run_query_task(args: argparse.Namespace) -> int:
    """Generate one model response for a single natural-language question.

    This is the quick manual path: build the selected prompt, call the
    configured model, and optionally postprocess/restore PGMR-lite output.
    """
    from src.pgmr.postprocess import postprocess_pgmr_query
    from src.pgmr.restore import restore_pgmr_query
    from src.query.prompt_builder import (
        build_final_prompt_for_question,
        validate_query_args,
    )
    from src.query.query_executor import generate_query_response

    validate_query_args(args)

    final_prompt = build_final_prompt_for_question(
        question=args.question,
        prompt_mode=args.prompt_mode,
        family=args.family,
        ace_playbook_path=getattr(args, "ace_playbook", None),
        ace_playbook_dir=getattr(args, "ace_playbook_dir", None),
        ace_mode=getattr(args, "ace_mode", None),
        ace_max_bullets=getattr(args, "ace_max_bullets", 0),
        model_name=getattr(args, "model", None),
    )

    print("Running query task with args:", args)
    print(f"Final prompt length: {len(final_prompt)} chars")
    print(f"Final prompt rough words: {len(final_prompt.split())}")

    response = generate_query_response(
        model_name=args.model,
        final_prompt=final_prompt,
    )
    print("="*80)
    print("Generated response:", response)

    pgmr_query = response

    # PGMR-lite output often needs cleanup before placeholder restoration.
    if getattr(args, "postprocess_pgmr", False) or getattr(args, "restore_pgmr", False):
        pgmr_query = postprocess_pgmr_query(response)
        print("="*80)
        print("\nPostprocessed PGMR:")
        print(pgmr_query)

    # Restoration maps PGMR placeholders back to ORKG predicates/classes.
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
    """Dispatch a configured training run from train_config.json."""
    from src.train.runner import run_training

    run_training(
        train_config_path=args.train_config,
        run_name=args.run,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        override_epochs=args.override_epochs,
        dry_run=args.dry_run,
    )

    return 0

def run_evaluate_task(args: argparse.Namespace) -> int:
    """Run the benchmark/evaluation pipeline for one model and dataset."""
    from src.evaluate.runner import execute_evaluate_task

    return execute_evaluate_task(args)



def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser and register all workflow subcommands."""
    parser = argparse.ArgumentParser(
        prog="orkg-sparql-pipeline",
        description="CLI entry point for the ORKG pipeline."
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Single-question inference command.
    query_parser = subparsers.add_parser("query", help="Run the query task.")
    query_parser.add_argument("--model", required=True, help="Model to use for querying.")
    query_parser.add_argument(
        "--prompt-mode",
        required=False,
        choices=[
            "empire_compass",
            "empire_compass_mini",
            "pgmr_mini",
            "pgmr",
            "zero_shot",
            "few_shot",
        ],
        help="Prompt mode to use for querying.",
    )
    query_parser.add_argument("--family", required=False,choices=["nlp4re", "empirical_research_practice"] ,help="Template family to use for querying (e.g., 'nlp4re', 'empirical_research').")
    query_parser.add_argument("--question", required=True, help="The question to query the model with.")
    query_parser.add_argument("--postprocess-pgmr", action="store_true", help="Apply PGMR-lite postprocessing to the generated response.")
    query_parser.add_argument("--restore-pgmr", action="store_true", help="Restore PGMR-lite placeholders to ORKG predicates/classes and print mapped SPARQL.")
    query_parser.add_argument("--pgmr-memory-dir",default="code/data/orkg_memory/templates", help="Directory containing PGMR memory/mapping files.")

    # ACE options are optional prompt context controls shared with evaluation.
    query_parser.add_argument(
        "--ace-playbook",
        required=False,
        default=None,
        help="Optional ACE playbook JSON file to prepend as adaptive context.",
    )
    query_parser.add_argument(
        "--ace-playbook-dir",
        required=False,
        default=None,
        help="Optional ACE playbook directory for model/family-aware routing.",
    )
    query_parser.add_argument(
        "--ace-mode",
        required=False,
        choices=["pgmr_lite", "direct_sparql", "any"],
        default=None,
        help="ACE playbook mode to use. Defaults to an inferred mode from prompt-mode.",
    )
    query_parser.add_argument(
        "--ace-max-bullets",
        required=False,
        type=int,
        default=0,
        help="Maximum number of ACE playbook bullets to prepend. 0 disables ACE.",
    )

    query_parser.set_defaults(func=run_query_task)


    # Training command. Actual trainer selection happens in src.train.runner.
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

    # Dataset-level benchmark command with extraction, execution, and metrics.
    evaluate_parser = subparsers.add_parser("evaluate", help="Run the evaluation task.")
    evaluate_parser.add_argument("--model", required=True, help="Model to use for evaluation.")
    evaluate_parser.add_argument("--dataset", required=True, help="Dataset to use for evaluation.")
    evaluate_parser.add_argument("--limit", required=False, type=int, help="Use only the first N dataset entries for a test run.")
    evaluate_parser.add_argument(
        "--prompt-mode",
        required=False,
        choices=[
            "empire_compass",
            "empire_compass_mini",
            "pgmr_mini",
            "pgmr",
            "zero_shot",
            "few_shot",
            "pgmr_lite_meta",
        ],
        help="Prompt mode to use for evaluation.",
    )
    evaluate_parser.add_argument("--sparql-endpoint", required=False, default= "https://www.orkg.org/triplestore" ,help="Optional SPARQL endpoint for executing extracted queries.")
    evaluate_parser.add_argument("--prediction-format",required=False,choices=["sparql", "pgmr_lite"],default="sparql",help="Output format generated by the model before execution.",)
    evaluate_parser.add_argument("--pgmr-memory-dir",required=False,default="code/data/orkg_memory/templates",help="Memory directory used to restore PGMR-lite placeholders to ORKG identifiers.",)
    evaluate_parser.add_argument("--kg-memory-path","--kg_memory_path",dest="kg_memory_path",default="code/data/orkg_memory/templates",help=(
        "Path to local ORKG/PGMR memory used for URI hallucination checks. "
        "Defaults to code/data/orkg_memory/templates."
    ),)

    # ACE can prepend model/family-specific playbook bullets to each prompt.
    evaluate_parser.add_argument(
        "--ace-playbook",
        required=False,
        default=None,
        help="Optional ACE playbook JSON file to prepend as adaptive context.",
    )
    evaluate_parser.add_argument(
        "--ace-playbook-dir",
        required=False,
        default=None,
        help="Optional ACE playbook directory for model/family-aware routing.",
    )
    evaluate_parser.add_argument(
        "--ace-mode",
        required=False,
        choices=["pgmr_lite", "direct_sparql", "any"],
        default=None,
        help="ACE playbook mode to use. Defaults to an inferred mode from prompt-mode.",
    )
    evaluate_parser.add_argument(
        "--ace-max-bullets",
        required=False,
        type=int,
        default=0,
        help="Maximum number of ACE playbook bullets to prepend. 0 disables ACE.",
    )

    evaluate_parser.set_defaults(func=run_evaluate_task)


    # LLM-assisted ACE starts from an existing evaluation run directory.
    ace_llm_parser = subparsers.add_parser(
        "ace-llm",
        help="Run LLM-assisted ACE from an evaluation run directory.",
    )
    add_ace_llm_arguments(ace_llm_parser)
    ace_llm_parser.set_defaults(func=execute_llm_assisted_ace)

    ace_parser = subparsers.add_parser(
        "ace",
        help="Run ACE workflows.",
    )
    ace_subparsers = ace_parser.add_subparsers(
        dest="ace_workflow",
        required=True,
    )

    ace_offline_parser = ace_subparsers.add_parser(
        "offline",
        help="Run offline ACE-style playbook construction.",
    )
    add_ace_llm_arguments(ace_offline_parser)
    ace_offline_parser.set_defaults(func=execute_llm_assisted_ace)

    ace_online_parser = ace_subparsers.add_parser(
        "online",
        help="Run the true per-question online ACE loop.",
    )
    add_online_ace_arguments(ace_online_parser)
    ace_online_parser.set_defaults(func=execute_online_ace)
    
    return parser



def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    result = args.func(args)
    return int(result or 0)



if __name__ == "__main__":
    raise SystemExit(main())
