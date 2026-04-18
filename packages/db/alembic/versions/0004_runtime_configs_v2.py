from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0004_runtime_configs_v2"
down_revision = "0003_runtime_configs"
branch_labels = None
depends_on = None

_DEFAULT_CONFIG = {
    "nodes": {
        "scope": {
            "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "prompt_version": "v1",
        },
        "planner": {
            "model_id": "global.anthropic.claude-sonnet-4-6",
            "prompt_version": "v1",
        },
        "clarifier": {
            "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "prompt_version": "v1",
        },
        "answer": {
            "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "prompt_version": "v1",
        },
    },
    "limits": {
        "max_agent_steps": 10,
        "max_budget_usd": None,
    },
}

_OLD_CONFIG_COLUMNS = [
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("schema_version", sa.String(), nullable=False),
    sa.Column("scope_model_id", sa.String(), nullable=False),
    sa.Column("planner_model_id", sa.String(), nullable=False),
    sa.Column("clarifier_model_id", sa.String(), nullable=False),
    sa.Column("answer_model_id", sa.String(), nullable=False),
    sa.Column("max_agent_steps", sa.Integer(), nullable=False),
    sa.Column("max_budget_usd", sa.Numeric(), nullable=True),
    sa.Column("prompt_version", sa.String(), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.Column("updated_at", sa.DateTime(), nullable=False),
]


def upgrade():
    op.drop_index("ix_agent_runs_runtime_config_id", table_name="agent_runs")
    op.drop_column("agent_runs", "runtime_config_id")

    op.drop_table("runtime_configs")

    op.create_table(
        "runtime_configs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.add_column(
        "agent_runs",
        sa.Column("runtime_config_id", sa.String(), sa.ForeignKey("runtime_configs.id"), nullable=True),
    )
    op.create_index("ix_agent_runs_runtime_config_id", "agent_runs", ["runtime_config_id"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    t = sa.table(
        "runtime_configs",
        sa.column("id", sa.String),
        sa.column("schema_version", sa.String),
        sa.column("config_json", sa.JSON),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(t, [
        {
            "id": "rc_v1_default",
            "schema_version": "v1",
            "config_json": _DEFAULT_CONFIG,
            "created_at": now,
            "updated_at": now,
        }
    ])


def downgrade():
    op.drop_index("ix_agent_runs_runtime_config_id", table_name="agent_runs")
    op.drop_column("agent_runs", "runtime_config_id")

    op.drop_table("runtime_configs")

    op.create_table("runtime_configs", *_OLD_CONFIG_COLUMNS)

    op.add_column(
        "agent_runs",
        sa.Column("runtime_config_id", sa.String(), sa.ForeignKey("runtime_configs.id"), nullable=True),
    )
    op.create_index("ix_agent_runs_runtime_config_id", "agent_runs", ["runtime_config_id"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    t_old = sa.table(
        "runtime_configs",
        sa.column("id", sa.String),
        sa.column("schema_version", sa.String),
        sa.column("scope_model_id", sa.String),
        sa.column("planner_model_id", sa.String),
        sa.column("clarifier_model_id", sa.String),
        sa.column("answer_model_id", sa.String),
        sa.column("max_agent_steps", sa.Integer),
        sa.column("max_budget_usd", sa.Numeric),
        sa.column("prompt_version", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(t_old, [
        {
            "id": "rc_m15_default",
            "schema_version": "m15",
            "scope_model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "planner_model_id": "global.anthropic.claude-sonnet-4-6",
            "clarifier_model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "answer_model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "max_agent_steps": 10,
            "max_budget_usd": None,
            "prompt_version": "v1",
            "created_at": now,
            "updated_at": now,
        }
    ])
