from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    run_id: str
    answer: str | None
    error: dict | None


class StreamEventBase(BaseModel):
    type: str
    timestamp: str
    session_id: str
    agent_run_id: str
    payload: dict


class AgentRunStartedPayload(BaseModel):
    agent_run_id: str


class AgentRunCompletedPayload(BaseModel):
    summary: str


class AgentRunFailedPayload(BaseModel):
    reason: str
    failure_type: str


class ErrorPayload(BaseModel):
    error_type: str
    message: str
    context: dict


class AssistantTokenDeltaPayload(BaseModel):
    text: str
    source: str | None = None


class AnswerCompletedPayload(BaseModel):
    message: str


class AgentRunStartedEvent(StreamEventBase):
    type: Literal["agent_run.started"]
    payload: AgentRunStartedPayload


class AgentRunCompletedEvent(StreamEventBase):
    type: Literal["agent_run.completed"]
    payload: AgentRunCompletedPayload


class AgentRunFailedEvent(StreamEventBase):
    type: Literal["agent_run.failed"]
    payload: AgentRunFailedPayload


class ErrorEvent(StreamEventBase):
    type: Literal["error"]
    payload: ErrorPayload


class AssistantTokenDeltaEvent(StreamEventBase):
    type: Literal["assistant.token.delta"]
    payload: AssistantTokenDeltaPayload


class ScopeCheckStartedEvent(StreamEventBase):
    type: Literal["scope_check.started"]
    payload: dict


class ScopeCheckCompletedEvent(StreamEventBase):
    type: Literal["scope_check.completed"]
    payload: dict


class ScopeCheckRejectedEvent(StreamEventBase):
    type: Literal["scope_check.rejected"]
    payload: dict


class PlannerStartedEvent(StreamEventBase):
    type: Literal["planner.started"]
    payload: dict


class PlannerCompletedEvent(StreamEventBase):
    type: Literal["planner.completed"]
    payload: dict


class ClarifierStartedEvent(StreamEventBase):
    type: Literal["clarifier.started"]
    payload: dict


class ClarifierCompletedEvent(StreamEventBase):
    type: Literal["clarifier.completed"]
    payload: dict


class ClarifierClarificationRequiredEvent(StreamEventBase):
    type: Literal["clarifier.clarification_required"]
    payload: dict


class AnswerStartedEvent(StreamEventBase):
    type: Literal["answer.started"]
    payload: dict


class AnswerCompletedEvent(StreamEventBase):
    type: Literal["answer.completed"]
    payload: AnswerCompletedPayload


ChatStreamEvent = (
    AgentRunStartedEvent
    | AgentRunCompletedEvent
    | AgentRunFailedEvent
    | ErrorEvent
    | AssistantTokenDeltaEvent
    | ScopeCheckStartedEvent
    | ScopeCheckCompletedEvent
    | ScopeCheckRejectedEvent
    | PlannerStartedEvent
    | PlannerCompletedEvent
    | ClarifierStartedEvent
    | ClarifierCompletedEvent
    | ClarifierClarificationRequiredEvent
    | AnswerStartedEvent
    | AnswerCompletedEvent
)
