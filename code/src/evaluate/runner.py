import argparse
from src.evaluate.sparql_extraction import extract_sparql_query
import json
from datetime import datetime, timezone
from src.query.prompt_builder import build_final_prompt_for_question
from src.query.inference_session import (
    generate_response_with_session,
    prepare_inference_session,
)

from src.evaluate.dataset_loader import (
    load_evaluate_entries,
    select_entry_fields,
)
from src.evaluate.run_io import (
    ensure_evaluate_run_dir,
    get_benchmark_raw_output_path,
    build_initial_run_metadata,
    build_raw_result_entry
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
        prompt_mode=args.prompt_mode,
    )

    output_path = get_benchmark_raw_output_path(run_dir)
    started_at_utc = datetime.now(timezone.utc).isoformat()

    run_metadata = build_initial_run_metadata(
        model_name=args.model,
        dataset_path=args.dataset,
        prompt_mode=args.prompt_mode,
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

    inference_session = prepare_inference_session(args.model)
    print(f"Inference provider: {inference_session['provider']}\n")

    results = []

    for index, entry in enumerate(entries, start=1):
        selected = select_entry_fields(
            entry,
            ["uid", "family" ,"question", "gold_sparql"],
        )

        entry_id = selected["uid"] or f"item_{index}"
        question = selected["question"]
        gold_query = selected["gold_sparql"]

        family = selected["family"]

        final_prompt = build_final_prompt_for_question(
            question=question,
            prompt_mode=args.prompt_mode,
            family=family,
        )

        response_started_at = datetime.now(timezone.utc)

        raw_model_output = generate_response_with_session(
            session=inference_session,
            final_prompt=final_prompt,
        )
        extracted_query = extract_sparql_query(raw_model_output)

        response_finished_at = datetime.now(timezone.utc)
        response_time_seconds = (
            response_finished_at - response_started_at
        ).total_seconds()

        result_entry = build_raw_result_entry(
            entry_id=entry_id,
            question=question,
            gold_query=gold_query,
        )
        result_entry["raw_model_output"] = raw_model_output
        result_entry["extracted_query"] = extracted_query
        result_entry["response_time_seconds"] = round(response_time_seconds, 4)

        results.append(result_entry)
        print(f"[{index}/{len(entries)}] family={family} prompt_chars={len(final_prompt)}")

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