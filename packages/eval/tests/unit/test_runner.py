from opscopilot_eval.datasets import ExampleRecord
from opscopilot_eval.runner import (
    LangfuseDatasetPusher,
    LangfuseSdkExperimentRunner,
    _answer_contains_evaluator,
    _build_langfuse_evaluators,
    _read_contexts,
)


class FakeLangfuseClient:
    def __init__(self):
        self.datasets = []
        self.items = []
        self.flushed = False

    def create_dataset(self, **kwargs):
        self.datasets.append(kwargs)

    def create_dataset_item(self, **kwargs):
        self.items.append(kwargs)

    def flush(self):
        self.flushed = True

    def get_dataset(self, name):
        return FakeLangfuseDataset(name)


class FakeLangfuseDataset:
    def __init__(self, name):
        self.name = name
        self.run_kwargs = None

    def run_experiment(self, **kwargs):
        self.run_kwargs = kwargs
        return type("Experiment", (), {"dataset_run_url": "http://langfuse.local/dataset-runs/one"})()


def test_langfuse_dataset_pusher_upserts_dataset_items():
    client = FakeLangfuseClient()
    pusher = LangfuseDatasetPusher(client)

    pushed = pusher.push(
        "smoke",
        [ExampleRecord("list pods", "tool_action", ["pod"])],
    )

    assert pushed == 1
    assert client.datasets[0]["name"] == "smoke"
    assert client.items[0]["dataset_name"] == "smoke"
    assert client.items[0]["input"] == "list pods"
    assert client.items[0]["expected_output"]["expected_intent"] == "tool_action"
    assert client.flushed


def test_langfuse_sdk_runner_uses_dataset_without_app_api(monkeypatch):
    client = FakeLangfuseClient()
    dataset = client.get_dataset("smoke")
    client.get_dataset = lambda _name: dataset
    runner = LangfuseSdkExperimentRunner(client)

    url = runner.run(
        dataset_name="smoke",
        experiment_name="smoke-run",
        model="model-a",
        prompt_version="v1",
    )

    assert url == "http://langfuse.local/dataset-runs/one"
    assert dataset.run_kwargs["name"] == "smoke-run"
    assert dataset.run_kwargs["metadata"]["runner"] == "langfuse_sdk"
    assert len(dataset.run_kwargs["evaluators"]) >= 2


def test_answer_contains_evaluator_returns_langfuse_evaluation():
    result = _answer_contains_evaluator(
        input="list pods",
        output="one pod",
        expected_output={"expected_answer_contains": ["pod"]},
    )

    assert result.name == "answer_contains"
    assert result.value == 1.0


def test_langfuse_evaluators_can_disable_llm_and_ragas(monkeypatch):
    monkeypatch.setenv("EVAL_LLM_JUDGE_ENABLED", "0")
    monkeypatch.setenv("EVAL_RAGAS_ENABLED", "0")

    assert [evaluator.__name__ for evaluator in _build_langfuse_evaluators()] == [
        "_answer_contains_evaluator",
        "_success_evaluator",
    ]


def test_read_contexts_from_expected_output_or_metadata():
    assert _read_contexts({"contexts": ["ctx"]}, None) == ["ctx"]
    assert _read_contexts({}, {"contexts": ["meta"]}) == ["meta"]
