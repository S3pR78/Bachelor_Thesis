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
