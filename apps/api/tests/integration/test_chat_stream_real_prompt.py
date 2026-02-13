import os

import pytest
from fastapi.testclient import TestClient


def _missing_env() -> list[str]:
    required = [
        "RUN_MCP_INTEGRATION",
        "MCP_BASE_URL",
        "DATABASE_URL",
        "LLM_MODEL_ID",
        "LLM_COST_TABLE_PATH",
        "AWS_REGION",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if os.getenv("RUN_MCP_INTEGRATION") != "1":
        if "RUN_MCP_INTEGRATION" not in missing:
            missing.append("RUN_MCP_INTEGRATION=1")
    return missing


@pytest.mark.integration
def test_chat_stream_real_prompt_hello_status(client: TestClient) -> None:
    missing = _missing_env()
    if missing:
        pytest.skip("missing env: " + ", ".join(missing))

    create_resp = client.post("/api/sessions", json={"title": "real-stream"})
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    with client.stream(
        "POST",
        f"/api/sessions/{session_id}/chat/stream",
        json={"message": "what is the status of pod hello in default namespace?"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(list(response.iter_text()))

    assert "event: agent_run.started" in body
    assert "event: assistant.token.delta" in body
    assert "event: agent_run.completed" in body
