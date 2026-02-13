from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionUpdateRequest(BaseModel):
    title: str | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
