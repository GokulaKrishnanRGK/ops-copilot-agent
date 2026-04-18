import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0006_add_injection_classifier_node"
down_revision = "0005_prompt_version_latest"
branch_labels = None
depends_on = None

_NODE_KEY = "injection_classifier"
_DEFAULT_MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
_DEFAULT_PROMPT_VERSION = "latest"


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config_json FROM runtime_configs")).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        config = dict(row.config_json) if row.config_json else {}
        nodes = dict(config.get("nodes", {}))
        if _NODE_KEY not in nodes:
            nodes[_NODE_KEY] = {
                "model_id": _DEFAULT_MODEL_ID,
                "prompt_version": _DEFAULT_PROMPT_VERSION,
            }
            config["nodes"] = nodes
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
        nodes = dict(config.get("nodes", {}))
        if _NODE_KEY in nodes:
            del nodes[_NODE_KEY]
            config["nodes"] = nodes
            conn.execute(
                sa.text(
                    "UPDATE runtime_configs SET config_json = CAST(:cfg AS JSON), updated_at = :now WHERE id = :id"
                ),
                {"cfg": json.dumps(config), "now": now, "id": row.id},
            )
