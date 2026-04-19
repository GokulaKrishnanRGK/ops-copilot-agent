import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0009_title_gen_config_seed"
down_revision = "0008_settings_env_overrides"
branch_labels = None
depends_on = None

_NEW_MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
_OLD_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

_TITLE_GEN_DEFAULTS = {
    "title_gen_model_id": _NEW_MODEL_ID,
    "title_gen_prompt_version": "latest",
}


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config_json FROM runtime_configs")).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        config = dict(row.config_json) if row.config_json else {}
        env = dict(config.get("env_overrides", {}))
        changed = False
        for key, value in _TITLE_GEN_DEFAULTS.items():
            if key not in env:
                env[key] = value
                changed = True
        if env.get("eval_judge_model_id") == _OLD_MODEL_ID:
            env["eval_judge_model_id"] = _NEW_MODEL_ID
            changed = True
        if not changed:
            continue
        config["env_overrides"] = env
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
        env = dict(config.get("env_overrides", {}))
        changed = False
        for key in _TITLE_GEN_DEFAULTS:
            if key in env:
                del env[key]
                changed = True
        if env.get("eval_judge_model_id") == _NEW_MODEL_ID:
            env["eval_judge_model_id"] = _OLD_MODEL_ID
            changed = True
        if not changed:
            continue
        config["env_overrides"] = env
        conn.execute(
            sa.text(
                "UPDATE runtime_configs SET config_json = CAST(:cfg AS JSON), updated_at = :now WHERE id = :id"
            ),
            {"cfg": json.dumps(config), "now": now, "id": row.id},
        )
