from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class InfoResponse(BaseModel):
    readonly: bool
    allowed_namespaces: list[str]
    tool_server_url: str


def _allowed_namespaces() -> list[str]:
    raw = os.getenv("K8S_ALLOWED_NAMESPACES", "")
    return [ns.strip() for ns in raw.split(",") if ns.strip()]


def _tool_server_host() -> str:
    raw = os.getenv("MCP_BASE_URL", "")
    if not raw:
        return ""
    parsed = urlparse(raw)
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else raw


@router.get("/info", response_model=InfoResponse)
def get_info() -> InfoResponse:
    return InfoResponse(
        readonly=True,
        allowed_namespaces=_allowed_namespaces(),
        tool_server_url=_tool_server_host(),
    )
