from sqlalchemy.orm import Session

from opscopilot_db import models


class RuntimeConfigRepo:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active(self) -> models.RuntimeConfig | None:
        return (
            self._db.query(models.RuntimeConfig)
            .order_by(models.RuntimeConfig.updated_at.desc())
            .first()
        )
