from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    started_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    agent_node: Mapped[str] = mapped_column(String, nullable=False)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    args_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    bytes_returned: Mapped[int] = mapped_column(Integer, nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)


class BudgetEvent(Base):
    __tablename__ = "budget_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    delta_usd: Mapped[float] = mapped_column(Numeric, nullable=False)
    total_usd: Mapped[float] = mapped_column(Numeric, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
