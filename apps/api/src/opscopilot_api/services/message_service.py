from opscopilot_db import models, repositories


class MessageService:
    def __init__(
        self,
        session_repo: repositories.SessionRepository,
        message_repo: repositories.MessageRepository,
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo

    def list_by_session(self, session_id: str) -> list[models.Message]:
        session = self._session_repo.get(session_id)
        if session is None:
            raise ValueError("session not found")
        return list(self._message_repo.list_by_session(session_id))
