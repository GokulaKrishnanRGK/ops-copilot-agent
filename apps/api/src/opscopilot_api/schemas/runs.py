from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    config_json: dict


class AgentRunListResponse(BaseModel):
    items: list[AgentRunResponse]
