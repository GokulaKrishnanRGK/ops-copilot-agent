from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime
    metadata_json: dict | None = None


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
