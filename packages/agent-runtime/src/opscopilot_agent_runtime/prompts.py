from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import yaml


class PromptSource(Protocol):
    def get(self, name: str, version: str) -> str: ...


class LocalYamlPromptSource:
    def __init__(self, prompts_dir: str | Path | None = None) -> None:
        self._prompts_dir = self._resolve_prompts_dir(prompts_dir)

    def get(self, name: str, version: str) -> str:
        prompt_file = self._prompts_dir / f"{name}.yaml"
        if not prompt_file.exists():
            raise FileNotFoundError(f"prompt file not found: {prompt_file}")

        payload = yaml.safe_load(prompt_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"prompt file must contain a mapping: {prompt_file}")

        versions = payload.get("versions")
        if not isinstance(versions, dict):
            raise ValueError(f"prompt file must define versions: {prompt_file}")

        prompt = versions.get(version)
        if not isinstance(prompt, str) or not prompt.strip():
            raise KeyError(f"prompt version not found: {name}@{version}")

        return prompt.strip()

    def _resolve_prompts_dir(self, prompts_dir: str | Path | None) -> Path:
        if prompts_dir is not None:
            return Path(prompts_dir)

        env_dir = os.getenv("PROMPTS_DIR")
        if env_dir:
            return Path(env_dir)

        for base in (Path.cwd(), *Path(__file__).resolve().parents):
            candidate = base / "prompts"
            if candidate.exists():
                return candidate

        return Path("prompts")
