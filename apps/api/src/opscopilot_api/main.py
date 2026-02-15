import logging
import time

from fastapi import FastAPI, Request
from opentelemetry import trace

from .logging import configure_logging, reset_log_context, set_log_context
from .routers.health_router import router as health_router
from .routers.api_router import router as api_router
from .telemetry import configure_telemetry


def create_app() -> FastAPI:
    configure_logging()
    configure_telemetry()
    app = FastAPI(title="Ops Copilot API", version="0.1.0")
    tracer = trace.get_tracer("opscopilot_api.http")

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        start = time.perf_counter()
        path_parts = [part for part in request.url.path.split("/") if part]
        session_id = ""
        if len(path_parts) >= 3 and path_parts[0] == "api" and path_parts[1] == "sessions":
            session_id = path_parts[2]
        context_tokens = set_log_context(session_id=session_id, agent_run_id="")
        with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.route", request.url.path)
            try:
                response = await call_next(request)
                duration_ms = int((time.perf_counter() - start) * 1000)
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.duration_ms", duration_ms)
                logging.getLogger("opscopilot_api.request").info(
                    "method=%s path=%s status=%s duration_ms=%d",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                )
                return response
            except Exception as exc:
                duration_ms = int((time.perf_counter() - start) * 1000)
                span.set_attribute("http.status_code", 500)
                span.set_attribute("http.duration_ms", duration_ms)
                span.record_exception(exc)
                logging.getLogger("opscopilot_api.request").exception(
                    "method=%s path=%s status=500 duration_ms=%d",
                    request.method,
                    request.url.path,
                    duration_ms,
                )
                raise
            finally:
                reset_log_context(context_tokens)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
