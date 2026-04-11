import json
from pathlib import Path


def load_json_config(config_path: str | Path) -> dict:
    """Load a JSON configuration file."""
    config_path = Path(config_path)
    
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config


def get_repo_root() -> Path:
    """Get the root directory of the repository."""
    return Path(__file__).resolve().parents[3]


def get_path_config_path() -> Path:
    """Get the path to the path configuration file."""
    return get_repo_root() / "code" / "config" / "path_config.json"



def get_configured_path(key: str) -> Path:
    """Get the configured path for a given key from the path configuration file."""
    config = load_json_config(str(get_path_config_path()))

    if key not in config:
        raise KeyError(f"Key '{key}' not found in path configuration.")
    
    value = config[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Configured path for key '{key}' must be a non-empty string")
    
    return (get_repo_root() / value.strip()).resolve()



def get_model_entry(config: dict, model_selector: str) -> dict:
    """
    Returns a single model entry from the multi-model configuration.

    The selector may either be:
    - the model config key (e.g. "t5_base"), or
    - the model_id value (e.g. "google-t5/t5-base").
    """
    models = config.get("models")

    if not isinstance(models, dict) or not models:
        raise ValueError("Model configuration must contain a non-empty 'models' object.")

    if not isinstance(model_selector, str) or not model_selector.strip():
        raise ValueError("model_selector must be a non-empty string.")

    selector = model_selector.strip().lower()

    if selector in models:
        model_entry = models[selector]
        if not isinstance(model_entry, dict):
            raise ValueError(f"Model entry '{selector}' must be a dictionary.")
        return model_entry

    matching_entries = []

    for model_key, model_entry in models.items():
        if not isinstance(model_entry, dict):
            raise ValueError(f"Model entry '{model_key}' must be a dictionary.")

        if model_entry.get("model_id") == selector:
            matching_entries.append((model_key, model_entry))

    if len(matching_entries) == 1:
        return matching_entries[0][1]

    if len(matching_entries) > 1:
        matching_keys = ", ".join(model_key for model_key, _ in matching_entries)
        raise ValueError(
            f"Model selector '{selector}' is ambiguous. Matching model keys: {matching_keys}"
        )

    available_keys = ", ".join(sorted(models.keys()))
    available_model_ids = ", ".join(
        sorted(
            model_entry.get("model_id", "")
            for model_entry in models.values()
            if isinstance(model_entry, dict) and model_entry.get("model_id")
        )
    )

    raise ValueError(
        f"Unknown model selector '{selector}'. "
        f"Available model keys: {available_keys}. "
        f"Available model_ids: {available_model_ids}"
    )