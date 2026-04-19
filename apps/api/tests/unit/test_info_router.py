import pytest
from fastapi.testclient import TestClient


def test_get_info_readonly_always_true(client: TestClient) -> None:
    resp = client.get("/api/info")

    assert resp.status_code == 200
    assert resp.json()["readonly"] is True


def test_get_info_allowed_namespaces_from_env(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("K8S_ALLOWED_NAMESPACES", "default,opscopilot,observability")

    resp = client.get("/api/info")

    assert resp.status_code == 200
    assert resp.json()["allowed_namespaces"] == ["default", "opscopilot", "observability"]


def test_get_info_allowed_namespaces_empty_when_unset(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("K8S_ALLOWED_NAMESPACES", raising=False)

    resp = client.get("/api/info")

    assert resp.status_code == 200
    assert resp.json()["allowed_namespaces"] == []


def test_get_info_tool_server_url_host_only(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("MCP_BASE_URL", "http://tool-server:8080/mcp")

    resp = client.get("/api/info")

    assert resp.status_code == 200
    assert resp.json()["tool_server_url"] == "http://tool-server:8080"


def test_get_info_tool_server_url_empty_when_unset(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("MCP_BASE_URL", raising=False)

    resp = client.get("/api/info")

    assert resp.status_code == 200
    assert resp.json()["tool_server_url"] == ""
