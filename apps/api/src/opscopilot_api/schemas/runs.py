from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UsageMetricsResponse(BaseModel):
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    llm_call_count: int


class BudgetMetricsResponse(BaseModel):
    total_usd: float
    delta_usd: float
    event_count: int


class NodeUsageResponse(BaseModel):
    agent_node: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    llm_call_count: int


class RunMetricsResponse(BaseModel):
    usage: UsageMetricsResponse
    budget: BudgetMetricsResponse
    node_usage: list[NodeUsageResponse]


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    config_json: dict
    metrics: RunMetricsResponse


class SessionMetricsResponse(BaseModel):
    usage: UsageMetricsResponse
    budget: BudgetMetricsResponse
    run_count: int


class AgentRunListResponse(BaseModel):
    items: list[AgentRunResponse]
    session_metrics: SessionMetricsResponse
