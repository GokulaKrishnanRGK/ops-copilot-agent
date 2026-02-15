from __future__ import annotations

import os

from opscopilot_observability import (
    clear_log_context,
    configure_json_logging,
    reset_log_context,
    set_log_context,
)


def configure_logging() -> None:
    configure_json_logging(
        service_name="api",
        level=os.getenv("LOG_LEVEL", "INFO"),
        root_config_attr="_opscopilot_configured",
        log_file=os.getenv("API_LOG_FILE"),
        require_log_file=True,
        backup_count=14,
    )


__all__ = [
    "clear_log_context",
    "configure_logging",
    "reset_log_context",
    "set_log_context",
]
