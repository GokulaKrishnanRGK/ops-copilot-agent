import pytest

from opscopilot_agent_runtime.prompts import (
    LangfusePromptSource,
    LocalYamlPromptSource,
    prompt_source_from_env,
)


def test_local_yaml_prompt_source_reads_versioned_prompt(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "answer.yaml").write_text(
        "name: answer\nversions:\n  v1: |\n    Return a concise answer.\n",
        encoding="utf-8",
    )

    source = LocalYamlPromptSource(prompts_dir)

    assert source.get("answer", "v1") == "Return a concise answer."


def test_local_yaml_prompt_source_rejects_missing_version(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "answer.yaml").write_text(
        "name: answer\nversions:\n  v1: |\n    Return a concise answer.\n",
        encoding="utf-8",
    )

    source = LocalYamlPromptSource(prompts_dir)

    with pytest.raises(KeyError, match="answer@v2"):
        source.get("answer", "v2")


def test_local_yaml_prompt_source_rejects_invalid_prompt_file(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "answer.yaml").write_text("name: answer\n", encoding="utf-8")

    source = LocalYamlPromptSource(prompts_dir)

    with pytest.raises(ValueError, match="versions"):
        source.get("answer", "v1")


class FakeLangfusePrompt:
    def __init__(self, text: str):
        self._text = text

    def compile(self) -> str:
        return self._text


class FakeLangfuseClient:
    def __init__(self):
        self.calls = []

    def get_prompt(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return FakeLangfusePrompt("Prompt from Langfuse.")


def test_langfuse_prompt_source_fetches_numeric_version():
    client = FakeLangfuseClient()
    source = LangfusePromptSource(client=client)

    prompt = source.get("answer", "v1")

    assert prompt == "Prompt from Langfuse."
    assert client.calls == [("answer", {"type": "text", "version": 1})]


def test_langfuse_prompt_source_fetches_label_version():
    client = FakeLangfuseClient()
    source = LangfusePromptSource(client=client)

    prompt = source.get("answer", "candidate")

    assert prompt == "Prompt from Langfuse."
    assert client.calls == [("answer", {"type": "text", "label": "candidate"})]


def test_prompt_source_from_env_returns_local_without_langfuse(monkeypatch):
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    source = prompt_source_from_env()

    assert isinstance(source, LocalYamlPromptSource)


def test_prompt_source_from_env_returns_langfuse_when_configured(monkeypatch):
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3001")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")

    source = prompt_source_from_env(client=FakeLangfuseClient())

    assert isinstance(source, LangfusePromptSource)
