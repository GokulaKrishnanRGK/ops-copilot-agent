from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from opscopilot_api.db import get_db
from opscopilot_api.schemas.runs import (
    AgentRunListResponse,
    AgentRunResponse,
    BudgetMetricsResponse,
    NodeUsageResponse,
    RunMetricsResponse,
    SessionMetricsResponse,
    UsageMetricsResponse,
)
from opscopilot_api.services.run_service import RunService
from opscopilot_db.repositories import AgentRunRepo, BudgetEventRepo, LlmCallRepo, MessageRepo, SessionRepo

router = APIRouter()


def get_run_service(db: Session = Depends(get_db)) -> RunService:
    return RunService(
        session_repo=SessionRepo(db=db),
        run_repo=AgentRunRepo(db=db),
        llm_call_repo=LlmCallRepo(db=db),
        budget_event_repo=BudgetEventRepo(db=db),
        message_repo=MessageRepo(db=db),
    )


@router.get("", response_model=AgentRunListResponse)
def list_runs(
    session_id: str = Query(...),
    service: RunService = Depends(get_run_service),
) -> AgentRunListResponse:
    try:
        items = service.list_by_session(session_id)
        session_metrics = service.metrics_for_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    run_items: list[AgentRunResponse] = []
    for item in items:
        run_metrics = service.metrics_for_run(item.id)
        run_items.append(
            AgentRunResponse(
                id=item.id,
                session_id=item.session_id,
                started_at=item.started_at,
                ended_at=item.ended_at,
                status=item.status,
                config_json=item.config_json,
                metrics=RunMetricsResponse(
                    usage=UsageMetricsResponse(
                        tokens_input=run_metrics.usage.tokens_input,
                        tokens_output=run_metrics.usage.tokens_output,
                        tokens_total=run_metrics.usage.tokens_total,
                        cost_usd=run_metrics.usage.cost_usd,
                        llm_call_count=run_metrics.usage.llm_call_count,
                    ),
                    budget=BudgetMetricsResponse(
                        total_usd=run_metrics.budget.total_usd,
                        delta_usd=run_metrics.budget.delta_usd,
                        event_count=run_metrics.budget.event_count,
                    ),
                    node_usage=[
                        NodeUsageResponse(
                            agent_node=node.agent_node,
                            tokens_input=node.tokens_input,
                            tokens_output=node.tokens_output,
                            tokens_total=node.tokens_total,
                            cost_usd=node.cost_usd,
                            llm_call_count=node.llm_call_count,
                        )
                        for node in run_metrics.node_usage
                    ],
                ),
            )
        )
    return AgentRunListResponse(
        items=run_items,
        session_metrics=SessionMetricsResponse(
            usage=UsageMetricsResponse(
                tokens_input=session_metrics.usage.tokens_input,
                tokens_output=session_metrics.usage.tokens_output,
                tokens_total=session_metrics.usage.tokens_total,
                cost_usd=session_metrics.usage.cost_usd,
                llm_call_count=session_metrics.usage.llm_call_count,
            ),
            budget=BudgetMetricsResponse(
                total_usd=session_metrics.budget.total_usd,
                delta_usd=session_metrics.budget.delta_usd,
                event_count=session_metrics.budget.event_count,
            ),
            run_count=session_metrics.run_count,
        ),
    )
