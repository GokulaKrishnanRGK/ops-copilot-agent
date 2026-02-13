from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from opscopilot_api.db import get_db
from opscopilot_api.schemas.runs import AgentRunListResponse, AgentRunResponse
from opscopilot_api.services.run_service import RunService
from opscopilot_db.repositories import AgentRunRepo, SessionRepo

router = APIRouter()


def get_run_service(db: Session = Depends(get_db)) -> RunService:
    return RunService(session_repo=SessionRepo(db=db), run_repo=AgentRunRepo(db=db))


@router.get("", response_model=AgentRunListResponse)
def list_runs(
    session_id: str = Query(...),
    service: RunService = Depends(get_run_service),
) -> AgentRunListResponse:
    try:
        items = service.list_by_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AgentRunListResponse(items=[AgentRunResponse.model_validate(item) for item in items])
