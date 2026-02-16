from __future__ import annotations

import logging
import os

from opscopilot_observability import (
    clear_log_context,
    configure_json_logging,
    configure_telemetry,
    set_log_context,
)


def _configure_logging() -> None:
    configure_telemetry(default_service_name="ops-copilot-agent-runtime")
    configure_json_logging(
        service_name="agent-runtime",
        level=os.getenv("LOG_LEVEL", "INFO"),
        root_config_attr="_opscopilot_agent_configured",
    )


def get_logger(name: str) -> logging.Logger:
    _configure_logging()
    return logging.getLogger(name)


__all__ = ["clear_log_context", "get_logger", "set_log_context"]
