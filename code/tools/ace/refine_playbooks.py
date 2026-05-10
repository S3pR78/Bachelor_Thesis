from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ace.orkg.adapter import compact_json
from ace.orkg.refine import refine_playbook_with_llm
from ace.llm import (
    get_max_tokens_from_model_config,
    get_model_id,
    normalize_provider,
    resolve_ace_llm_client,
)
from src.utils.config_loader import load_json_config, get_model_entry


def resolve_model_entry(config_path: str, model_key: str) -> dict[str, Any]:
    full_config = load_json_config(config_path)
    return get_model_entry(full_config, model_key)


def get_provider(model_config: dict[str, Any]) -> str:
    return normalize_provider(model_config.get("provider"))


def get_max_tokens(model_config: dict[str, Any], *, cli_max_tokens: int | None, default: int = 2048) -> int:
    if cli_max_tokens is not None:
        return cli_max_tokens

    return get_max_tokens_from_model_config(model_config, default=default)


def parse_playbook_filename(path: Path) -> tuple[str, str]:
    stem = path.stem
    if "__" not in stem:
        raise ValueError(f"Playbook filename must be <family>__<prediction_format>.txt: {path}")
    family, prediction_format = stem.split("__", 1)
    return family, prediction_format


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LLM refine ORKG ACE playbooks.")
    parser.add_argument("--playbook-dir", default="code/data/ace_playbooks")
    parser.add_argument("--model-key", required=True, help="Generator model key whose playbooks should be refined.")
    parser.add_argument("--refiner-model-key", default="gpt_4o_mini")
    parser.add_argument("--model-config", default="code/config/model_config.json")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--allow-api-calls", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    source_dir = Path(args.playbook_dir) / args.model_key
    out_dir = Path(args.out_dir)
    cleaned_dir = out_dir / "cleaned_playbooks"
    log_dir = out_dir / "llm_logs"

    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    playbook_paths = sorted(source_dir.glob("*.txt"))

    if not playbook_paths:
        raise FileNotFoundError(f"No playbooks found in {source_dir}")

    model_config = resolve_model_entry(args.model_config, args.refiner_model_key)
    provider = get_provider(model_config)

    model_id = get_model_id(model_config, model_key=args.refiner_model_key)
    max_tokens = get_max_tokens(model_config, cli_max_tokens=args.max_tokens)

    planned = {
        "source_dir": str(source_dir),
        "playbook_count": len(playbook_paths),
        "playbooks": [str(path) for path in playbook_paths],
        "refiner_model_key": args.refiner_model_key,
        "refiner_model_id": model_id,
        "provider": provider,
        "estimated_llm_calls": len(playbook_paths),
        "out_dir": str(out_dir),
        "publish": args.publish,
        "max_tokens": max_tokens,
    }

    print("Planned playbook refine:")
    print(compact_json(planned))

    if not args.allow_api_calls:
        print()
        print("DRY RUN ONLY: no LLM calls were made.")
        print("Add --allow-api-calls to run LLM refinement.")
        return 0

    client = resolve_ace_llm_client(args.model_config, args.refiner_model_key)

    reports = []
    for idx, path in enumerate(playbook_paths, start=1):
        family, prediction_format = parse_playbook_filename(path)
        print(f"\n=== Refine {idx}/{len(playbook_paths)}: {path.name} ===")

        playbook_text = path.read_text(encoding="utf-8")

        cleaned_path = cleaned_dir / path.name

        try:
            report = refine_playbook_with_llm(
                playbook_text=playbook_text,
                family=family,
                prediction_format=prediction_format,
                api_client=client,
                api_provider=client.provider,
                model=client.model_id,
                max_tokens=max_tokens,
                call_id=f"refine_{family}_{prediction_format}",
                log_dir=str(log_dir),
            )

            cleaned_path.write_text(report["cleaned_playbook"], encoding="utf-8")

            report_for_json = {
                k: v for k, v in report.items()
                if k not in {"cleaned_playbook", "raw_response"}
            }
            report_for_json["source_path"] = str(path)
            report_for_json["cleaned_path"] = str(cleaned_path)
            report_for_json["status"] = "ok"
            reports.append(report_for_json)

            if args.publish:
                path.write_text(report["cleaned_playbook"], encoding="utf-8")
                report_for_json["published_path"] = str(path)

            print(
                f"rules: {report['original_rule_count']} -> {report['refined_rule_count']} "
                f"(pre_rejections={len(report['pre_rejections'])}, "
                f"post_rejections={len(report['post_rejections'])})"
            )

        except Exception as exc:
            # Keep the pipeline robust: a bad JSON response for one playbook should
            # not discard already-refined playbooks or prevent refining the others.
            cleaned_path.write_text(playbook_text, encoding="utf-8")
            error_report = {
                "source_path": str(path),
                "cleaned_path": str(cleaned_path),
                "family": family,
                "prediction_format": prediction_format,
                "status": "failed_fallback_original",
                "error": str(exc),
            }
            reports.append(error_report)
            print(f"WARNING: refine failed for {path.name}: {exc}")
            print(f"Fallback copied original playbook to {cleaned_path}")

    report_path = out_dir / "refine_report.json"
    report_path.write_text(compact_json(reports), encoding="utf-8")

    print()
    print("Wrote refine report:", report_path)
    print("Cleaned playbooks:", cleaned_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
