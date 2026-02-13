from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    run_id: str
    answer: str | None
    error: dict | None
