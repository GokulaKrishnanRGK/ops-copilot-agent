from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from opscopilot_api.db import get_db
from opscopilot_api.schemas.messages import MessageListResponse, MessageResponse
from opscopilot_api.services.message_service import MessageService
from opscopilot_db.repositories import MessageRepo, SessionRepo

router = APIRouter()


def get_message_service(db: Session = Depends(get_db)) -> MessageService:
    return MessageService(session_repo=SessionRepo(db=db), message_repo=MessageRepo(db=db))


@router.get("", response_model=MessageListResponse)
def list_messages(
    session_id: str = Query(...),
    service: MessageService = Depends(get_message_service),
) -> MessageListResponse:
    try:
        items = service.list_by_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MessageListResponse(items=[MessageResponse.model_validate(item) for item in items])
