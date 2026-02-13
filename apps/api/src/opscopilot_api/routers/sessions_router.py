from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from opscopilot_db.repositories import MessageRepo, SessionRepo
from opscopilot_api.db import get_db
from opscopilot_api.schemas.chat import ChatRequest, ChatResponse
from opscopilot_api.schemas.sessions import (
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
    SessionUpdateRequest,
)
from opscopilot_api.services.chat_service import ChatExecutionError, ChatService, SessionNotFoundError
from opscopilot_api.services.event_mapper import agent_run_completed, agent_run_failed, error_event
from opscopilot_api.services.runtime_factory import RuntimeFactory
from opscopilot_api.services.session_service import SessionService
from opscopilot_api.services.sse import encode_sse

router = APIRouter()


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    return SessionService(repo=SessionRepo(db=db))


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(
        session_repo=SessionRepo(db=db),
        message_repo=MessageRepo(db=db),
        runtime_factory=RuntimeFactory(),
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return SessionResponse.model_validate(service.create(title=payload.title))


@router.get("", response_model=SessionListResponse)
def list_sessions(
    service: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    items = [SessionResponse.model_validate(item) for item in service.list()]
    return SessionListResponse(items=items)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    session = service.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return SessionResponse.model_validate(session)


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    payload: SessionUpdateRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    session = service.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    updated = service.update_title(session=session, title=payload.title)
    return SessionResponse.model_validate(updated)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> Response:
    session = service.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    service.delete(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{session_id}/chat", response_model=ChatResponse)
def chat(
    session_id: str,
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        result = service.run(session_id=session_id, prompt=payload.message)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ChatExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return ChatResponse(run_id=result.run_id, answer=result.answer, error=result.error)


@router.post("/{session_id}/chat/stream")
def chat_stream(
    session_id: str,
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    try:
        event_iterator = iter(service.run_stream(session_id=session_id, prompt=payload.message))
        first_event = next(event_iterator)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StopIteration:
        first_event = agent_run_completed(session_id, "unknown")

    def stream():
        yield encode_sse(first_event.get("type", "message"), first_event)
        try:
            for event in event_iterator:
                event_type = event.get("type", "message")
                yield encode_sse(event_type, event)
        except ValueError as exc:
            run_id = first_event.get("agent_run_id", "unknown")
            yield encode_sse("error", error_event(session_id, run_id, "invalid_request", str(exc)))
            yield encode_sse("agent_run.failed", agent_run_failed(session_id, run_id, str(exc), "invalid_request"))
        except Exception as exc:
            run_id = first_event.get("agent_run_id", "unknown")
            yield encode_sse("error", error_event(session_id, run_id, "runtime_error", str(exc)))
            yield encode_sse("agent_run.failed", agent_run_failed(session_id, run_id, str(exc), "runtime_error"))

    return StreamingResponse(stream(), media_type="text/event-stream")
