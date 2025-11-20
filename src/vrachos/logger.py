"""Logging functionality."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any


class _ColoredFormatter(logging.Formatter):
    """Formatter with optional ANSI colors and relative timestamps."""

    _start_time = time.monotonic()

    COLORS: dict[str, str] = {
        "RESET": "\u001b[0m",
        "DEBUG": "\u001b[0;36m",  # Cyan
        "INFO": "\u001b[0;32m",  # Green
        "WARNING": "\u001b[0;33m",  # Yellow
        "ERROR": "\u001b[0;31m",  # Red
        "CRITICAL": "\u001b[1;31m",  # Bold Red
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the object."""
        super().__init__(*args, **kwargs)
        # Detect non-TTY to disable colors automatically
        self.enable_colors = sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """
        Override the format method to add color codes to the log messages.

        Adds these custom fields to the log record:
        - rel_secs: relative time since program start (e.g., "12.3456s")
        - color: ANSI color code for the log level
        - reset: ANSI reset code to return to normal colors
        """
        # Total width 10 including 's', right-aligned for neat columns
        record.rel_secs = (
            f"{time.monotonic() - _ColoredFormatter._start_time:.4f}s".rjust(
                10
            )
        )
        if self.enable_colors:
            record.color = self.COLORS.get(record.levelname, "")
            record.reset = self.COLORS["RESET"]
        else:
            record.color = ""
            record.reset = ""
        return super().format(record)


class _Logger(logging.Logger):
    """Rich persistent logger."""

    def __init__(
        self,
        name: str = __name__,
        level: int = logging.NOTSET,
    ) -> None:
        """Initialize the object."""
        super().__init__(name, logging.DEBUG)

        if not self.handlers:
            self.c_handler = logging.StreamHandler()
            self.c_handler.setLevel(level)

            c_format = _ColoredFormatter(
                "[%(color)s%(levelname)-8s%(reset)s]: %(rel_secs)s "
                "%(filename)20s:%(lineno)d - %(message)s"
            )
            self.c_handler.setFormatter(c_format)
            self.addHandler(self.c_handler)

    def setLevel(self, level: int | str) -> None:
        """Set the logger's level threshold."""
        if hasattr(self, "c_handler"):
            self.c_handler.setLevel(level)

    def add(self, log_filepath: Path) -> None:
        """Enable persistent log to given file."""
        try:
            parent = log_filepath.parent
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                f"Cannot create directory {parent}: {exc}"
            ) from exc

        if not os.access(parent, os.W_OK | os.X_OK):
            raise PermissionError(f"Directory not writable: {parent}")

        try:
            handler = logging.FileHandler(log_filepath, encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(
                f"Cannot open log file {log_filepath}: {exc}"
            ) from exc

        handler.setLevel(logging.NOTSET)

        handler.setFormatter(
            logging.Formatter(
                "[%(levelname)-8s]: %(asctime)s "
                "%(filename)20s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        self.addHandler(handler)


# Public module-level logger
logger = _Logger()
