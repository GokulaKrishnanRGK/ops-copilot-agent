from pydantic import BaseModel, Field


class NodeConfigSchema(BaseModel):
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)


class SettingsNodesSchema(BaseModel):
    scope: NodeConfigSchema
    planner: NodeConfigSchema
    clarifier: NodeConfigSchema
    answer: NodeConfigSchema
    summarizer: NodeConfigSchema
    injection_classifier: NodeConfigSchema


class SettingsResponse(BaseModel):
    id: str
    schema_version: str
    nodes: SettingsNodesSchema
    max_agent_steps: int
    max_budget_usd: float | None
    history_window_turns: int
    summarizer_prompt_version: str
    eval_sample_rate: float
    eval_llm_judge_enabled: bool
    eval_ragas_enabled: bool
    eval_judge_model_id: str
    prompt_injection_llm_check: bool
    agent_max_tool_calls: int
    agent_max_llm_calls: int
    agent_max_execution_time_ms: int
    bedrock_embedding_model_id: str


class SettingsUpdate(BaseModel):
    nodes: SettingsNodesSchema
    max_agent_steps: int = Field(ge=1)
    max_budget_usd: float | None = Field(default=None, ge=0)
    history_window_turns: int = Field(ge=1)
    summarizer_prompt_version: str = Field(min_length=1)
    eval_sample_rate: float = Field(ge=0.0, le=1.0)
    eval_llm_judge_enabled: bool
    eval_ragas_enabled: bool
    eval_judge_model_id: str = Field(min_length=1)
    prompt_injection_llm_check: bool
    agent_max_tool_calls: int = Field(ge=1)
    agent_max_llm_calls: int = Field(ge=1)
    agent_max_execution_time_ms: int = Field(ge=1)
    bedrock_embedding_model_id: str = Field(min_length=1)
