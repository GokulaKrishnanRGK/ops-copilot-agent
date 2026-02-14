from collections.abc import Iterable, Sequence

from sqlalchemy.orm import Session as SQLAlchemySession

from opscopilot_db import models


class ToolCallRepo:
    def __init__(self, db: SQLAlchemySession) -> None:
        self._db = db

    def create(self, tool_call: models.ToolCall) -> models.ToolCall:
        self._db.add(tool_call)
        self._db.commit()
        self._db.refresh(tool_call)
        return tool_call

    def list_by_run(self, agent_run_id: str) -> Iterable[models.ToolCall]:
        return (
            self._db.query(models.ToolCall)
            .filter(models.ToolCall.agent_run_id == agent_run_id)
            .order_by(models.ToolCall.created_at.asc())
            .all()
        )

    def list_by_runs(self, agent_run_ids: Sequence[str]) -> Iterable[models.ToolCall]:
        if not agent_run_ids:
            return []
        return (
            self._db.query(models.ToolCall)
            .filter(models.ToolCall.agent_run_id.in_(list(agent_run_ids)))
            .order_by(models.ToolCall.created_at.asc())
            .all()
        )
