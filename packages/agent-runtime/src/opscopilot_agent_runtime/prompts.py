from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol

import yaml


class PromptSource(Protocol):
    def get(self, name: str, version: str) -> str: ...


@dataclass(frozen=True)
class PromptDefinition:
    name: str
    version: str
    text: str


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


class LangfusePromptSource:
    def __init__(
        self,
        client: Any | None = None,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
    ) -> None:
        self._client = client or self._create_client(public_key, secret_key, host)

    def get(self, name: str, version: str) -> str:
        prompt = self._client.get_prompt(name, type="text", **_version_kwargs(version))
        compiled = prompt.compile()
        if not isinstance(compiled, str) or not compiled.strip():
            raise RuntimeError(f"langfuse prompt did not compile to text: {name}@{version}")
        return compiled.strip()

    def _create_client(
        self,
        public_key: str | None,
        secret_key: str | None,
        host: str | None,
    ) -> Any:
        resolved_host = host or os.getenv("LANGFUSE_HOST")
        resolved_public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        resolved_secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        if not resolved_host or not resolved_public_key or not resolved_secret_key:
            raise RuntimeError(
                "LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, and LANGFUSE_SECRET_KEY are required"
            )
        module = import_module("langfuse")
        client_class = getattr(module, "Langfuse")
        return client_class(
            public_key=resolved_public_key,
            secret_key=resolved_secret_key,
            host=resolved_host,
        )


def prompt_source_from_env(client: Any | None = None) -> PromptSource:
    host = os.getenv("LANGFUSE_HOST")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if host and public_key and secret_key:
        return LangfusePromptSource(
            client=client,
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
    return LocalYamlPromptSource()


def load_local_prompt_definitions(prompts_dir: str | Path | None = None) -> list[PromptDefinition]:
    source = LocalYamlPromptSource(prompts_dir)
    definitions: list[PromptDefinition] = []
    for prompt_file in sorted(source._prompts_dir.glob("*.yaml")):
        payload = yaml.safe_load(prompt_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"prompt file must contain a mapping: {prompt_file}")
        name = payload.get("name")
        versions = payload.get("versions")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"prompt file must define name: {prompt_file}")
        if not isinstance(versions, dict):
            raise ValueError(f"prompt file must define versions: {prompt_file}")
        for version, prompt in versions.items():
            if not isinstance(version, str) or not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"invalid prompt version in file: {prompt_file}")
            definitions.append(
                PromptDefinition(name=name.strip(), version=version, text=prompt.strip())
            )
    return definitions


def push_prompts_to_langfuse(
    client: Any | None = None,
    prompts_dir: str | Path | None = None,
) -> int:
    resolved_client = client or LangfusePromptSource()._client
    definitions = load_local_prompt_definitions(prompts_dir)
    for definition in definitions:
        resolved_client.create_prompt(
            name=definition.name,
            type="text",
            prompt=definition.text,
            labels=[definition.version],
        )
    return len(definitions)


def _version_kwargs(version: str) -> dict[str, int | str]:
    if version.isdigit():
        return {"version": int(version)}
    return {"label": version}
