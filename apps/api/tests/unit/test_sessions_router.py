from fastapi.testclient import TestClient


def test_session_crud_flow(client: TestClient) -> None:
    create_resp = client.post("/api/sessions", json={"title": "My Session"})
    assert create_resp.status_code == 201
    created = create_resp.json()
    session_id = created["id"]
    assert created["title"] == "My Session"

    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    assert any(item["id"] == session_id for item in list_resp.json()["items"])

    get_resp = client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id

    patch_resp = client.patch(f"/api/sessions/{session_id}", json={"title": "Updated"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated"

    delete_resp = client.delete(f"/api/sessions/{session_id}")
    assert delete_resp.status_code == 204

    missing_resp = client.get(f"/api/sessions/{session_id}")
    assert missing_resp.status_code == 404
