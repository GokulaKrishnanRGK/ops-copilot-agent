from collections.abc import Iterable

from sqlalchemy.orm import Session as SQLAlchemySession

from opscopilot_db import models


class SessionRepo:
    def __init__(self, db: SQLAlchemySession) -> None:
        self._db = db

    def create(self, session: models.Session) -> models.Session:
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def get(self, session_id: str) -> models.Session | None:
        return self._db.query(models.Session).filter(models.Session.id == session_id).one_or_none()

    def list(self) -> Iterable[models.Session]:
        return self._db.query(models.Session).order_by(models.Session.created_at.desc()).all()

    def update(self, session: models.Session) -> models.Session:
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def delete(self, session_id: str) -> None:
        session = self.get(session_id)
        if session is None:
            return
        self._db.delete(session)
        self._db.commit()
