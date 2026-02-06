import os

import httpx


def _base_url() -> str:
    return os.environ.get("TOOLS_BASE_URL", "http://localhost:8080")


def execute_tool(tool_name: str, args: dict, timeout_ms: int) -> dict:
    payload = {"tool_name": tool_name, "args": args, "timeout_ms": timeout_ms}
    timeout = timeout_ms / 1000.0
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{_base_url()}/tools/execute", json=payload)
        resp.raise_for_status()
        return resp.json()
