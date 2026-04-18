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
    max_usd: float | None
    remaining_usd: float | None
    status: str


class NodeUsageResponse(BaseModel):
    agent_node: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    llm_call_count: int


class ModelUsageResponse(BaseModel):
    provider: str
    model_id: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    llm_call_count: int


class RunMetricsResponse(BaseModel):
    usage: UsageMetricsResponse
    budget: BudgetMetricsResponse
    node_usage: list[NodeUsageResponse]
    model_usage: list[ModelUsageResponse]


class RuntimeConfigResponse(BaseModel):
    id: str
    schema_version: str
    node_models: dict[str, str]
    max_agent_steps: int
    max_budget_usd: float | None


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    runtime_config: RuntimeConfigResponse | None
    metrics: RunMetricsResponse


class SessionMetricsResponse(BaseModel):
    usage: UsageMetricsResponse
    budget: BudgetMetricsResponse
    run_count: int


class AgentRunListResponse(BaseModel):
    items: list[AgentRunResponse]
    session_metrics: SessionMetricsResponse
