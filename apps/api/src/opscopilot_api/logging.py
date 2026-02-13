import logging
import os
import time
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_opscopilot_configured", False):
        return

    level = os.getenv("API_LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("API_LOG_FILE")
    if not log_file:
        raise RuntimeError("API_LOG_FILE is required")
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s service=api level=%(levelname)s thread_id=%(thread)d logger=%(name)s msg=%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    formatter.converter = time.localtime

    file_handler = TimedRotatingFileHandler(
        filename=str(log_path),
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
        utc=False,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    root.setLevel(level)
    setattr(root, "_opscopilot_configured", True)
