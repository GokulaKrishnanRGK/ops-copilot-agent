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

    def list(self, limit: int | None = None, offset: int = 0) -> Iterable[models.Session]:
        query = self._db.query(models.Session).order_by(models.Session.created_at.desc()).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

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
