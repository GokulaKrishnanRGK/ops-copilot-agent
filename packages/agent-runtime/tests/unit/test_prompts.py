import pytest

from opscopilot_agent_runtime.prompts import (
    LangfusePromptSource,
    LocalYamlPromptSource,
    load_local_prompt_definitions,
    prompt_ref_for,
    prompt_source_from_env,
    push_prompts_to_langfuse,
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
    def __init__(self, text: str, version: int = 7):
        self._text = text
        self.version = version

    def compile(self) -> str:
        return self._text


class FakeLangfuseClient:
    def __init__(self):
        self.calls = []

    def get_prompt(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return FakeLangfusePrompt("Prompt from Langfuse.")


def test_langfuse_prompt_source_fetches_yaml_version_label():
    client = FakeLangfuseClient()
    source = LangfusePromptSource(client=client)

    prompt = source.get("answer", "v1")

    assert prompt == "Prompt from Langfuse."
    assert client.calls == [("answer", {"type": "text", "label": "v1"})]
    assert prompt_ref_for(source, "answer", "v1").langfuse_version == "7"


def test_langfuse_prompt_source_fetches_numeric_version():
    client = FakeLangfuseClient()
    source = LangfusePromptSource(client=client)

    prompt = source.get("answer", "1")

    assert prompt == "Prompt from Langfuse."
    assert client.calls == [("answer", {"type": "text", "version": 1})]


def test_langfuse_prompt_source_fetches_label_version():
    client = FakeLangfuseClient()
    source = LangfusePromptSource(client=client)

    prompt = source.get("answer", "candidate")

    assert prompt == "Prompt from Langfuse."
    assert client.calls == [("answer", {"type": "text", "label": "candidate"})]


def test_prompt_source_from_env_raises_without_langfuse(monkeypatch):
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="LANGFUSE_HOST"):
        prompt_source_from_env()


def test_prompt_source_from_env_returns_langfuse_when_configured(monkeypatch):
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3001")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")

    source = prompt_source_from_env(client=FakeLangfuseClient())

    assert isinstance(source, LangfusePromptSource)


def test_load_local_prompt_definitions_reads_all_versions(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "answer.yaml").write_text(
        "name: answer\nversions:\n  v1: |\n    Base answer.\n  v1_stream: |\n    Stream answer.\n",
        encoding="utf-8",
    )

    definitions = load_local_prompt_definitions(prompts_dir)

    assert [(item.name, item.version, item.text) for item in definitions] == [
        ("answer", "v1", "Base answer."),
        ("answer", "v1_stream", "Stream answer."),
    ]


class FakeLangfusePushClient:
    def __init__(self):
        self.created = []

    def create_prompt(self, **kwargs):
        self.created.append(kwargs)


def test_push_prompts_to_langfuse_creates_text_prompts(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "scope.yaml").write_text(
        "name: scope\nversions:\n  v1: |\n    Scope prompt.\n",
        encoding="utf-8",
    )
    client = FakeLangfusePushClient()

    pushed = push_prompts_to_langfuse(client=client, prompts_dir=prompts_dir)

    assert pushed == 1
    assert client.created == [
        {
            "name": "scope",
            "type": "text",
            "prompt": "Scope prompt.",
            "labels": ["v1", "latest"],
        }
    ]


def test_push_prompts_to_langfuse_latest_label_on_last_version(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "answer.yaml").write_text(
        "name: answer\nversions:\n  v1: |\n    Answer v1.\n  v2: |\n    Answer v2.\n",
        encoding="utf-8",
    )
    client = FakeLangfusePushClient()

    push_prompts_to_langfuse(client=client, prompts_dir=prompts_dir)

    labels_by_version = {c["labels"][0]: c["labels"] for c in client.created}
    assert labels_by_version["v1"] == ["v1"]
    assert labels_by_version["v2"] == ["v2", "latest"]
