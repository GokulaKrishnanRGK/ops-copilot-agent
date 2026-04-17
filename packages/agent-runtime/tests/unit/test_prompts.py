import pytest

from opscopilot_agent_runtime.prompts import LocalYamlPromptSource


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
