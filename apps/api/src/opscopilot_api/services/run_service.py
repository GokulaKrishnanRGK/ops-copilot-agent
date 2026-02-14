from dataclasses import dataclass
from decimal import Decimal

from opscopilot_db import models, repositories


@dataclass(frozen=True)
class UsageMetrics:
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    llm_call_count: int


@dataclass(frozen=True)
class BudgetMetrics:
    total_usd: float
    delta_usd: float
    event_count: int


@dataclass(frozen=True)
class NodeUsageMetrics:
    agent_node: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    llm_call_count: int


@dataclass(frozen=True)
class RunMetrics:
    usage: UsageMetrics
    budget: BudgetMetrics
    node_usage: list[NodeUsageMetrics]


@dataclass(frozen=True)
class SessionMetrics:
    usage: UsageMetrics
    budget: BudgetMetrics
    run_count: int


def _to_float(value: Decimal | float | int) -> float:
    return float(value)


class RunService:
    def __init__(
        self,
        session_repo: repositories.SessionRepository,
        run_repo: repositories.AgentRunRepository,
        llm_call_repo: repositories.LlmCallRepository,
        budget_event_repo: repositories.BudgetEventRepository,
    ) -> None:
        self._session_repo = session_repo
        self._run_repo = run_repo
        self._llm_call_repo = llm_call_repo
        self._budget_event_repo = budget_event_repo

    def list_by_session(self, session_id: str) -> list[models.AgentRun]:
        session = self._session_repo.get(session_id)
        if session is None:
            raise ValueError("session not found")
        return list(self._run_repo.list_by_session(session_id))

    def metrics_for_run(self, run_id: str) -> RunMetrics:
        llm_calls = list(self._llm_call_repo.list_by_run(run_id))
        budget_events = list(self._budget_event_repo.list_by_run(run_id))
        return self._build_run_metrics(llm_calls=llm_calls, budget_events=budget_events)

    def metrics_for_session(self, session_id: str) -> SessionMetrics:
        runs = self.list_by_session(session_id)
        total_tokens_input = 0
        total_tokens_output = 0
        total_cost_usd = 0.0
        total_llm_calls = 0
        total_budget_delta_usd = 0.0
        total_budget_events = 0
        latest_budget_total_usd = 0.0

        for run in runs:
            llm_calls = list(self._llm_call_repo.list_by_run(run.id))
            budget_events = list(self._budget_event_repo.list_by_run(run.id))

            for call in llm_calls:
                total_tokens_input += call.tokens_input
                total_tokens_output += call.tokens_output
                total_cost_usd += _to_float(call.cost_usd)
                total_llm_calls += 1

            if budget_events:
                total_budget_delta_usd += sum(_to_float(item.delta_usd) for item in budget_events)
                total_budget_events += len(budget_events)
                latest_budget_total_usd = _to_float(budget_events[-1].total_usd)

        usage = UsageMetrics(
            tokens_input=total_tokens_input,
            tokens_output=total_tokens_output,
            tokens_total=total_tokens_input + total_tokens_output,
            cost_usd=total_cost_usd,
            llm_call_count=total_llm_calls,
        )
        budget = BudgetMetrics(
            total_usd=latest_budget_total_usd,
            delta_usd=total_budget_delta_usd,
            event_count=total_budget_events,
        )
        return SessionMetrics(usage=usage, budget=budget, run_count=len(runs))

    def _build_run_metrics(
        self,
        llm_calls: list[models.LlmCall],
        budget_events: list[models.BudgetEvent],
    ) -> RunMetrics:
        tokens_input = sum(item.tokens_input for item in llm_calls)
        tokens_output = sum(item.tokens_output for item in llm_calls)
        cost_usd = sum(_to_float(item.cost_usd) for item in llm_calls)
        usage = UsageMetrics(
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_input + tokens_output,
            cost_usd=cost_usd,
            llm_call_count=len(llm_calls),
        )

        if budget_events:
            budget_total_usd = _to_float(budget_events[-1].total_usd)
            budget_delta_usd = sum(_to_float(item.delta_usd) for item in budget_events)
        else:
            budget_total_usd = 0.0
            budget_delta_usd = 0.0
        budget = BudgetMetrics(
            total_usd=budget_total_usd,
            delta_usd=budget_delta_usd,
            event_count=len(budget_events),
        )

        node_map: dict[str, NodeUsageMetrics] = {}
        for item in llm_calls:
            existing = node_map.get(item.agent_node)
            if existing is None:
                node_map[item.agent_node] = NodeUsageMetrics(
                    agent_node=item.agent_node,
                    tokens_input=item.tokens_input,
                    tokens_output=item.tokens_output,
                    tokens_total=item.tokens_input + item.tokens_output,
                    cost_usd=_to_float(item.cost_usd),
                    llm_call_count=1,
                )
                continue
            tokens_in = existing.tokens_input + item.tokens_input
            tokens_out = existing.tokens_output + item.tokens_output
            node_map[item.agent_node] = NodeUsageMetrics(
                agent_node=item.agent_node,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                tokens_total=tokens_in + tokens_out,
                cost_usd=existing.cost_usd + _to_float(item.cost_usd),
                llm_call_count=existing.llm_call_count + 1,
            )

        node_usage = sorted(node_map.values(), key=lambda item: item.cost_usd, reverse=True)
        return RunMetrics(usage=usage, budget=budget, node_usage=node_usage)
