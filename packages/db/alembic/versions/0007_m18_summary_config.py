import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0007_m18_summary_config"
down_revision = "0006_injection_classifier"
branch_labels = None
depends_on = None

_SUMMARIZER_NODE_KEY = "summarizer"
_DEFAULT_SUMMARIZER_MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
_DEFAULT_SUMMARIZER_PROMPT_VERSION = "latest"
_DEFAULT_HISTORY_WINDOW_TURNS = 6
_DEFAULT_SUMMARIZER_PROMPT_VERSION_LIMIT_KEY = "summarizer_prompt_version"
_DEFAULT_HISTORY_WINDOW_TURNS_LIMIT_KEY = "history_window_turns"


def upgrade():
    op.add_column("sessions", sa.Column("prompt_summary", sa.Text(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config_json FROM runtime_configs")).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        config = dict(row.config_json) if row.config_json else {}
        changed = False

        nodes = dict(config.get("nodes", {}))
        if _SUMMARIZER_NODE_KEY not in nodes:
            nodes[_SUMMARIZER_NODE_KEY] = {
                "model_id": _DEFAULT_SUMMARIZER_MODEL_ID,
                "prompt_version": _DEFAULT_SUMMARIZER_PROMPT_VERSION,
            }
            config["nodes"] = nodes
            changed = True

        limits = dict(config.get("limits", {}))
        if _DEFAULT_HISTORY_WINDOW_TURNS_LIMIT_KEY not in limits:
            limits[_DEFAULT_HISTORY_WINDOW_TURNS_LIMIT_KEY] = _DEFAULT_HISTORY_WINDOW_TURNS
            changed = True
        if _DEFAULT_SUMMARIZER_PROMPT_VERSION_LIMIT_KEY not in limits:
            limits[_DEFAULT_SUMMARIZER_PROMPT_VERSION_LIMIT_KEY] = _DEFAULT_SUMMARIZER_PROMPT_VERSION
            changed = True
        if changed:
            config["limits"] = limits
            conn.execute(
                sa.text(
                    "UPDATE runtime_configs SET config_json = CAST(:cfg AS JSON), updated_at = :now WHERE id = :id"
                ),
                {"cfg": json.dumps(config), "now": now, "id": row.id},
            )


def downgrade():
    op.drop_column("sessions", "prompt_summary")

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config_json FROM runtime_configs")).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        config = dict(row.config_json) if row.config_json else {}
        changed = False

        nodes = dict(config.get("nodes", {}))
        if _SUMMARIZER_NODE_KEY in nodes:
            del nodes[_SUMMARIZER_NODE_KEY]
            config["nodes"] = nodes
            changed = True

        limits = dict(config.get("limits", {}))
        for key in (_DEFAULT_HISTORY_WINDOW_TURNS_LIMIT_KEY, _DEFAULT_SUMMARIZER_PROMPT_VERSION_LIMIT_KEY):
            if key in limits:
                del limits[key]
                changed = True
        if changed:
            config["limits"] = limits
            conn.execute(
                sa.text(
                    "UPDATE runtime_configs SET config_json = CAST(:cfg AS JSON), updated_at = :now WHERE id = :id"
                ),
                {"cfg": json.dumps(config), "now": now, "id": row.id},
            )
