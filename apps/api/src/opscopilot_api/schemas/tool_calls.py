from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_run_id: str
    tool_name: str
    status: str
    latency_ms: int
    bytes_returned: int
    truncated: bool
    error_message: str | None
    created_at: datetime
    log_text: str | None = None


class ToolCallListResponse(BaseModel):
    items: list[ToolCallResponse]
