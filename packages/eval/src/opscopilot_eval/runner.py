from __future__ import annotations

import json
import os
import uuid
from importlib import import_module
from typing import Any

from opscopilot_eval.datasets import ExampleRecord
from opscopilot_eval.scorers import LlmJudgeScorer, RagasScorer
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.gateway import run_gateway_call
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags
from opscopilot_observability import NoOpLangfuseAdapter


class LangfuseDatasetPusher:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_env(cls) -> "LangfuseDatasetPusher":
        if not os.getenv("LANGFUSE_HOST"):
            raise RuntimeError("LANGFUSE_HOST is required to push datasets")
        if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
            raise RuntimeError("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required to push datasets")
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

    def push(self, dataset_name: str, examples: list[ExampleRecord]) -> int:
        create_dataset = getattr(self._client, "create_dataset", None)
        if callable(create_dataset):
            try:
                create_dataset(name=dataset_name, description=f"Ops Copilot eval dataset {dataset_name}")
            except Exception:
                pass
        create_dataset_item = getattr(self._client, "create_dataset_item", None)
        if not callable(create_dataset_item):
            raise RuntimeError("Langfuse client does not support create_dataset_item")
        for index, example in enumerate(examples):
            create_dataset_item(
                dataset_name=dataset_name,
                input=example.input,
                expected_output={
                    "expected_intent": example.expected_intent,
                    "expected_answer_contains": example.expected_answer_contains,
                },
                metadata={"eval_index": index, "dataset": dataset_name},
                id=f"{dataset_name}-{index}",
            )
        flush = getattr(self._client, "flush", None)
        if callable(flush):
            flush()
        return len(examples)


class LangfuseSdkExperimentRunner:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_env(cls) -> "LangfuseSdkExperimentRunner":
        if not os.getenv("LANGFUSE_HOST"):
            raise RuntimeError("LANGFUSE_HOST is required to run Langfuse experiments")
        if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
            raise RuntimeError("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required to run Langfuse experiments")
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

    def run(
        self,
        *,
        dataset_name: str,
        experiment_name: str,
        model: str,
        prompt_version: str,
    ) -> str | None:
        dataset = self._client.get_dataset(dataset_name)
        task = _build_langfuse_task(model=model, prompt_version=prompt_version)
        experiment = dataset.run_experiment(
            name=experiment_name,
            description=f"Ops Copilot SDK-only eval run for {dataset_name}",
            task=task,
            evaluators=_build_langfuse_evaluators(),
            metadata={
                "dataset": dataset_name,
                "model": model,
                "prompt_version": prompt_version,
                "runner": "langfuse_sdk",
            },
        )
        flush = getattr(self._client, "flush", None)
        if callable(flush):
            flush()
        url = getattr(experiment, "url", None)
        if isinstance(url, str) and url:
            return url
        dataset_run_url = getattr(experiment, "dataset_run_url", None)
        if isinstance(dataset_run_url, str) and dataset_run_url:
            return dataset_run_url
        return None


def _build_langfuse_task(*, model: str, prompt_version: str):
    provider = BedrockProvider()
    budget = BudgetEnforcer(BudgetState(max_usd=_read_eval_budget(), total_usd=0.0))
    ledger = CostLedger()

    def task(*, item, **kwargs):
        prompt = _read_item_input(item)
        request = LlmRequest(
            model_id=model,
            messages=[
                LlmMessage(
                    role="system",
                    content=(
                        "You are evaluating Ops Copilot behavior against a dataset item. "
                        "Answer the user query directly and concisely."
                    ),
                ),
                LlmMessage(role="user", content=prompt),
            ],
            response_format=LlmResponseFormat(type="text", schema=None),
            temperature=0.0,
            max_tokens=_read_int("EVAL_TASK_MAX_TOKENS", 512),
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="langfuse_eval", agent_run_id="langfuse_eval", agent_node="eval_task"),
        )
        response = run_gateway_call(provider=provider, request=request, budget=budget, ledger=ledger)
        if response.error:
            raise RuntimeError(response.error.message)
        return response.output.text or json.dumps(response.output.json or {}, default=str)

    return task


def _build_langfuse_evaluators() -> list[Any]:
    evaluators = [_answer_contains_evaluator, _success_evaluator]
    if os.getenv("EVAL_LLM_JUDGE_ENABLED", "1") != "0":
        evaluators.append(_build_llm_judge_evaluator())
    if os.getenv("EVAL_RAGAS_ENABLED", "1") != "0":
        evaluators.append(_ragas_evaluator)
    return evaluators


def _answer_contains_evaluator(*, input, output, expected_output=None, **kwargs):
    evaluation_class = getattr(import_module("langfuse"), "Evaluation")
    expected = _expected_answer_contains(expected_output)
    answer = output if isinstance(output, str) else ""
    value = 1.0 if all(item.lower() in answer.lower() for item in expected) else 0.0
    return evaluation_class(name="answer_contains", value=value)


def _success_evaluator(*, input, output, expected_output=None, **kwargs):
    evaluation_class = getattr(import_module("langfuse"), "Evaluation")
    return evaluation_class(name="eval_success", value=1.0 if isinstance(output, str) and output else 0.0)


def _build_llm_judge_evaluator():
    scorer = LlmJudgeScorer(
        provider=BedrockProvider(),
        model_id=os.getenv("EVAL_JUDGE_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0"),
        budget=BudgetEnforcer(BudgetState(max_usd=_read_eval_budget(), total_usd=0.0)),
        ledger=CostLedger(),
        langfuse=NoOpLangfuseAdapter(),
    )

    def evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
        evaluation_class = getattr(import_module("langfuse"), "Evaluation")
        score = scorer.score(
            prompt=input if isinstance(input, str) else json.dumps(input, default=str),
            answer=output if isinstance(output, str) else json.dumps(output, default=str),
            tool_results=[],
            rag_context=None,
            session_id="langfuse_eval",
            run_id="langfuse_eval",
        )
        return [
            evaluation_class(name="answer_relevance", value=score.relevance, comment=score.comment),
            evaluation_class(name="answer_groundedness", value=score.groundedness, comment=score.comment),
        ]

    return evaluator


def _ragas_evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
    contexts = _read_contexts(expected_output, metadata)
    if not contexts:
        return []
    evaluation_class = getattr(import_module("langfuse"), "Evaluation")
    score = RagasScorer(langfuse=NoOpLangfuseAdapter()).score(
        prompt=input if isinstance(input, str) else json.dumps(input, default=str),
        answer=output if isinstance(output, str) else json.dumps(output, default=str),
        contexts=contexts,
        session_id="langfuse_eval",
        run_id="langfuse_eval",
    )
    if score is None:
        return []
    return [
        evaluation_class(name="rag_faithfulness", value=score.faithfulness),
        evaluation_class(name="rag_answer_relevance", value=score.answer_relevance),
    ]


def _read_item_input(item: Any) -> str:
    value = item.get("input") if isinstance(item, dict) else getattr(item, "input", None)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("Langfuse dataset item input must be a non-empty string")
    return value


def _expected_answer_contains(expected_output: Any) -> list[str]:
    if not isinstance(expected_output, dict):
        return []
    value = expected_output.get("expected_answer_contains")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _read_contexts(expected_output: Any, metadata: Any) -> list[str]:
    for source in (expected_output, metadata):
        if isinstance(source, dict):
            value = source.get("contexts")
            if isinstance(value, list):
                return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def _read_eval_budget() -> float:
    value = os.getenv("EVAL_LLM_JUDGE_BUDGET_USD", os.getenv("LLM_MAX_BUDGET_USD", "1.0"))
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError("EVAL_LLM_JUDGE_BUDGET_USD must be a number") from exc


def _read_int(name: str, default_value: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default_value
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
