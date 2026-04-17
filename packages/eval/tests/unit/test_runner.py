import json

from opscopilot_eval.datasets import ExampleRecord
from opscopilot_eval.runner import AgentOutput, EvalRunner, write_summary


class FakeAgentClient:
    def __init__(self):
        self.prompts = []

    def run(self, prompt):
        self.prompts.append(prompt)
        return AgentOutput(answer=f"{prompt} pod", run_id=f"run-{len(self.prompts)}", error=None)


class FakeExperimentUploader:
    def __init__(self):
        self.calls = []

    def upload(self, **kwargs):
        self.calls.append(kwargs)
        return "http://langfuse.local/experiments/one"


def test_eval_runner_summarizes_uploads_and_writes_json(tmp_path):
    agent = FakeAgentClient()
    uploader = FakeExperimentUploader()
    runner = EvalRunner(agent_client=agent, experiment_uploader=uploader)
    examples = [
        ExampleRecord("list pods", "tool_action", ["pod"]),
        ExampleRecord("describe deployment", "tool_action", ["missing"]),
    ]

    summary = runner.run(
        dataset_name="smoke",
        examples=examples,
        prompt_version="v1",
        model="model-a",
        experiment_name="smoke-run",
    )
    path = write_summary(summary, tmp_path / "summary.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert agent.prompts == ["list pods", "describe deployment"]
    assert summary.total_examples == 2
    assert summary.successful_examples == 2
    assert summary.metrics["success_score"]["mean"] == 1.0
    assert summary.metrics["answer_contains_score"]["mean"] == 0.5
    assert summary.langfuse_experiment_url == "http://langfuse.local/experiments/one"
    assert uploader.calls[0]["dataset_name"] == "smoke"
    assert payload["results"][0]["run_id"] == "run-1"
