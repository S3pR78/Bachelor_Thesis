from datetime import datetime, timezone
from pathlib import Path

from src.utils.config_loader import get_configured_path


def make_safe_name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Value must be a non-empty string.")
    
    return "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in value.strip()
    )


def get_dataset_stem(dataset_path: str) -> str:
    path = Path(dataset_path)
    
    if not path.name:
        raise ValueError(f"Invalid dataset path: {dataset_path}")
    
    return path.stem


def build_evaluate_run_dir(
        model_name: str,
        dataset_path: str,
        prompt_mode: str | None,
) -> Path:
    base_dir = get_configured_path("evaluation_runs")

    safe_model_name = make_safe_name(model_name)
    safe_prompt_mode = make_safe_name(prompt_mode or "default")
    safe_dataset_name = make_safe_name(get_dataset_stem(dataset_path))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    return(
        base_dir
        / safe_model_name
        / f"{safe_prompt_mode}__{safe_dataset_name}__{timestamp}"
    )



def ensure_evaluate_run_dir(
        model_name: str,
        dataset_path: str,
        prompt_mode: str | None,
) -> Path:
    run_dir = build_evaluate_run_dir(
        model_name=model_name,
        dataset_path=dataset_path,
        prompt_mode=prompt_mode,
    )

    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir

def get_benchmark_raw_output_path(run_dir: Path) -> Path:
    if not isinstance(run_dir, Path):
        raise ValueError("run_dir must be a pathlib.Path instance.")

    return run_dir / "benchmark_raw.json"