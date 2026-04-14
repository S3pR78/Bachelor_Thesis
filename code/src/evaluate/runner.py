import argparse
import json
from datetime import datetime, timezone

from src.evaluate.dataset_loader import (
    load_evaluate_entries,
    select_entry_fields,
)
from src.evaluate.result_builder import build_raw_result_entry
from src.evaluate.run_metadata import build_initial_run_metadata
from src.evaluate.run_paths import (
    ensure_evaluate_run_dir,
    get_benchmark_raw_output_path,
)


def execute_evaluate_task(args: argparse.Namespace) -> int:
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

    output_path = get_benchmark_raw_output_path(run_dir)
    started_at_utc = datetime.now(timezone.utc).isoformat()

    run_metadata = build_initial_run_metadata(
        model_name=args.model,
        dataset_path=args.dataset,
        prompt_mode=None,
        requested_limit=args.limit,
        run_dir=run_dir,
        output_path=output_path,
        started_at_utc=started_at_utc,
        total_items=len(entries),
    )

    print(f"Run directory: {run_dir}\n")
    print(f"Raw benchmark output path: {output_path}\n")
    print(f"Run metadata: {run_metadata}\n")
    print(f"Loaded entries for this run: {len(entries)}\n")

    results = []

    for index, entry in enumerate(entries, start=1):
        selected = select_entry_fields(
            entry,
            ["uid", "question", "gold_sparql"],
        )

        entry_id = selected["uid"] or f"item_{index}"
        question = selected["question"]
        gold_query = selected["gold_sparql"]

        result_entry = build_raw_result_entry(
            entry_id=entry_id,
            question=question,
            gold_query=gold_query,
        )

        results.append(result_entry)

        print(f"[{index}/{len(entries)}] result_entry={result_entry}")

    payload = {
        "run_metadata": run_metadata,
        "results": results,
    }

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Collected result entries: {len(results)}")
    print(f"Saved raw benchmark payload to: {output_path}")

    return 0