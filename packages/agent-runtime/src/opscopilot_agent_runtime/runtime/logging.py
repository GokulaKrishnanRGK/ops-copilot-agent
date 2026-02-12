import logging
import os


def _configure_logging() -> None:
    if os.getenv("AGENT_DEBUG") != "1":
        return
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    _configure_logging()
    return logging.getLogger(name)
