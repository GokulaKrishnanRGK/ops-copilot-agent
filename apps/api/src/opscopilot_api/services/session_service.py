from datetime import datetime, timezone
from uuid import uuid4

from opscopilot_db import models, repositories


class SessionService:
    def __init__(self, repo: repositories.SessionRepository) -> None:
        self._repo = repo

    def create(self, title: str | None = None) -> models.Session:
        now = datetime.now(timezone.utc)
        record = models.Session(
            id=str(uuid4()),
            title=title,
            created_at=now,
            updated_at=now,
        )
        return self._repo.create(record)

    def list(self) -> list[models.Session]:
        return list(self._repo.list())

    def get(self, session_id: str) -> models.Session | None:
        return self._repo.get(session_id)

    def update_title(self, session: models.Session, title: str | None) -> models.Session:
        session.title = title
        session.updated_at = datetime.now(timezone.utc)
        return self._repo.update(session)

    def delete(self, session_id: str) -> None:
        self._repo.delete(session_id)
