from __future__ import annotations

import os
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
    eval_judge_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    prompt_injection_llm_check: bool = False
    agent_max_tool_calls: int = 10
    agent_max_llm_calls: int = 10
    agent_max_execution_time_ms: int = 30_000

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
            eval_sample_rate=float(env["eval_sample_rate"]) if "eval_sample_rate" in env else float(os.getenv("EVAL_SAMPLE_RATE", "0.1")),
            eval_llm_judge_enabled=bool(env["eval_llm_judge_enabled"]) if "eval_llm_judge_enabled" in env else os.getenv("EVAL_LLM_JUDGE_ENABLED", "1") != "0",
            eval_ragas_enabled=bool(env["eval_ragas_enabled"]) if "eval_ragas_enabled" in env else os.getenv("EVAL_RAGAS_ENABLED", "1") != "0",
            eval_judge_model_id=str(env["eval_judge_model_id"]) if "eval_judge_model_id" in env else os.getenv("EVAL_JUDGE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"),
            prompt_injection_llm_check=bool(env["prompt_injection_llm_check"]) if "prompt_injection_llm_check" in env else os.getenv("PROMPT_INJECTION_LLM_CHECK", "0") == "1",
            agent_max_tool_calls=int(env["agent_max_tool_calls"]) if "agent_max_tool_calls" in env else int(os.getenv("AGENT_MAX_TOOL_CALLS", "10")),
            agent_max_llm_calls=int(env["agent_max_llm_calls"]) if "agent_max_llm_calls" in env else int(os.getenv("AGENT_MAX_LLM_CALLS", "10")),
            agent_max_execution_time_ms=int(env["agent_max_execution_time_ms"]) if "agent_max_execution_time_ms" in env else int(os.getenv("AGENT_MAX_EXECUTION_TIME_MS", "30000")),
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
