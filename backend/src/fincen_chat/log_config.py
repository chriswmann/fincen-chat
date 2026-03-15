import logging.config
import os

from pathlib import Path
from typing import Any

import yaml

LOG_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "logging_config.yaml"

LIB_LOG_LEVEL = os.getenv("LIB_LOG_LEVEL")

def read_config(log_config_path: Path) -> dict[str, Any]:
    with open(log_config_path, "r") as fin:
        return yaml.safe_load(fin)


def setup_logging() -> None:
    config = read_config(LOG_CONFIG_PATH)
    log_file = Path(config["handlers"]["file"]["filename"])
    if LIB_LOG_LEVEL is not None:
        level = LIB_LOG_LEVEL.upper()
        config["loggers"]["temporalio"]["level"] = level
        config["loggers"]["pydantic"]["level"] = level
        config["loggers"]["pydantic_ai"]["level"] = level
        config["loggers"]["langfuse"]["level"] = level
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(config=config)
