from fastapi.testclient import TestClient

from opscopilot_api.main import create_app


def test_app_starts() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
