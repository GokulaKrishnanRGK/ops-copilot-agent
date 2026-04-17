from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from statistics import mean
from typing import Any, Protocol
from urllib import request

from opscopilot_eval.datasets import ExampleRecord


@dataclass(frozen=True)
class AgentOutput:
    answer: str | None
    run_id: str | None
    error: dict | None


@dataclass(frozen=True)
class EvalCaseResult:
    input: str
    expected_intent: str
    expected_answer_contains: list[str]
    answer: str | None
    run_id: str | None
    error: dict | None
    latency_ms: float
    answer_contains_score: float
    success_score: float


@dataclass(frozen=True)
class EvalSummary:
    dataset: str
    experiment_name: str
    prompt_version: str
    model: str
    total_examples: int
    successful_examples: int
    metrics: dict[str, dict[str, float]]
    results: list[EvalCaseResult]
    langfuse_experiment_url: str | None


class AgentClient(Protocol):
    def run(self, prompt: str) -> AgentOutput: ...


class ExperimentUploader(Protocol):
    def upload(
        self,
        *,
        dataset_name: str,
        experiment_name: str,
        prompt_version: str,
        model: str,
        results: list[EvalCaseResult],
    ) -> str | None:
        ...


class NoOpExperimentUploader:
    def upload(self, **kwargs) -> str | None:
        return None


class HttpAgentClient:
    def __init__(self, api_url: str, timeout_seconds: float = 120.0) -> None:
        self._api_url = api_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def run(self, prompt: str) -> AgentOutput:
        session = self._post("/sessions", {"title": "Eval run"})
        session_id = session["id"]
        response = self._post(f"/sessions/{session_id}/chat", {"message": prompt})
        return AgentOutput(
            answer=response.get("answer"),
            run_id=response.get("run_id"),
            error=response.get("error"),
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self._api_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self._timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class LangfuseExperimentUploader:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_env(cls) -> ExperimentUploader:
        if not os.getenv("LANGFUSE_HOST"):
            return NoOpExperimentUploader()
        if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
            return NoOpExperimentUploader()
        module = import_module("langfuse")
        get_client = getattr(module, "get_client", None)
        if callable(get_client):
            return cls(get_client())
        client_class = getattr(module, "Langfuse")
        return cls(
            client_class(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST"),
            )
        )

    def upload(
        self,
        *,
        dataset_name: str,
        experiment_name: str,
        prompt_version: str,
        model: str,
        results: list[EvalCaseResult],
    ) -> str | None:
        indexed_results = {index: result for index, result in enumerate(results)}
        data = [
            {
                "input": result.input,
                "expected_output": {
                    "expected_intent": result.expected_intent,
                    "expected_answer_contains": result.expected_answer_contains,
                },
                "metadata": {
                    "eval_index": index,
                    "dataset": dataset_name,
                    "prompt_version": prompt_version,
                    "model": model,
                    "run_id": result.run_id,
                    "success_score": result.success_score,
                    "answer_contains_score": result.answer_contains_score,
                    "latency_ms": result.latency_ms,
                },
            }
            for index, result in indexed_results.items()
        ]

        def task(*, item, **kwargs):
            metadata = _read_item_field(item, "metadata") or {}
            index = metadata["eval_index"]
            return indexed_results[index].answer or ""

        experiment = self._client.run_experiment(
            name=experiment_name,
            description=f"Ops Copilot eval run for {dataset_name}",
            data=data,
            task=task,
        )
        flush = getattr(self._client, "flush", None)
        if callable(flush):
            flush()
        url = getattr(experiment, "url", None)
        if isinstance(url, str) and url:
            return url
        return None


class EvalRunner:
    def __init__(
        self,
        agent_client: AgentClient,
        experiment_uploader: ExperimentUploader | None = None,
    ) -> None:
        self._agent_client = agent_client
        self._experiment_uploader = experiment_uploader or NoOpExperimentUploader()

    def run(
        self,
        *,
        dataset_name: str,
        examples: list[ExampleRecord],
        prompt_version: str,
        model: str,
        experiment_name: str | None = None,
    ) -> EvalSummary:
        resolved_experiment_name = experiment_name or _default_experiment_name(dataset_name)
        results = [self._run_example(example) for example in examples]
        url = self._experiment_uploader.upload(
            dataset_name=dataset_name,
            experiment_name=resolved_experiment_name,
            prompt_version=prompt_version,
            model=model,
            results=results,
        )
        return EvalSummary(
            dataset=dataset_name,
            experiment_name=resolved_experiment_name,
            prompt_version=prompt_version,
            model=model,
            total_examples=len(results),
            successful_examples=sum(1 for result in results if result.error is None),
            metrics=_summarize_metrics(results),
            results=results,
            langfuse_experiment_url=url,
        )

    def _run_example(self, example: ExampleRecord) -> EvalCaseResult:
        started = time.perf_counter()
        output = self._agent_client.run(example.input)
        latency_ms = (time.perf_counter() - started) * 1000.0
        answer = output.answer or ""
        contains_matches = [
            expected.lower() in answer.lower() for expected in example.expected_answer_contains
        ]
        answer_contains_score = 1.0 if all(contains_matches) else 0.0
        success_score = 1.0 if output.error is None else 0.0
        return EvalCaseResult(
            input=example.input,
            expected_intent=example.expected_intent,
            expected_answer_contains=example.expected_answer_contains,
            answer=output.answer,
            run_id=output.run_id,
            error=output.error,
            latency_ms=latency_ms,
            answer_contains_score=answer_contains_score,
            success_score=success_score,
        )


def write_summary(summary: EvalSummary, path: str | Path) -> Path:
    resolved_path = Path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(summary)
    resolved_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return resolved_path


def default_summary_path(dataset_name: str, experiment_name: str) -> Path:
    return Path("packages/eval/results") / f"{dataset_name}-{experiment_name}.json"


def _summarize_metrics(results: list[EvalCaseResult]) -> dict[str, dict[str, float]]:
    return {
        "answer_contains_score": _aggregate([result.answer_contains_score for result in results]),
        "success_score": _aggregate([result.success_score for result in results]),
        "latency_ms": _aggregate([result.latency_ms for result in results]),
    }


def _aggregate(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "p95": 0.0}
    sorted_values = sorted(values)
    p95_index = min(len(sorted_values) - 1, int(len(sorted_values) * 0.95))
    return {"mean": mean(sorted_values), "p95": sorted_values[p95_index]}


def _default_experiment_name(dataset_name: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{dataset_name}-{timestamp}"


def _read_item_field(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field)
