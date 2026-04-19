from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from opscopilot_db import models


@dataclass(frozen=True)
class NodeConfig:
    model_id: str
    prompt_version: str


@dataclass(frozen=True)
class RuntimeConfigData:
    id: str
    schema_version: str
    nodes: dict[str, NodeConfig]
    max_agent_steps: int
    max_budget_usd: float | None
    history_window_turns: int = 6
    summarizer_prompt_version: str = "latest"
    eval_sample_rate: float = 0.1
    eval_llm_judge_enabled: bool = True
    eval_ragas_enabled: bool = True
    eval_judge_model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    prompt_injection_llm_check: bool = False
    agent_max_tool_calls: int = 10
    agent_max_llm_calls: int = 10
    agent_max_execution_time_ms: int = 30_000
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v1"
    title_gen_model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    title_gen_prompt_version: str = "latest"

    def node(self, name: str) -> NodeConfig:
        try:
            return self.nodes[name]
        except KeyError:
            raise RuntimeError(f"no config for node '{name}' in runtime config")

    @staticmethod
    def from_db(config: models.RuntimeConfig) -> RuntimeConfigData:
        raw: dict[str, Any] = config.config_json
        nodes = {
            name: NodeConfig(
                model_id=cfg["model_id"],
                prompt_version=cfg.get("prompt_version", "v1"),
            )
            for name, cfg in raw.get("nodes", {}).items()
        }
        limits: dict[str, Any] = raw.get("limits", {})
        max_budget_raw = limits.get("max_budget_usd")
        env: dict[str, Any] = raw.get("env_overrides", {})
        return RuntimeConfigData(
            id=config.id,
            schema_version=config.schema_version,
            nodes=nodes,
            max_agent_steps=int(limits.get("max_agent_steps", 10)),
            max_budget_usd=float(max_budget_raw) if max_budget_raw is not None else None,
            history_window_turns=int(limits.get("history_window_turns", 6)),
            summarizer_prompt_version=str(limits.get("summarizer_prompt_version", "latest")),
            eval_sample_rate=float(env.get("eval_sample_rate", 0.1)),
            eval_llm_judge_enabled=bool(env.get("eval_llm_judge_enabled", True)),
            eval_ragas_enabled=bool(env.get("eval_ragas_enabled", True)),
            eval_judge_model_id=str(env.get("eval_judge_model_id", "global.anthropic.claude-haiku-4-5-20251001-v1:0")),
            prompt_injection_llm_check=bool(env.get("prompt_injection_llm_check", False)),
            agent_max_tool_calls=int(env.get("agent_max_tool_calls", 10)),
            agent_max_llm_calls=int(env.get("agent_max_llm_calls", 10)),
            agent_max_execution_time_ms=int(env.get("agent_max_execution_time_ms", 30000)),
            bedrock_embedding_model_id=str(env.get("bedrock_embedding_model_id", "amazon.titan-embed-text-v1")),
            title_gen_model_id=str(env.get("title_gen_model_id", "global.anthropic.claude-haiku-4-5-20251001-v1:0")),
            title_gen_prompt_version=str(env.get("title_gen_prompt_version", "latest")),
        )


class ConfigCache(Protocol):
    def get(self) -> RuntimeConfigData: ...


class InMemoryConfigCache:
    def __init__(self, config: models.RuntimeConfig) -> None:
        self._data = RuntimeConfigData.from_db(config)

    def get(self) -> RuntimeConfigData:
        return self._data

    def set(self, config: RuntimeConfigData) -> None:
        self._data = config
