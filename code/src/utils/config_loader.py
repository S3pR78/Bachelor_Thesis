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