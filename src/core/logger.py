"""로깅 시스템."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent.parent / "logs"


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create and configure a logger with console and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    LOG_DIR.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
