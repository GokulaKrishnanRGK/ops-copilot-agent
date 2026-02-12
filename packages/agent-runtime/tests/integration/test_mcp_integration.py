import os

import pytest

from opscopilot_agent_runtime.mcp_client import MCPClient


def test_mcp_integration_call_tool():
    if os.getenv("RUN_MCP_INTEGRATION") != "1":
        pytest.skip("RUN_MCP_INTEGRATION not enabled")
    base_url = os.getenv("MCP_BASE_URL")
    if not base_url:
        pytest.skip("MCP_BASE_URL not set")
    client = MCPClient.from_env()
    namespace = os.getenv("MCP_NAMESPACE", "default")
    label_selector = os.getenv("MCP_LABEL_SELECTOR", "")
    response = client.call_tool(
        "k8s.list_pods", {"namespace": namespace, "label_selector": label_selector}
    )
    assert "structured_content" in response
    structured = response["structured_content"]
    assert structured.get("status") == "success"
    result = structured.get("result")
    assert isinstance(result, dict)
    items = result.get("items", [])
    assert len(items) > 0
