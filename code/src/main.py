import argparse
import sys
from pathlib import Path



def run_query_task(args: argparse.Namespace) -> int:
    """Generate one model response for a single natural-language question.

    This is the quick manual path: build the selected prompt, call the
    configured model, and optionally postprocess/restore PGMR-lite output.
    """
    from src.pgmr.memory_resolver import PgmrResolutionOptions
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
        model_name=getattr(args, "model", None),
        prediction_format=getattr(args, "prediction_format", None),
        ace_playbook_path=getattr(args, "ace_playbook", None),
        ace_playbook_dir=getattr(args, "ace_playbook_dir", None),
        ace_mode=getattr(args, "ace_mode", None),
        ace_max_bullets=getattr(args, "ace_max_bullets", 0),
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
        pgmr_resolution_options = PgmrResolutionOptions(
            enable_similarity_mapping=bool(
                getattr(args, "pgmr_similarity_mapping", False)
            ),
            auto_map_threshold=float(
                getattr(args, "pgmr_auto_map_threshold", 0.90)
            ),
            suggestion_threshold=float(
                getattr(args, "pgmr_suggestion_threshold", 0.75)
            ),
            min_margin=float(getattr(args, "pgmr_min_margin", 0.08)),
        )
        restore_result = restore_pgmr_query(
            pgmr_query=pgmr_query,
            memory_dir=Path(args.pgmr_memory_dir),
            options=pgmr_resolution_options,
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

        if restore_result.alias_mappings:
            print("\nPGMR alias mappings:")
            for mapping in restore_result.alias_mappings:
                print(
                    f"- {mapping['alias']} -> "
                    f"{mapping['mapped_to_placeholder']} "
                    f"({mapping['canonical_uri']})"
                )

        if restore_result.auto_mappings:
            print("\nPGMR automatic similarity mappings:")
            for mapping in restore_result.auto_mappings:
                print(
                    f"- {mapping['missing_placeholder']} -> "
                    f"{mapping['mapped_to_placeholder']} "
                    f"score={mapping['score']}"
                )

        if restore_result.mapping_suggestions:
            print("\nPGMR mapping suggestions:")
            for mapping in restore_result.mapping_suggestions:
                print(
                    f"- {mapping['missing_placeholder']} -> "
                    f"{mapping['candidate_placeholder']} "
                    f"score={mapping['score']}"
                )




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


def _latest_benchmark_raw_files() -> set[str]:
    return {
        str(path)
        for path in Path("code/outputs/evaluation_runs").glob("**/benchmark_raw.json")
    }


def _detect_new_benchmark_raw_path(before: set[str]) -> Path:
    after = _latest_benchmark_raw_files()
    new_paths = sorted(after - before)
    if new_paths:
        return Path(new_paths[-1])

    all_paths = sorted(after)
    if not all_paths:
        raise FileNotFoundError("No benchmark_raw.json found after evaluation.")
    return Path(all_paths[-1])


def _namespace_to_cli_args(args: argparse.Namespace, argument_names: list[str]) -> list[str]:
    cli_args: list[str] = []
    for name in argument_names:
        value = getattr(args, name, None)
        if value is None or value is False:
            continue

        option = f"--{name.replace('_', '-')}"
        if value is True:
            cli_args.append(option)
        else:
            cli_args.extend([option, str(value)])
    return cli_args


def _run_tool_main(module_name: str, argv: list[str]) -> int:
    import importlib

    module = importlib.import_module(module_name)
    previous_argv = sys.argv[:]
    try:
        sys.argv = [module_name, *argv]
        return int(module.main() or 0)
    finally:
        sys.argv = previous_argv


def run_ace_offline_warmup_task(args: argparse.Namespace) -> int:
    """Run ORKG ACE offline warmup, optionally evaluating a dataset first."""
    if bool(args.raw_path) == bool(args.dataset):
        raise ValueError("Exactly one of --raw-path or --dataset must be provided.")

    raw_path = Path(args.raw_path) if args.raw_path else None

    if args.dataset:
        missing = [
            name
            for name in ("generator_model_key", "prompt_mode", "prediction_format")
            if not getattr(args, name, None)
        ]
        if missing:
            joined = ", ".join(f"--{name.replace('_', '-')}" for name in missing)
            raise ValueError(f"--dataset mode requires: {joined}")

        evaluate_args = argparse.Namespace(
            model=args.generator_model_key,
            dataset=args.dataset,
            limit=args.evaluate_limit,
            prompt_mode=args.prompt_mode,
            sparql_endpoint=args.sparql_endpoint,
            prediction_format=args.prediction_format,
            postprocess_pgmr=args.postprocess_pgmr,
            pgmr_memory_dir=args.pgmr_memory_dir,
            pgmr_similarity_mapping=args.pgmr_similarity_mapping,
            pgmr_auto_map_threshold=args.pgmr_auto_map_threshold,
            pgmr_suggestion_threshold=args.pgmr_suggestion_threshold,
            pgmr_min_margin=args.pgmr_min_margin,
            kg_memory_path=args.kg_memory_path,
            ace_playbook=None,
            ace_playbook_dir=None,
            ace_mode=None,
            ace_max_bullets=0,
        )

        before = _latest_benchmark_raw_files()
        result = run_evaluate_task(evaluate_args)
        if result != 0:
            return result
        raw_path = _detect_new_benchmark_raw_path(before)
        print(f"Detected benchmark_raw.json for offline warmup: {raw_path}")

    if raw_path is None:
        raise ValueError("Could not resolve raw input path for offline warmup.")

    tool_args = [
        "--raw-path",
        str(raw_path),
        *_namespace_to_cli_args(
            args,
            [
                "generator_model_key",
                "reflector_model_key",
                "curator_model_key",
                "model_config",
                "out_dir",
                "playbook_dir",
                "limit",
                "token_budget",
                "max_tokens",
                "include_correct",
                "no_publish_playbooks",
                "allow_api_calls",
            ],
        ),
    ]
    return _run_tool_main("tools.ace.run_offline_warmup", tool_args)


def run_ace_online_task(args: argparse.Namespace) -> int:
    """Dispatch ORKG Online ACE through the existing tool wrapper."""
    tool_args = _namespace_to_cli_args(
        args,
        [
            "dataset",
            "generator_model_key",
            "prompt_mode",
            "prediction_format",
            "online_mode",
            "initial_playbook_dir",
            "out_dir",
            "planner_model_key",
            "reflector_model_key",
            "curator_model_key",
            "refiner_model_key",
            "model_config",
            "limit",
            "top_k_rules",
            "disable_planner",
            "ace_max_bullets",
            "max_attempts",
            "refine_every_accepted",
            "sparql_endpoint",
            "pgmr_memory_dir",
            "pgmr_similarity_mapping",
            "no_pgmr_similarity_mapping",
            "max_tokens",
            "publish_final_playbooks",
            "allow_api_calls",
        ],
    )
    return _run_tool_main("tools.ace.run_online_ace", tool_args)


def run_ace_refine_playbooks_task(args: argparse.Namespace) -> int:
    """Dispatch ORKG ACE playbook refinement through the existing tool wrapper."""
    tool_args = _namespace_to_cli_args(
        args,
        [
            "playbook_dir",
            "model_key",
            "refiner_model_key",
            "model_config",
            "out_dir",
            "max_tokens",
            "publish",
            "allow_api_calls",
        ],
    )
    return _run_tool_main("tools.ace.refine_playbooks", tool_args)


def add_ace_parser(subparsers: argparse._SubParsersAction) -> None:
    ace_parser = subparsers.add_parser("ace", help="Run ORKG ACE workflows.")
    ace_subparsers = ace_parser.add_subparsers(dest="ace_command", required=True)

    offline_parser = ace_subparsers.add_parser(
        "offline-warmup",
        help="Build offline ACE warmup playbooks from benchmark_raw.json or a dataset.",
    )
    offline_input = offline_parser.add_mutually_exclusive_group(required=True)
    offline_input.add_argument("--raw-path", default=None)
    offline_input.add_argument("--dataset", default=None)
    offline_parser.add_argument("--generator-model-key", required=True)
    offline_parser.add_argument("--reflector-model-key", required=True)
    offline_parser.add_argument("--curator-model-key", required=True)
    offline_parser.add_argument("--prompt-mode", default=None)
    offline_parser.add_argument("--prediction-format", choices=["sparql", "pgmr_lite"], default=None)
    offline_parser.add_argument("--sparql-endpoint", default="https://www.orkg.org/triplestore")
    offline_parser.add_argument("--postprocess-pgmr", action="store_true")
    offline_parser.add_argument("--pgmr-memory-dir", default="code/data/orkg_memory/templates")
    offline_parser.add_argument("--pgmr-similarity-mapping", action="store_true")
    offline_parser.add_argument("--pgmr-auto-map-threshold", type=float, default=0.90)
    offline_parser.add_argument("--pgmr-suggestion-threshold", type=float, default=0.75)
    offline_parser.add_argument("--pgmr-min-margin", type=float, default=0.08)
    offline_parser.add_argument("--kg-memory-path", "--kg_memory_path", dest="kg_memory_path", default="code/data/orkg_memory/templates")
    offline_parser.add_argument("--evaluate-limit", type=int, default=None)
    offline_parser.add_argument("--model-config", default="code/config/model_config.json")
    offline_parser.add_argument("--out-dir", required=True)
    offline_parser.add_argument("--playbook-dir", default="code/data/ace_playbooks")
    offline_parser.add_argument("--limit", type=int, default=None)
    offline_parser.add_argument("--include-correct", action="store_true")
    offline_parser.add_argument("--token-budget", type=int, default=4000)
    offline_parser.add_argument("--max-tokens", type=int, default=None)
    offline_parser.add_argument("--no-publish-playbooks", action="store_true")
    offline_parser.add_argument("--allow-api-calls", action="store_true")
    offline_parser.set_defaults(func=run_ace_offline_warmup_task)

    online_parser = ace_subparsers.add_parser("online", help="Run ORKG Online ACE.")
    online_parser.add_argument("--dataset", required=True)
    online_parser.add_argument("--generator-model-key", required=True)
    online_parser.add_argument("--prompt-mode", required=True)
    online_parser.add_argument("--prediction-format", required=True, choices=["pgmr_lite", "sparql"])
    online_parser.add_argument("--online-mode", required=True, choices=["playbook_refinement", "test_time_repair"])
    online_parser.add_argument("--initial-playbook-dir", default="code/data/ace_playbooks")
    online_parser.add_argument("--out-dir", required=True)
    online_parser.add_argument("--planner-model-key", default="gpt_4o_mini")
    online_parser.add_argument("--reflector-model-key", default="gpt_4o_mini")
    online_parser.add_argument("--curator-model-key", default="gpt_4o_mini")
    online_parser.add_argument(
        "--refiner-model-key",
        default="gpt_4o_mini",
        help="Model key used for periodic grow-and-refine cleanup during playbook_refinement.",
    )
    online_parser.add_argument("--model-config", default="code/config/model_config.json")
    online_parser.add_argument("--limit", type=int, default=None)
    online_parser.add_argument("--top-k-rules", type=int, default=8)
    online_parser.add_argument(
        "--disable-planner",
        action="store_true",
        default=False,
        help="Disable LLM planner and retrieve top-k rules using only the question.",
    )
    online_parser.add_argument("--ace-max-bullets", type=int, default=-1)
    online_parser.add_argument("--max-attempts", type=int, default=2)
    online_parser.add_argument(
        "--refine-every-accepted",
        type=int,
        default=0,
        help="Run LLM playbook refinement after every N accepted rules. 0 disables periodic refinement.",
    )
    online_parser.add_argument("--sparql-endpoint", default="https://www.orkg.org/triplestore")
    online_parser.add_argument("--pgmr-memory-dir", default="code/data/orkg_memory/templates")
    online_parser.add_argument("--pgmr-similarity-mapping", action="store_true", default=True)
    online_parser.add_argument("--no-pgmr-similarity-mapping", dest="no_pgmr_similarity_mapping", action="store_true")
    online_parser.add_argument("--max-tokens", type=int, default=None)
    online_parser.add_argument("--publish-final-playbooks", action="store_true")
    online_parser.add_argument("--allow-api-calls", action="store_true")
    online_parser.set_defaults(func=run_ace_online_task)

    refine_parser = ace_subparsers.add_parser("refine-playbooks", help="LLM-refine ORKG ACE playbooks.")
    refine_parser.add_argument("--playbook-dir", default="code/data/ace_playbooks")
    refine_parser.add_argument("--model-key", required=True)
    refine_parser.add_argument("--refiner-model-key", default="gpt_4o_mini")
    refine_parser.add_argument("--model-config", default="code/config/model_config.json")
    refine_parser.add_argument("--out-dir", required=True)
    refine_parser.add_argument("--max-tokens", type=int, default=None)
    refine_parser.add_argument("--publish", action="store_true")
    refine_parser.add_argument("--allow-api-calls", action="store_true")
    refine_parser.set_defaults(func=run_ace_refine_playbooks_task)



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
    query_parser.add_argument("--pgmr-similarity-mapping", action="store_true", help="Enable conservative PGMR similarity mapping during restore.")
    query_parser.add_argument("--pgmr-auto-map-threshold", type=float, default=0.90, help="Minimum score for automatic PGMR similarity mapping.")
    query_parser.add_argument("--pgmr-suggestion-threshold", type=float, default=0.75, help="Minimum score for PGMR manual mapping suggestions.")
    query_parser.add_argument("--pgmr-min-margin", type=float, default=0.08, help="Minimum score margin over the second PGMR similarity candidate.")

    query_parser.add_argument(
        "--prediction-format",
        required=False,
        choices=["sparql", "pgmr_lite"],
        default=None,
        help="Prediction format used for ACE playbook routing in query mode.",
    )
    query_parser.add_argument(
        "--ace-playbook",
        "--ace-playbook-path",
        dest="ace_playbook",
        required=False,
        default=None,
        help="Optional ACE playbook file to prepend as adaptive context.",
    )
    query_parser.add_argument(
        "--ace-playbook-dir",
        required=False,
        default=None,
        help="Optional ACE playbook directory for model/family/format-aware routing.",
    )
    query_parser.add_argument(
        "--ace-mode",
        required=False,
        choices=["pgmr_lite", "direct_sparql", "sparql", "any"],
        default=None,
        help="ACE playbook mode to use. Defaults to prediction-format/prompt-mode inference.",
    )
    query_parser.add_argument(
        "--ace-max-bullets",
        required=False,
        type=int,
        default=0,
        help="Maximum number of ACE playbook bullets to prepend. 0 disables ACE; negative means all.",
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
    evaluate_parser.add_argument("--postprocess-pgmr", action="store_true", help="Apply PGMR-lite postprocessing before restore/execution.")
    evaluate_parser.add_argument("--pgmr-memory-dir",required=False,default="code/data/orkg_memory/templates",help="Memory directory used to restore PGMR-lite placeholders to ORKG identifiers.",)
    evaluate_parser.add_argument("--pgmr-similarity-mapping", action="store_true", help="Enable conservative PGMR similarity mapping during restore.")
    evaluate_parser.add_argument("--pgmr-auto-map-threshold", type=float, default=0.90, help="Minimum score for automatic PGMR similarity mapping.")
    evaluate_parser.add_argument("--pgmr-suggestion-threshold", type=float, default=0.75, help="Minimum score for PGMR manual mapping suggestions.")
    evaluate_parser.add_argument("--pgmr-min-margin", type=float, default=0.08, help="Minimum score margin over the second PGMR similarity candidate.")
    evaluate_parser.add_argument("--kg-memory-path","--kg_memory_path",dest="kg_memory_path",default="code/data/orkg_memory/templates",help=(
        "Path to local ORKG/PGMR memory used for URI hallucination checks. "
        "Defaults to code/data/orkg_memory/templates."
    ),)

    evaluate_parser.add_argument(
        "--ace-playbook",
        "--ace-playbook-path",
        dest="ace_playbook",
        required=False,
        default=None,
        help="Optional ACE playbook file to prepend as adaptive context.",
    )
    evaluate_parser.add_argument(
        "--ace-playbook-dir",
        required=False,
        default=None,
        help="Optional ACE playbook directory for model/family/format-aware routing.",
    )
    evaluate_parser.add_argument(
        "--ace-mode",
        required=False,
        choices=["pgmr_lite", "direct_sparql", "sparql", "any"],
        default=None,
        help="ACE playbook mode to use. Defaults to prediction-format/prompt-mode inference.",
    )
    evaluate_parser.add_argument(
        "--ace-max-bullets",
        required=False,
        type=int,
        default=0,
        help="Maximum number of ACE playbook bullets to prepend. 0 disables ACE; negative means all.",
    )

    evaluate_parser.set_defaults(func=run_evaluate_task)

    add_ace_parser(subparsers)
    
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
