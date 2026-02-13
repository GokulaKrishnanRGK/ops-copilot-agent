from collections.abc import Iterable

from sqlalchemy.orm import Session as SQLAlchemySession

from opscopilot_db import models


class AgentRunRepo:
    def __init__(self, db: SQLAlchemySession) -> None:
        self._db = db

    def create(self, agent_run: models.AgentRun) -> models.AgentRun:
        self._db.add(agent_run)
        self._db.commit()
        self._db.refresh(agent_run)
        return agent_run

    def get(self, agent_run_id: str) -> models.AgentRun | None:
        return self._db.query(models.AgentRun).filter(models.AgentRun.id == agent_run_id).one_or_none()

    def list_by_session(self, session_id: str) -> Iterable[models.AgentRun]:
        return (
            self._db.query(models.AgentRun)
            .filter(models.AgentRun.session_id == session_id)
            .order_by(models.AgentRun.started_at.desc())
            .all()
        )

    def update(self, agent_run: models.AgentRun) -> models.AgentRun:
        self._db.add(agent_run)
        self._db.commit()
        self._db.refresh(agent_run)
        return agent_run
