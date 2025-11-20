#!/usr/bin/env python

"""Main entry point."""

from pathlib import Path

from vrachos.configuration import Configuration
from vrachos.core.io import random_temp_file_path
from vrachos.logger import logger
from vrachos.ui import UI


class AppConfig(Configuration):
    """Custom configuration."""

    FILEPATH = Path(random_temp_file_path(suffix="json"))
    debug: bool = False
    timeout: int = 30


def main() -> None:
    """Entrypoint."""
    UI.init()

    print("Test logger")
    log_filepath = random_temp_file_path(suffix="log")
    logger.add(log_filepath)
    logger.debug(f"logger filepath = {log_filepath}")
    logger.debug("Hello")
    logger.info("Hello")
    logger.warning("Hello")
    logger.error("Hello")
    logger.critical("Hello")

    print("Test configuration")
    config = AppConfig()
    config.load()  # Load from file or create with defaults
    config.debug = True
    config.save()  # Atomically write to file
    logger.debug(f"AppConfig filepath = {AppConfig.FILEPATH}")


if __name__ == "__main__":
    main()
