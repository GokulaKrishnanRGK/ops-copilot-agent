from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
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
        self._langfuse.score_current_trace(
            name="answer_relevance",
            value=score.relevance,
            comment=score.comment,
            metadata={"agent_node": "llm_judge"},
        )
        self._langfuse.score_current_trace(
            name="answer_groundedness",
            value=score.groundedness,
            comment=score.comment,
            metadata={"agent_node": "llm_judge"},
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
