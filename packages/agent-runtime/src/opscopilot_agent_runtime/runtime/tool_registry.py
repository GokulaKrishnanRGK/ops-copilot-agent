from __future__ import annotations

from dataclasses import dataclass

from opscopilot_agent_runtime.mcp_client import MCPClient, MCPTool


@dataclass
class ToolRegistry:
    client: MCPClient
    _cache: list[MCPTool] | None = None

    def list_tools(self) -> list[MCPTool]:
        if self._cache is None:
            self._cache = self.client.list_tools()
        return self._cache
