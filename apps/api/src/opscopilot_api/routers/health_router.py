from fastapi import APIRouter, HTTPException, status

from opscopilot_api.services.readiness_service import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "api"}


@router.get("/ready")
def ready() -> dict:
    try:
        check_database()
    except Exception as exc:  # pragma: no cover - exercised in tests via monkeypatch
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "service": "api",
                "dependencies": {"database": "error"},
                "error": str(exc),
            },
        ) from exc
    return {"status": "ready", "service": "api", "dependencies": {"database": "ok"}}
