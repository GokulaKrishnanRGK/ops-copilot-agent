from sqlalchemy.orm import Session

from opscopilot_db import models


class RuntimeConfigRepo:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, config_id: str) -> models.RuntimeConfig | None:
        return self._db.query(models.RuntimeConfig).filter(models.RuntimeConfig.id == config_id).one_or_none()

    def get_active(self) -> models.RuntimeConfig | None:
        return (
            self._db.query(models.RuntimeConfig)
            .order_by(models.RuntimeConfig.updated_at.desc())
            .first()
        )
