import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

_instrumented_engine_ids: set[int] = set()
_engine: Engine | None = None


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    return url


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    engine = create_engine(get_database_url(), pool_pre_ping=True)
    _instrument_engine(engine)
    _engine = engine
    return _engine


def get_sessionmaker():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def _instrument_engine(engine: Engine) -> None:
    engine_id = id(engine)
    if engine_id in _instrumented_engine_ids:
        return
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    except ModuleNotFoundError:
        if endpoint:
            raise RuntimeError(
                "OTEL_EXPORTER_OTLP_ENDPOINT is set but opentelemetry-instrumentation-sqlalchemy "
                "is not installed"
            )
        return
    SQLAlchemyInstrumentor().instrument(engine=engine)
    _instrumented_engine_ids.add(engine_id)
