from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client


@dataclass(frozen=True)
class MCPError(Exception):
    code: int
    message: str

    def __str__(self) -> str:
        return f"mcp error {self.code}: {self.message}"


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str


class MCPClient:
    def __init__(self, base_url: str, timeout_s: float, max_retries: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_retries = max_retries

    @staticmethod
    def from_env() -> "MCPClient":
        base_url = os.getenv("MCP_BASE_URL", "http://localhost:8080/mcp")
        timeout_ms = int(os.getenv("MCP_TIMEOUT_MS", "3000"))
        max_retries = int(os.getenv("MCP_MAX_RETRIES", "2"))
        return MCPClient(base_url, timeout_ms / 1000.0, max_retries)

    def list_tools(self) -> list[MCPTool]:
        return asyncio.run(self._list_tools())

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict:
        return asyncio.run(self._call_tool(name, arguments))

    async def _list_tools(self) -> list[MCPTool]:
        async def handler(session: ClientSession):
            tools = await session.list_tools()
            return [MCPTool(name=t.name, description=t.description or "") for t in tools.tools]

        return await self._with_session(handler)

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict:
        async def handler(session: ClientSession):
            result = await session.call_tool(name, arguments=arguments)
            return self._result_to_dict(result)

        return await self._with_session(handler)

    async def _with_session(self, handler):
        attempt = 0
        while True:
            attempt += 1
            try:
                async with streamable_http_client(self._base_url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await handler(session)
            except Exception as exc:
                if attempt > self._max_retries:
                    raise exc
                await asyncio.sleep(0.2 * attempt)

    def _result_to_dict(self, result) -> dict:
        content_items: list[dict[str, Any]] = []
        for item in result.content:
            if isinstance(item, types.TextContent):
                content_items.append({"type": "text", "text": item.text})
            elif isinstance(item, types.ImageContent):
                content_items.append({"type": "image", "data": item.data, "mime_type": item.mime_type})
            else:
                content_items.append({"type": "unknown"})
        structured = getattr(result, "structured_content", None)
        if structured is None:
            structured = getattr(result, "structuredContent", None)
        return {
            "content": content_items,
            "structured_content": structured,
        }
