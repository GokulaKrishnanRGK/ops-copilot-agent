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
        return RuntimeConfigData(
            id=config.id,
            schema_version=config.schema_version,
            nodes=nodes,
            max_agent_steps=int(limits.get("max_agent_steps", 10)),
            max_budget_usd=float(max_budget_raw) if max_budget_raw is not None else None,
        )


class ConfigCache(Protocol):
    def get(self) -> RuntimeConfigData: ...


class InMemoryConfigCache:
    def __init__(self, config: models.RuntimeConfig) -> None:
        self._data = RuntimeConfigData.from_db(config)

    def get(self) -> RuntimeConfigData:
        return self._data
