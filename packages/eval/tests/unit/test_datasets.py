import pytest

from opscopilot_eval.datasets import (
    LocalJsonlDatasetStore,
    S3DatasetStore,
    dataset_store_from_env,
)


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


class FakeS3Client:
    def __init__(self):
        self.list_calls = []
        self.objects = {
            ("eval-bucket", "eval/datasets/smoke.jsonl"): (
                b'{"input":"list pods","expected_intent":"tool_action",'
                b'"expected_answer_contains":["pod"]}\n'
            ),
            ("eval-bucket", "eval/datasets/regression.jsonl"): b"",
        }

    def list_objects_v2(self, **kwargs):
        self.list_calls.append(kwargs)
        return {
            "Contents": [
                {"Key": "eval/datasets/smoke.jsonl"},
                {"Key": "eval/datasets/regression.jsonl"},
                {"Key": "eval/datasets/ignored.txt"},
            ]
        }

    def get_object(self, **kwargs):
        key = (kwargs["Bucket"], kwargs["Key"])
        if key not in self.objects:
            raise FileNotFoundError(kwargs["Key"])
        return {"Body": FakeBody(self.objects[key])}


class FakeBody:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload


def test_s3_dataset_store_lists_datasets():
    client = FakeS3Client()
    store = S3DatasetStore(bucket="eval-bucket", prefix="eval/datasets", client=client)

    assert store.list_datasets() == ["regression", "smoke"]
    assert client.list_calls == [{"Bucket": "eval-bucket", "Prefix": "eval/datasets/"}]


def test_s3_dataset_store_loads_examples():
    store = S3DatasetStore(bucket="eval-bucket", prefix="eval/datasets", client=FakeS3Client())

    examples = store.load("smoke")

    assert len(examples) == 1
    assert examples[0].input == "list pods"
    assert examples[0].expected_intent == "tool_action"
    assert examples[0].expected_answer_contains == ["pod"]


def test_dataset_store_from_env_returns_local_without_bucket(monkeypatch):
    monkeypatch.delenv("EVAL_DATASET_BUCKET", raising=False)

    store = dataset_store_from_env()

    assert isinstance(store, LocalJsonlDatasetStore)


def test_dataset_store_from_env_returns_s3_with_bucket(monkeypatch):
    monkeypatch.setenv("EVAL_DATASET_BUCKET", "eval-bucket")
    monkeypatch.setenv("EVAL_DATASET_PREFIX", "eval/datasets")

    store = dataset_store_from_env(client=FakeS3Client())

    assert isinstance(store, S3DatasetStore)
    assert store.list_datasets() == ["regression", "smoke"]
