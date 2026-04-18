import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0005_prompt_version_latest"
down_revision = "0004_runtime_configs_v2"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config_json FROM runtime_configs")).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        config = dict(row.config_json) if row.config_json else {}
        for node in config.get("nodes", {}).values():
            node["prompt_version"] = "latest"
        conn.execute(
            sa.text(
                "UPDATE runtime_configs SET config_json = CAST(:cfg AS JSON), updated_at = :now WHERE id = :id"
            ),
            {"cfg": json.dumps(config), "now": now, "id": row.id},
        )


def downgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config_json FROM runtime_configs")).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        config = dict(row.config_json) if row.config_json else {}
        for node in config.get("nodes", {}).values():
            node["prompt_version"] = "v1"
        conn.execute(
            sa.text(
                "UPDATE runtime_configs SET config_json = CAST(:cfg AS JSON), updated_at = :now WHERE id = :id"
            ),
            {"cfg": json.dumps(config), "now": now, "id": row.id},
        )
