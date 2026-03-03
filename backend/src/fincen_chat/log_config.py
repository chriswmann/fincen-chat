import logging.config

from pathlib import Path
from typing import Any

import yaml

LOG_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "logging_config.yaml"


def read_config(log_config_path: Path) -> dict[str, Any]:
    with open(log_config_path, "r") as fin:
        return yaml.safe_load(fin)


def setup_logging() -> None:
    config = read_config(LOG_CONFIG_PATH)
    log_file = Path(config["handlers"]["file"]["filename"])
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(config=config)
