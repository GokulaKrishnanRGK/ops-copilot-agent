from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

from mcp import types

from opscopilot_agent_runtime.mcp_client import MCPClient


@dataclass
class FakeTool:
    name: str
    description: str


@dataclass
class FakeListToolsResult:
    tools: list[FakeTool]


@dataclass
class FakeCallResult:
    content: list[Any]
    structured_content: dict[str, Any] | None = None


class FakeSession:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.initialized = False

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> bool:
        return False

    async def initialize(self) -> None:
        self.initialized = True

    async def list_tools(self) -> FakeListToolsResult:
        return FakeListToolsResult(
            tools=[FakeTool(name="k8s.list_pods", description="")]
        )

    async def call_tool(self, _name: str, arguments: dict[str, Any]) -> FakeCallResult:
        return FakeCallResult(
            content=[types.TextContent(type="text", text=str(arguments))],
            structured_content={"ok": True},
        )


class FakeStream:
    async def __aenter__(self):
        return (None, None, None)

    async def __aexit__(self, _exc_type, _exc, _tb) -> bool:
        return False


def fake_streamable_http_client(_base_url: str) -> FakeStream:
    return FakeStream()


def test_mcp_client_list_tools():
    with patch(
        "opscopilot_agent_runtime.mcp_client.streamable_http_client",
        fake_streamable_http_client,
    ), patch("opscopilot_agent_runtime.mcp_client.ClientSession", FakeSession):
        client = MCPClient("http://example", 1.0, 0)
        tools = client.list_tools()

    assert tools[0].name == "k8s.list_pods"


def test_mcp_client_call_tool():
    with patch(
        "opscopilot_agent_runtime.mcp_client.streamable_http_client",
        fake_streamable_http_client,
    ), patch("opscopilot_agent_runtime.mcp_client.ClientSession", FakeSession):
        client = MCPClient("http://example", 1.0, 0)
        response = client.call_tool("k8s.list_pods", {"namespace": "default"})

    assert response["content"][0]["text"] == "{'namespace': 'default'}"
    assert response["structured_content"] == {"ok": True}
