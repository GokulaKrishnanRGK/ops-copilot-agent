import httpx
import pytest

from opscopilot_tools.client import execute_tool


def _can_reach(url: str) -> bool:
    try:
        resp = httpx.get(url, timeout=1.0)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _can_reach("http://localhost:8080/health"), reason="tool server not running")
def test_health_endpoint():
    resp = httpx.get("http://localhost:8080/health", timeout=2.0)
    assert resp.status_code == 200


def test_execute_tool_http_error(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            raise httpx.HTTPStatusError("err", request=None, response=None)

        def json(self):
            return {}

    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json):
            return FakeResponse()

    monkeypatch.setattr("httpx.Client", FakeClient)
    with pytest.raises(httpx.HTTPStatusError):
        execute_tool("k8s.list_pods", {"namespace": "default"}, 1000)
