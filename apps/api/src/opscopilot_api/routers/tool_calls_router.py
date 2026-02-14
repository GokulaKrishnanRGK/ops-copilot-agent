from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from opscopilot_api.db import get_db
from opscopilot_api.schemas.tool_calls import ToolCallListResponse, ToolCallResponse
from opscopilot_api.services.tool_call_service import ToolCallService
from opscopilot_db.repositories import AgentRunRepo, SessionRepo, ToolCallRepo

router = APIRouter()


def get_tool_call_service(db: Session = Depends(get_db)) -> ToolCallService:
    return ToolCallService(
        session_repo=SessionRepo(db=db),
        run_repo=AgentRunRepo(db=db),
        tool_call_repo=ToolCallRepo(db=db),
    )


def _log_text_for_call(tool_call) -> str | None:
    if tool_call.tool_name != "k8s.get_pod_logs":
        return None
    payload = tool_call.result_json
    if not isinstance(payload, dict):
        return None
    value = payload.get("text")
    if isinstance(value, str):
        return value
    fallback = payload.get("logs")
    if isinstance(fallback, str):
        return fallback
    return None


@router.get("", response_model=ToolCallListResponse)
def list_tool_calls(
    run_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    run_ids: str | None = Query(default=None),
    service: ToolCallService = Depends(get_tool_call_service),
) -> ToolCallListResponse:
    parsed_run_ids: list[str] = []
    if isinstance(run_ids, str) and run_ids.strip():
        parsed_run_ids = [value.strip() for value in run_ids.split(",") if value.strip()]

    if not run_id and not session_id and not parsed_run_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="run_id, run_ids, or session_id is required",
        )
    try:
        if run_id:
            items = service.list_by_run(run_id)
        elif parsed_run_ids:
            items = service.list_by_runs(parsed_run_ids)
        else:
            items = service.list_by_session(session_id or "")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ToolCallListResponse(
        items=[
            ToolCallResponse(
                id=item.id,
                agent_run_id=item.agent_run_id,
                tool_name=item.tool_name,
                status=item.status,
                latency_ms=item.latency_ms,
                bytes_returned=item.bytes_returned,
                truncated=item.truncated,
                error_message=item.error_message,
                created_at=item.created_at,
                log_text=_log_text_for_call(item),
            )
            for item in items
        ]
    )
