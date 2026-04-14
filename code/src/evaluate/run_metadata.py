from pathlib import Path


def build_initial_run_metadata(
    model_name: str,
    dataset_path: str,
    prompt_mode: str | None,
    requested_limit: int | None,
    run_dir: Path,
    output_path: Path,
    started_at_utc: str,
    total_items: int,
) -> dict:
    return {
        "model_name": model_name,
        "dataset_path": dataset_path,
        "prompt_mode": prompt_mode,
        "requested_limit": requested_limit,
        "run_dir": str(run_dir),
        "output_path": str(output_path),
        "started_at_utc": started_at_utc,
        "total_items": total_items,
    }