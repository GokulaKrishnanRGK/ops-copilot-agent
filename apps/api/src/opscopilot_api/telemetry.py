from opscopilot_observability import configure_telemetry as _configure_shared_telemetry


def configure_telemetry() -> None:
    _configure_shared_telemetry(service_name="ops-copilot-api")
