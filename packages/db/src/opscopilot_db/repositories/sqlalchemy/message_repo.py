from collections.abc import Iterable

from sqlalchemy.orm import Session as SQLAlchemySession

from opscopilot_db import models


class MessageRepo:
    def __init__(self, db: SQLAlchemySession) -> None:
        self._db = db

    def create(self, message: models.Message) -> models.Message:
        self._db.add(message)
        self._db.commit()
        self._db.refresh(message)
        return message

    def get(self, message_id: str) -> models.Message | None:
        return self._db.query(models.Message).filter(models.Message.id == message_id).one_or_none()

    def list_by_session(
        self,
        session_id: str,
        limit: int | None = None,
        offset: int = 0,
        descending: bool = False,
    ) -> Iterable[models.Message]:
        query = self._db.query(models.Message).filter(models.Message.session_id == session_id)
        if descending:
            query = query.order_by(models.Message.created_at.desc())
        else:
            query = query.order_by(models.Message.created_at.asc())
        query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()
