import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0008_settings_env_overrides"
down_revision = "0007_m18_summary_config"
branch_labels = None
depends_on = None

_DEFAULTS: dict = {
    "eval_sample_rate": 0.1,
    "eval_llm_judge_enabled": True,
    "eval_ragas_enabled": True,
    "eval_judge_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
    "prompt_injection_llm_check": False,
    "agent_max_tool_calls": 10,
    "agent_max_llm_calls": 10,
    "agent_max_execution_time_ms": 30000,
    "bedrock_embedding_model_id": "amazon.titan-embed-text-v1",
}


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config_json FROM runtime_configs")).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        config = dict(row.config_json) if row.config_json else {}
        if "env_overrides" in config:
            continue
        config["env_overrides"] = dict(_DEFAULTS)
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
        if "env_overrides" not in config:
            continue
        del config["env_overrides"]
        conn.execute(
            sa.text(
                "UPDATE runtime_configs SET config_json = CAST(:cfg AS JSON), updated_at = :now WHERE id = :id"
            ),
            {"cfg": json.dumps(config), "now": now, "id": row.id},
        )
