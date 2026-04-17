import pytest

from opscopilot_eval.datasets import LocalJsonlDatasetStore


def test_local_jsonl_dataset_store_lists_datasets(tmp_path):
    root = tmp_path / "datasets"
    root.mkdir()
    (root / "smoke.jsonl").write_text("", encoding="utf-8")
    (root / "regression.jsonl").write_text("", encoding="utf-8")

    store = LocalJsonlDatasetStore(root)

    assert store.list_datasets() == ["regression", "smoke"]


def test_local_jsonl_dataset_store_loads_examples(tmp_path):
    root = tmp_path / "datasets"
    root.mkdir()
    (root / "smoke.jsonl").write_text(
        '{"input":"list pods","expected_intent":"tool_action","expected_answer_contains":["pod"]}\n',
        encoding="utf-8",
    )

    store = LocalJsonlDatasetStore(root)
    examples = store.load("smoke")

    assert len(examples) == 1
    assert examples[0].input == "list pods"
    assert examples[0].expected_intent == "tool_action"
    assert examples[0].expected_answer_contains == ["pod"]


def test_local_jsonl_dataset_store_rejects_missing_dataset(tmp_path):
    store = LocalJsonlDatasetStore(tmp_path / "datasets")

    with pytest.raises(FileNotFoundError, match="missing"):
        store.load("missing")


def test_local_jsonl_dataset_store_rejects_invalid_record(tmp_path):
    root = tmp_path / "datasets"
    root.mkdir()
    (root / "broken.jsonl").write_text(
        '{"input":"list pods","expected_intent":"tool_action"}\n',
        encoding="utf-8",
    )

    store = LocalJsonlDatasetStore(root)

    with pytest.raises(ValueError, match="expected_answer_contains"):
        store.load("broken")
