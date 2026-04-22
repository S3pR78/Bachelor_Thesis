from __future__ import annotations

import argparse
from pathlib import Path


def read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assemble a dataset expansion prompt from base prompt, wrapper, and run file."
    )
    parser.add_argument(
        "--base-prompt",
        required=True,
        help="Path to the family base prompt file.",
    )
    parser.add_argument(
        "--wrapper-prompt",
        required=True,
        help="Path to the batch wrapper file.",
    )
    parser.add_argument(
        "--run-prompt",
        required=True,
        help="Path to the run file.",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Path to the assembled output prompt file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output file.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    base_prompt_path = Path(args.base_prompt)
    wrapper_prompt_path = Path(args.wrapper_prompt)
    run_prompt_path = Path(args.run_prompt)
    output_path = Path(args.output_file)

    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. Use --overwrite to replace it."
        )

    base_prompt = read_text(base_prompt_path)
    wrapper_prompt = read_text(wrapper_prompt_path)
    run_prompt = read_text(run_prompt_path)

    assembled_prompt = f"""# Assembled Dataset Expansion Prompt

## Family Base Prompt
{base_prompt}

---

## Batch Wrapper Prompt
{wrapper_prompt}

---

## Run Prompt
{run_prompt}
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(assembled_prompt, encoding="utf-8")

    print(f"Assembled prompt written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())