"""Central logging setup for PawPal+."""

import logging
from pathlib import Path


def setup_logging(log_file: str = "pawpal_execution.log", level: int = logging.INFO) -> None:
    """Set up root logging handlers once for console and file output."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_path = Path(log_file)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
