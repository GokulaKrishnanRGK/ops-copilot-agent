from collections.abc import Iterable

from sqlalchemy.orm import Session as SQLAlchemySession

from opscopilot_db import models


class BudgetEventRepo:
    def __init__(self, db: SQLAlchemySession) -> None:
        self._db = db

    def create(self, budget_event: models.BudgetEvent) -> models.BudgetEvent:
        self._db.add(budget_event)
        self._db.commit()
        self._db.refresh(budget_event)
        return budget_event

    def list_by_run(self, agent_run_id: str) -> Iterable[models.BudgetEvent]:
        return (
            self._db.query(models.BudgetEvent)
            .filter(models.BudgetEvent.agent_run_id == agent_run_id)
            .order_by(models.BudgetEvent.created_at.asc())
            .all()
        )
