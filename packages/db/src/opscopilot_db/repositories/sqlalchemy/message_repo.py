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

    def list_by_session(self, session_id: str) -> Iterable[models.Message]:
        return (
            self._db.query(models.Message)
            .filter(models.Message.session_id == session_id)
            .order_by(models.Message.created_at.asc())
            .all()
        )
