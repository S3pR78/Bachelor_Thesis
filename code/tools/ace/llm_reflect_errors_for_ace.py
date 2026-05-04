from __future__ import annotations

import argparse
from pathlib import Path

from src.ace.llm_reflector import (
    load_trace_report,
    build_llm_reflection_prompt,
    run_llm_reflector,
    save_llm_delta_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use an LLM as ACE Reflector to produce playbook deltas from error traces."
    )
    parser.add_argument("--traces", required=True, help="Path to ace_error_traces.json.")
    parser.add_argument(
        "--reflector-model",
        default="gpt_4o_mini",
        help="OpenAI model config key used as LLM reflector.",
    )
    parser.add_argument("--family", required=True)
    parser.add_argument("--mode", required=True, choices=["pgmr_lite", "direct_sparql", "any"])
    parser.add_argument("--generator-model", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-traces", type=int, default=12)
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument(
        "--save-prompt",
        default=None,
        help="Optional path to save the exact LLM reflector prompt.",
    )
    parser.add_argument(
        "--dry-run-prompt",
        action="store_true",
        help="Only print/save the prompt. Do not call the LLM.",
    )
    return parser.parse_args()


def print_delta_report(report: dict) -> None:
    print("LLM-assisted ACE reflector report")
    print("=" * 80)
    print(f"traces:          {report['source_trace_path']}")
    print(f"reflector model: {report['reflector_model']}")
    print(f"family:          {report['family']}")
    print(f"mode:            {report['mode']}")
    print(f"deltas:          {report['delta_count']}")
    print()

    for delta in report.get("deltas", []):
        bullet = delta["bullet"]
        print("-" * 80)
        print(f"ID:       {bullet['id']}")
        print(f"Category: {bullet['category']}")
        print(f"Priority: {bullet['priority']}")
        print(f"Title:    {bullet['title']}")
        print(f"Rule:     {bullet['content']}")
        if bullet.get("positive_pattern"):
            print(f"Pattern:  {bullet['positive_pattern']}")
        if bullet.get("avoid"):
            print(f"Avoid:    {bullet['avoid']}")
        print(f"Reason:   {delta.get('reason', '')}")


def main() -> None:
    args = parse_args()

    traces_path = Path(args.traces)
    output_path = (
        Path(args.output)
        if args.output
        else traces_path.parent / "ace_deltas_llm.json"
    )

    save_prompt_path = (
        Path(args.save_prompt)
        if args.save_prompt
        else traces_path.parent / "llm_reflector_prompt.txt"
    )

    if args.dry_run_prompt:
        trace_report = load_trace_report(traces_path)
        prompt = build_llm_reflection_prompt(
            trace_report=trace_report,
            trace_path=str(traces_path),
            family=args.family,
            mode=args.mode,
            generator_model=args.generator_model,
            max_traces=args.max_traces,
        )
        save_prompt_path.parent.mkdir(parents=True, exist_ok=True)
        save_prompt_path.write_text(prompt, encoding="utf-8")
        print(prompt)
        print()
        print(f"Saved prompt to: {save_prompt_path}")
        return

    report = run_llm_reflector(
        traces_path=traces_path,
        reflector_model=args.reflector_model,
        family=args.family,
        mode=args.mode,
        generator_model=args.generator_model,
        max_traces=args.max_traces,
        max_output_tokens=args.max_output_tokens,
        temperature=args.temperature,
        save_prompt_path=save_prompt_path,
    )

    save_llm_delta_report(report, output_path)
    print_delta_report(report)
    print()
    print(f"Saved LLM ACE deltas to: {output_path}")
    print(f"Saved LLM prompt to:     {save_prompt_path}")


if __name__ == "__main__":
    main()
