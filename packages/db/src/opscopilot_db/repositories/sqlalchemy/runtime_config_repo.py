import uuid
from datetime import datetime, timezone

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

    def create(self, config_json: dict, schema_version: str) -> models.RuntimeConfig:
        now = datetime.now(timezone.utc)
        row = models.RuntimeConfig(
            id=str(uuid.uuid4()),
            schema_version=schema_version,
            config_json=config_json,
            created_at=now,
            updated_at=now,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row
