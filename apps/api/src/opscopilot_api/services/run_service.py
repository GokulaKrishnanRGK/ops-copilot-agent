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
    max_usd: float | None
    remaining_usd: float | None
    status: str


@dataclass(frozen=True)
class NodeUsageMetrics:
    agent_node: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    llm_call_count: int


@dataclass(frozen=True)
class ModelUsageMetrics:
    provider: str
    model_id: str
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
    model_usage: list[ModelUsageMetrics]


@dataclass(frozen=True)
class SessionMetrics:
    usage: UsageMetrics
    budget: BudgetMetrics
    run_count: int


def _to_float(value: Decimal | float | int) -> float:
    return float(value)


def _budget_max_usd(config_json: dict) -> float | None:
    budget = config_json.get("budget")
    if not isinstance(budget, dict):
        return None
    value = budget.get("max_usd")
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    return None


def _budget_metrics(total_usd: float, delta_usd: float, event_count: int, max_usd: float | None) -> BudgetMetrics:
    if max_usd is None:
        return BudgetMetrics(
            total_usd=total_usd,
            delta_usd=delta_usd,
            event_count=event_count,
            max_usd=None,
            remaining_usd=None,
            status="unknown",
        )
    remaining_usd = max(max_usd - total_usd, 0.0)
    if total_usd > max_usd:
        status = "exceeded"
    elif remaining_usd == 0:
        status = "exhausted"
    else:
        status = "available"
    return BudgetMetrics(
        total_usd=total_usd,
        delta_usd=delta_usd,
        event_count=event_count,
        max_usd=max_usd,
        remaining_usd=remaining_usd,
        status=status,
    )


def _provider_for_call(call: models.LlmCall) -> str:
    metadata = call.metadata_json if isinstance(call.metadata_json, dict) else {}
    provider = metadata.get("provider")
    if isinstance(provider, str) and provider:
        return provider
    if "/" in call.model_id:
        prefix = call.model_id.split("/", 1)[0]
        if prefix:
            return prefix
    return "unknown"


class RunService:
    def __init__(
        self,
        session_repo: repositories.SessionRepository,
        run_repo: repositories.AgentRunRepository,
        llm_call_repo: repositories.LlmCallRepository,
        budget_event_repo: repositories.BudgetEventRepository,
        message_repo: repositories.MessageRepository | None = None,
    ) -> None:
        self._session_repo = session_repo
        self._run_repo = run_repo
        self._llm_call_repo = llm_call_repo
        self._budget_event_repo = budget_event_repo
        self._message_repo = message_repo

    def list_by_session(self, session_id: str) -> list[models.AgentRun]:
        session = self._session_repo.get(session_id)
        if session is None:
            raise ValueError("session not found")
        return list(self._run_repo.list_by_session(session_id))

    def metrics_for_run(self, run_id: str) -> RunMetrics:
        run = self._run_repo.get(run_id)
        config_json = run.config_json if run is not None else {}
        llm_calls = list(self._llm_call_repo.list_by_run(run_id))
        budget_events = list(self._budget_event_repo.list_by_run(run_id))
        return self._build_run_metrics(
            llm_calls=llm_calls,
            budget_events=budget_events,
            budget_max_usd=_budget_max_usd(config_json),
        )

    def metrics_for_session(self, session_id: str) -> SessionMetrics:
        runs = self.list_by_session(session_id)
        total_tokens_input = 0
        total_tokens_output = 0
        total_cost_usd = 0.0
        total_llm_calls = 0
        total_budget_delta_usd = 0.0
        total_budget_events = 0
        latest_budget_total_usd = 0.0
        latest_budget_max_usd: float | None = None

        for run in runs:
            llm_calls = list(self._llm_call_repo.list_by_run(run.id))
            budget_events = list(self._budget_event_repo.list_by_run(run.id))
            run_budget_max_usd = _budget_max_usd(run.config_json)
            if run_budget_max_usd is not None:
                latest_budget_max_usd = run_budget_max_usd

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
        budget = _budget_metrics(
            total_usd=latest_budget_total_usd,
            delta_usd=total_budget_delta_usd,
            event_count=total_budget_events,
            max_usd=latest_budget_max_usd,
        )
        run_count = len(runs)
        if run_count == 0:
            run_count = self._fallback_run_count_from_messages(session_id)
        return SessionMetrics(usage=usage, budget=budget, run_count=run_count)

    def _fallback_run_count_from_messages(self, session_id: str) -> int:
        if self._message_repo is None:
            return 0
        run_ids: set[str] = set()
        for message in self._message_repo.list_by_session(session_id):
            metadata = message.metadata_json if isinstance(message.metadata_json, dict) else None
            if metadata is None:
                continue
            run_id = metadata.get("run_id")
            if isinstance(run_id, str) and run_id:
                run_ids.add(run_id)
        return len(run_ids)

    def _build_run_metrics(
        self,
        llm_calls: list[models.LlmCall],
        budget_events: list[models.BudgetEvent],
        budget_max_usd: float | None,
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
        budget = _budget_metrics(
            total_usd=budget_total_usd,
            delta_usd=budget_delta_usd,
            event_count=len(budget_events),
            max_usd=budget_max_usd,
        )

        node_map: dict[str, NodeUsageMetrics] = {}
        model_map: dict[tuple[str, str], ModelUsageMetrics] = {}
        for item in llm_calls:
            existing_node = node_map.get(item.agent_node)
            if existing_node is None:
                node_map[item.agent_node] = NodeUsageMetrics(
                    agent_node=item.agent_node,
                    tokens_input=item.tokens_input,
                    tokens_output=item.tokens_output,
                    tokens_total=item.tokens_input + item.tokens_output,
                    cost_usd=_to_float(item.cost_usd),
                    llm_call_count=1,
                )
            else:
                tokens_in = existing_node.tokens_input + item.tokens_input
                tokens_out = existing_node.tokens_output + item.tokens_output
                node_map[item.agent_node] = NodeUsageMetrics(
                    agent_node=item.agent_node,
                    tokens_input=tokens_in,
                    tokens_output=tokens_out,
                    tokens_total=tokens_in + tokens_out,
                    cost_usd=existing_node.cost_usd + _to_float(item.cost_usd),
                    llm_call_count=existing_node.llm_call_count + 1,
                )
            provider = _provider_for_call(item)
            model_key = (provider, item.model_id)
            model_existing = model_map.get(model_key)
            if model_existing is None:
                model_map[model_key] = ModelUsageMetrics(
                    provider=provider,
                    model_id=item.model_id,
                    tokens_input=item.tokens_input,
                    tokens_output=item.tokens_output,
                    tokens_total=item.tokens_input + item.tokens_output,
                    cost_usd=_to_float(item.cost_usd),
                    llm_call_count=1,
                )
                continue
            model_tokens_in = model_existing.tokens_input + item.tokens_input
            model_tokens_out = model_existing.tokens_output + item.tokens_output
            model_map[model_key] = ModelUsageMetrics(
                provider=provider,
                model_id=item.model_id,
                tokens_input=model_tokens_in,
                tokens_output=model_tokens_out,
                tokens_total=model_tokens_in + model_tokens_out,
                cost_usd=model_existing.cost_usd + _to_float(item.cost_usd),
                llm_call_count=model_existing.llm_call_count + 1,
            )

        node_usage = sorted(node_map.values(), key=lambda item: item.cost_usd, reverse=True)
        model_usage = sorted(model_map.values(), key=lambda item: item.cost_usd, reverse=True)
        return RunMetrics(usage=usage, budget=budget, node_usage=node_usage, model_usage=model_usage)
