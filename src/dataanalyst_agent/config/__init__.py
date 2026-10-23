from pathlib import Path
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def read_config_file() -> dict:
    config_path =  DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {config_path.resolve()}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
