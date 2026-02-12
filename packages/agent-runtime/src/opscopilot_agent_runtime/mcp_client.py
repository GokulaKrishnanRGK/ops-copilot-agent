from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client

from opscopilot_agent_runtime.runtime.logging import get_logger

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
    input_schema: dict | None
    output_schema: dict | None


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
        logger = get_logger(__name__)
        tools = asyncio.run(self._list_tools())
        if os.getenv("AGENT_DEBUG") == "1":
            logger.info("mcp list_tools count=%s names=%s", len(tools), [t.name for t in tools])
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict:
        logger = get_logger(__name__)
        if os.getenv("AGENT_DEBUG") == "1":
            logger.info("mcp call_tool name=%s args=%s", name, json.dumps(arguments, default=str))
        return asyncio.run(self._call_tool(name, arguments))

    async def _list_tools(self) -> list[MCPTool]:
        async def handler(session: ClientSession):
            tools = await session.list_tools()
            result = []
            for t in tools.tools:
                input_schema = getattr(t, "inputSchema", None)
                if input_schema is None:
                    input_schema = getattr(t, "input_schema", None)
                output_schema = getattr(t, "outputSchema", None)
                if output_schema is None:
                    output_schema = getattr(t, "output_schema", None)
                result.append(
                    MCPTool(
                        name=t.name,
                        description=t.description or "",
                        input_schema=input_schema,
                        output_schema=output_schema,
                    )
                )
            return result

        return await self._with_session(handler)

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict:
        logger = get_logger(__name__)

        async def handler(session: ClientSession):
            result = await session.call_tool(name, arguments=arguments)
            payload = self._result_to_dict(result)
            if os.getenv("AGENT_DEBUG") == "1":
                logger.info("mcp tool_result name=%s payload=%s", name, json.dumps(payload, default=str))
            return payload

        return await self._with_session(handler)

    async def _with_session(self, handler):
        logger = get_logger(__name__)
        attempt = 0
        while True:
            attempt += 1
            try:
                async with streamable_http_client(self._base_url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await handler(session)
            except Exception as exc:
                if os.getenv("AGENT_DEBUG") == "1":
                    logger.info("mcp session error base_url=%s attempt=%s error=%s", self._base_url, attempt, exc)
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
