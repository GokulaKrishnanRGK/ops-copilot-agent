from fastapi.testclient import TestClient

from opscopilot_api.main import create_app


def test_ready_ok(monkeypatch) -> None:
    monkeypatch.setattr("opscopilot_api.routers.health_router.check_database", lambda: None)
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "api",
        "dependencies": {"database": "ok"},
    }


def test_ready_not_ok(monkeypatch) -> None:
    def _raise() -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("opscopilot_api.routers.health_router.check_database", _raise)
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()["detail"]
    assert body["status"] == "not_ready"
    assert body["dependencies"]["database"] == "error"
