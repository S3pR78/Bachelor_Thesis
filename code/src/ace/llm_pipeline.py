from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


FAMILIES = [
    "nlp4re",
    "empirical_research_practice",
]


def run_command(cmd: list[str]) -> None:
    print("\n$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def print_rules(deltas_path: Path) -> None:
    if not deltas_path.exists():
        print(f"No deltas found: {deltas_path}")
        return

    rules = load_json(deltas_path)

    if not isinstance(rules, list):
        print("Deltas file is not a JSON array.")
        return

    print("\nGenerated candidate rules:")
    print("=" * 80)

    if not rules:
        print("(no rules)")
        return

    for i, rule in enumerate(rules, start=1):
        print(f"\n[{i}] {rule.get('title')}")
        print(f"    category: {rule.get('category')}")
        print(f"    priority: {rule.get('priority')}")
        print(f"    content:  {rule.get('content')}")
        avoid = rule.get("avoid")
        if avoid:
            print(f"    avoid:    {avoid}")
        evidence = rule.get("evidence_item_ids") or []
        print(f"    evidence: {', '.join(map(str, evidence)) if evidence else '-'}")

    print("\n" + "=" * 80)


def ask_review_action(family: str, deltas_path: Path, default_action: str) -> str:
    if default_action != "ask":
        return default_action

    while True:
        print()
        print(f"Review family: {family}")
        print(f"Deltas file: {deltas_path}")
        print("Choose:")
        print("  y    = import all candidate rules")
        print("  n    = import nothing for this family")
        print("  edit = open JSON file, edit manually, then import")
        print("  show = show rules again")
        print("  skip = skip this family")

        choice = input("Your choice [y/n/edit/show/skip]: ").strip().lower()

        if choice in {"y", "yes"}:
            return "yes"
        if choice in {"n", "no"}:
            return "no"
        if choice in {"edit", "e"}:
            return "edit"
        if choice in {"skip", "s"}:
            return "skip"
        if choice == "show":
            print_rules(deltas_path)
            continue

        print("Invalid choice. Please enter y, n, edit, show, or skip.")


def edit_file(path: Path) -> None:
    editor = os.environ.get("EDITOR", "nano")
    print(f"\nOpening editor: {editor} {path}")
    subprocess.run([editor, str(path)], check=True)


def validate_deltas(path: Path) -> None:
    data = load_json(path)

    if not isinstance(data, list):
        raise ValueError(f"Deltas must be a JSON array: {path}")

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Rule at index {i} is not an object.")
        if not item.get("title"):
            raise ValueError(f"Rule at index {i} has no title.")
        if not item.get("content"):
            raise ValueError(f"Rule at index {i} has no content.")

    print(f"Validated {len(data)} rule(s): {path}")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Evaluation run directory containing benchmark_raw.json.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Local model key, e.g. qwen25_coder_7b_instruct.",
    )
    parser.add_argument(
        "--mode",
        default="pgmr_lite",
        choices=["pgmr_lite", "direct_sparql", "any"],
        help="ACE mode used for trace building and playbook routing.",
    )
    parser.add_argument(
        "--playbook-dir",
        type=Path,
        default=Path("code/data/ace_playbooks"),
        help="Root directory containing model-specific ACE playbooks.",
    )
    parser.add_argument(
        "--llm-model",
        default="gpt-4o-mini",
        help="OpenAI model used as LLM-assisted reflector.",
    )
    parser.add_argument(
        "--max-traces",
        type=int,
        default=20,
        help="Maximum number of traces per family passed to the LLM reflector.",
    )
    parser.add_argument(
        "--max-rules",
        type=int,
        default=8,
        help="Maximum number of candidate rules requested from the LLM reflector.",
    )
    parser.add_argument(
        "--max-new-rules",
        type=int,
        default=5,
        help="Maximum number of rules imported into each playbook.",
    )
    parser.add_argument(
        "--review",
        choices=["ask", "yes", "no", "edit", "skip"],
        default="ask",
        help=(
            "Review behavior after LLM deltas are generated. "
            "ask = interactive, yes = import all, no = import none, "
            "edit = always open editor before import, skip = skip imports."
        ),
    )
    parser.add_argument(
        "--skip-trace-build",
        action="store_true",
        help="Do not rebuild ace_error_traces.json if it already exists.",
    )


def execute_llm_assisted_ace(args: argparse.Namespace) -> None:
    raw_path = args.run_dir / "benchmark_raw.json"
    trace_path = args.run_dir / "ace_error_traces.json"

    if not raw_path.exists():
        raise FileNotFoundError(f"Missing benchmark_raw.json: {raw_path}")

    print("=== LLM-assisted ACE pipeline ===")
    print("run_dir:", args.run_dir)
    print("model:", args.model)
    print("mode:", args.mode)
    print("raw:", raw_path)
    print("traces:", trace_path)
    print("playbook_dir:", args.playbook_dir)
    print("llm_model:", args.llm_model)
    print("review:", args.review)

    if args.skip_trace_build and trace_path.exists():
        print("\nSkipping trace build because --skip-trace-build was set.")
    else:
        run_command(
            [
                sys.executable,
                "code/tools/ace/inspect_errors_for_ace.py",
                "--raw",
                str(raw_path),
                "--mode",
                args.mode,
                "--output",
                str(trace_path),
                "--max-examples",
                "5",
            ]
        )

    for family in FAMILIES:
        playbook_path = (
            args.playbook_dir
            / args.model
            / f"{family}_{args.mode}_playbook.json"
        )

        if not playbook_path.exists():
            print(f"\nSKIP {family}: playbook not found: {playbook_path}")
            continue

        deltas_path = args.run_dir / f"ace_llm_deltas_{family}.json"
        prompt_path = args.run_dir / f"llm_reflector_prompt_{family}.txt"

        print("\n" + "#" * 80)
        print("Family:", family)
        print("Playbook:", playbook_path)
        print("Deltas:", deltas_path)
        print("#" * 80)

        run_command(
            [
                sys.executable,
                "code/tools/ace/llm_reflect_errors_for_ace.py",
                "--error-traces",
                str(trace_path),
                "--current-playbook",
                str(playbook_path),
                "--family",
                family,
                "--mode",
                args.mode,
                "--local-model",
                args.model,
                "--llm-model",
                args.llm_model,
                "--max-traces",
                str(args.max_traces),
                "--max-rules",
                str(args.max_rules),
                "--output",
                str(deltas_path),
                "--save-prompt",
                str(prompt_path),
            ]
        )

        print_rules(deltas_path)

        action = ask_review_action(family, deltas_path, args.review)

        if action in {"no", "skip"}:
            print(f"Not importing rules for {family}.")
            continue

        if action == "edit":
            edit_file(deltas_path)
            validate_deltas(deltas_path)

        if action == "yes":
            validate_deltas(deltas_path)

        run_command(
            [
                sys.executable,
                "code/tools/ace/import_llm_deltas_to_playbook.py",
                "--playbook",
                str(playbook_path),
                "--deltas",
                str(deltas_path),
                "--family",
                family,
                "--mode",
                args.mode,
                "--max-new-rules",
                str(args.max_new_rules),
            ]
        )

    print("\nDone.")
    print("Next step: run evaluation with --ace-playbook-dir and compare against the original run.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLM-assisted ACE from benchmark_raw.json to updated playbooks."
    )
    add_arguments(parser)
    args = parser.parse_args()
    execute_llm_assisted_ace(args)


if __name__ == "__main__":
    main()
