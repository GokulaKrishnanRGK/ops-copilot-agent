import logging
import time

from fastapi import FastAPI, Request

from .logging import configure_logging
from .routers.health_router import router as health_router
from .routers.api_router import router as api_router


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Ops Copilot API", version="0.1.0")

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - start) * 1000)
            logging.getLogger("opscopilot_api.request").info(
                "method=%s path=%s status=%s duration_ms=%d",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logging.getLogger("opscopilot_api.request").exception(
                "method=%s path=%s status=500 duration_ms=%d",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
