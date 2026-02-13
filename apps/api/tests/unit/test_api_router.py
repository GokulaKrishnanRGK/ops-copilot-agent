from fastapi.testclient import TestClient


def test_api_routes(client: TestClient) -> None:
    assert client.get("/api/sessions").status_code == 200
    assert client.get("/api/messages", params={"session_id": "missing"}).status_code == 404
    assert client.get("/api/runs", params={"session_id": "missing"}).status_code == 404
