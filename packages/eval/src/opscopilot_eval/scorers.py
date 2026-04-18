from __future__ import annotations

import json
import asyncio
import os
import uuid
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.gateway import run_gateway_call
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import (
    LlmMessage,
    LlmRequest,
    LlmResponseFormat,
    LlmTags,
)
from opscopilot_observability import LangfuseAdapter


@dataclass(frozen=True)
class JudgeScore:
    relevance: float
    groundedness: float
    comment: str | None = None


@dataclass(frozen=True)
class RagasScore:
    faithfulness: float
    answer_relevance: float


class LlmJudgeScorer:
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        budget: BudgetEnforcer,
        ledger: CostLedger,
        langfuse: LangfuseAdapter,
    ) -> None:
        self._provider = provider
        self._model_id = model_id
        self._budget = budget
        self._ledger = ledger
        self._langfuse = langfuse

    def score(
        self,
        prompt: str,
        answer: str,
        tool_results: list[Any],
        rag_context: str | None = None,
        session_id: str = "eval",
        run_id: str = "eval",
        trace_id: str | None = None,
    ) -> JudgeScore:
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(
                    role="system",
                    content=(
                        "Score the assistant answer from 1 to 5 for relevance and groundedness. "
                        "Use only the prompt, tool results, optional context, and answer. "
                        "Return JSON with relevance, groundedness, and comment."
                    ),
                ),
                LlmMessage(
                    role="user",
                    content=json.dumps(
                        {
                            "prompt": prompt,
                            "answer": answer,
                            "tool_results": tool_results,
                            "rag_context": rag_context,
                        },
                        default=str,
                    ),
                ),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_judge_schema()),
            temperature=0.0,
            max_tokens=256,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id=session_id, agent_run_id=run_id, agent_node="llm_judge"),
        )
        response = run_gateway_call(
            provider=self._provider,
            request=request,
            budget=self._budget,
            ledger=self._ledger,
        )
        if response.error:
            raise RuntimeError(response.error.message)
        payload = response.output.json or {}
        score = JudgeScore(
            relevance=_read_score(payload, "relevance"),
            groundedness=_read_score(payload, "groundedness"),
            comment=payload.get("comment") if isinstance(payload.get("comment"), str) else None,
        )
        self._langfuse.create_score(
            name="answer_relevance",
            value=score.relevance,
            trace_id=trace_id,
            session_id=session_id,
            comment=score.comment,
            metadata={"agent_node": "llm_judge", "agent_run_id": run_id},
        )
        self._langfuse.create_score(
            name="answer_groundedness",
            value=score.groundedness,
            trace_id=trace_id,
            session_id=session_id,
            comment=score.comment,
            metadata={"agent_node": "llm_judge", "agent_run_id": run_id},
        )
        self._langfuse.flush()
        return score


class RagasScorer:
    def __init__(
        self,
        faithfulness_metric: Any | None = None,
        answer_relevance_metric: Any | None = None,
        langfuse: LangfuseAdapter | None = None,
    ) -> None:
        self._faithfulness_metric = faithfulness_metric
        self._answer_relevance_metric = answer_relevance_metric
        self._langfuse = langfuse

    def score(
        self,
        prompt: str,
        answer: str,
        contexts: list[str],
        session_id: str = "eval",
        run_id: str = "eval",
        trace_id: str | None = None,
    ) -> RagasScore | None:
        clean_contexts = [context for context in contexts if context.strip()]
        if not clean_contexts:
            return None

        payload = {
            "user_input": prompt,
            "response": answer,
            "retrieved_contexts": clean_contexts,
        }
        faithfulness_metric = self._faithfulness_metric or _build_ragas_metric("Faithfulness")
        answer_relevance_metric = self._answer_relevance_metric or _build_ragas_metric("AnswerRelevancy")
        score = RagasScore(
            faithfulness=_read_ragas_score(_run_metric(faithfulness_metric, payload)),
            answer_relevance=_read_ragas_score(_run_metric(answer_relevance_metric, payload)),
        )
        if self._langfuse is not None:
            self._langfuse.create_score(
                name="rag_faithfulness",
                value=score.faithfulness,
                trace_id=trace_id,
                session_id=session_id,
                metadata={"agent_node": "ragas", "agent_run_id": run_id},
            )
            self._langfuse.create_score(
                name="rag_answer_relevance",
                value=score.answer_relevance,
                trace_id=trace_id,
                session_id=session_id,
                metadata={"agent_node": "ragas", "agent_run_id": run_id},
            )
            self._langfuse.flush()
        return score


def _judge_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "relevance": {"type": "number"},
            "groundedness": {"type": "number"},
            "comment": {"type": "string"},
        },
        "required": ["relevance", "groundedness"],
    }


def _read_score(payload: dict, key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise ValueError(f"{key} score is required")
    score = float(value)
    if score < 1 or score > 5:
        raise ValueError(f"{key} score must be between 1 and 5")
    return score


def _build_ragas_metric(name: str) -> Any:
    module = import_module("ragas.metrics.collections")
    metric_class = getattr(module, name)
    llm = _build_ragas_llm()
    if name == "AnswerRelevancy":
        return metric_class(llm=llm, embeddings=_build_ragas_embeddings())
    return metric_class(llm=llm)


def _build_ragas_llm() -> Any:
    model = os.getenv("RAGAS_LLM_MODEL") or os.getenv("LLM_MODEL_ID") or "global.amazon.nova-2-lite-v1:0"
    llm_factory = getattr(import_module("ragas.llms"), "llm_factory")
    return llm_factory(
        _litellm_model_name("bedrock", model),
        provider="bedrock",
        client=_build_litellm_router(model),
        adapter="litellm",
    )


def _build_ragas_embeddings() -> Any:
    model = os.getenv("RAGAS_EMBEDDING_MODEL") or _default_embedding_model()
    embeddings_class = getattr(import_module("ragas.embeddings"), "LiteLLMEmbeddings")
    return embeddings_class(model=_litellm_model_name("bedrock", model), **_bedrock_litellm_params())


def _build_litellm_router(model: str) -> Any:
    router_class = getattr(import_module("litellm"), "Router")
    model_name = _litellm_model_name("bedrock", model)
    return router_class(
        model_list=[
            {
                "model_name": model_name,
                "litellm_params": {
                    "model": model_name,
                    **_bedrock_litellm_params(),
                },
            }
        ]
    )


def _bedrock_litellm_params() -> dict[str, str]:
    region = os.getenv("RAGAS_BEDROCK_REGION") or os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION")
    if not region:
        raise RuntimeError("RAGAS_BEDROCK_REGION, BEDROCK_REGION, or AWS_REGION is required for Bedrock RAGAS scoring")
    params = {"aws_region_name": region}
    optional_env = {
        "aws_access_key_id": "AWS_ACCESS_KEY_ID",
        "aws_secret_access_key": "AWS_SECRET_ACCESS_KEY",
        "aws_session_token": "AWS_SESSION_TOKEN",
        "aws_profile_name": "AWS_PROFILE",
    }
    for key, env_name in optional_env.items():
        value = os.getenv(env_name)
        if value:
            params[key] = value
    return params


def _litellm_model_name(provider: str, model: str) -> str:
    if model.startswith(f"{provider}/"):
        return model
    return f"{provider}/{model}"


def _default_embedding_model() -> str:
    return os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1")


def _run_metric(metric: Any, payload: dict) -> Any:
    return asyncio.run(metric.ascore(**payload))


def _read_ragas_score(result: Any) -> float:
    value = getattr(result, "value", result)
    if not isinstance(value, int | float):
        raise ValueError("ragas score must be numeric")
    score = float(value)
    if score < 0 or score > 1:
        raise ValueError("ragas score must be between 0 and 1")
    return score
