from collections.abc import Iterable

from sqlalchemy.orm import Session as SQLAlchemySession

from opscopilot_db import models


class LlmCallRepo:
    def __init__(self, db: SQLAlchemySession) -> None:
        self._db = db

    def create(self, llm_call: models.LlmCall) -> models.LlmCall:
        self._db.add(llm_call)
        self._db.commit()
        self._db.refresh(llm_call)
        return llm_call

    def list_by_run(self, agent_run_id: str) -> Iterable[models.LlmCall]:
        return (
            self._db.query(models.LlmCall)
            .filter(models.LlmCall.agent_run_id == agent_run_id)
            .order_by(models.LlmCall.created_at.asc())
            .all()
        )
