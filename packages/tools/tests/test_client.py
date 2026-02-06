from opscopilot_tools.client import execute_tool


def test_execute_tool_builds_payload(monkeypatch):
    called = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, timeout):
            called["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json):
            called["url"] = url
            called["json"] = json
            return FakeResponse()

    monkeypatch.setattr("httpx.Client", FakeClient)
    result = execute_tool("k8s.list_pods", {"namespace": "default"}, 1500)
    assert result == {"ok": True}
    assert called["json"]["tool_name"] == "k8s.list_pods"
    assert called["timeout"] == 1.5
