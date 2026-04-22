from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.evaluate.dataset_loader import get_dataset_entries
from src.sparql.execution import detect_sparql_query_type, execute_sparql_query
from src.sparql.prefixes import prepend_orkg_prefixes


def load_dataset_object(input_path: Path) -> object:
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_entry_label(entry: dict, index: int) -> str:
    if not isinstance(entry, dict):
        return f"item_{index}"
    return str(entry.get("uid") or entry.get("id") or f"item_{index}")


def enrich_entry_with_gold_result(
    entry: dict,
    endpoint_url: str,
    timeout_seconds: int,
) -> str:
    if not isinstance(entry, dict):
        raise ValueError("Each dataset entry must be a dictionary.")

    gold_query = entry.get("gold_sparql")
    executed_at_utc = datetime.now(timezone.utc).isoformat()

    if not isinstance(gold_query, str) or not gold_query.strip():
        entry["gold_query_execution"] = {
            "status": "skipped",
            "reason": "missing_gold_sparql",
            "endpoint": endpoint_url,
            "executed_at_utc": executed_at_utc,
        }
        return "skipped"

    query_with_prefixes = prepend_orkg_prefixes(gold_query)
    query_type = detect_sparql_query_type(query_with_prefixes)

    if query_type not in {"select", "ask"}:
        entry["gold_query_execution"] = {
            "status": "skipped",
            "reason": f"unsupported_query_type:{query_type}",
            "endpoint": endpoint_url,
            "executed_at_utc": executed_at_utc,
            "result_type": query_type,
            "query_with_prefixes": query_with_prefixes,
        }
        return "skipped"

    try:
        response_json = execute_sparql_query(
            query=query_with_prefixes,
            endpoint_url=endpoint_url,
            timeout_seconds=timeout_seconds,
        )

        entry["gold_query_execution"] = {
            "status": "ok",
            "endpoint": endpoint_url,
            "executed_at_utc": executed_at_utc,
            "result_type": query_type,
            "query_with_prefixes": query_with_prefixes,
            "response_json": response_json,
        }
        return "ok"

    except Exception as exc:
        entry["gold_query_execution"] = {
            "status": "error",
            "endpoint": endpoint_url,
            "executed_at_utc": executed_at_utc,
            "result_type": query_type,
            "query_with_prefixes": query_with_prefixes,
            "error": str(exc),
        }
        return "error"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enrich_dataset_with_gold_results",
        description="Execute gold SPARQL queries and store the results in a new dataset file.",
    )
    parser.add_argument("--input", required=True, help="Input dataset JSON path.")
    parser.add_argument("--output", required=True, help="Output dataset JSON path.")
    parser.add_argument("--endpoint", required=True, help="SPARQL endpoint URL.")
    parser.add_argument(
        "--limit",
        required=False,
        type=int,
        help="Only enrich the first N entries for a test run.",
    )
    parser.add_argument(
        "--timeout-seconds",
        required=False,
        type=int,
        default=60,
        help="HTTP timeout for SPARQL requests.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    dataset_obj = load_dataset_object(input_path)
    entries = get_dataset_entries(dataset_obj)

    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("limit must be a positive integer.")
        entries_to_process = entries[: args.limit]
    else:
        entries_to_process = entries

    ok_count = 0
    error_count = 0
    skipped_count = 0

    print(f"Loaded entries: {len(entries)}")
    print(f"Processing entries: {len(entries_to_process)}")
    print(f"SPARQL endpoint: {args.endpoint}")

    for index, entry in enumerate(entries_to_process, start=1):
        entry_label = build_entry_label(entry, index)
        status = enrich_entry_with_gold_result(
            entry=entry,
            endpoint_url=args.endpoint,
            timeout_seconds=args.timeout_seconds,
        )

        if status == "ok":
            ok_count += 1
        elif status == "error":
            error_count += 1
        else:
            skipped_count += 1

        print(f"[{index}/{len(entries_to_process)}] id={entry_label} status={status}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(dataset_obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nFinished gold query enrichment.")
    print(f"ok={ok_count} error={error_count} skipped={skipped_count}")
    print(f"Saved enriched dataset to: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())