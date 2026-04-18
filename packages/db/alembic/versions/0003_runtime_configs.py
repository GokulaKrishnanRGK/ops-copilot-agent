from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0003_runtime_configs"
down_revision = "0002_tool_calls_result_json"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "runtime_configs",
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
    )

    op.add_column(
        "agent_runs",
        sa.Column("runtime_config_id", sa.String(), sa.ForeignKey("runtime_configs.id"), nullable=True),
    )
    op.create_index("ix_agent_runs_runtime_config_id", "agent_runs", ["runtime_config_id"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    op.execute(
        sa.text(
            "INSERT INTO runtime_configs "
            "(id, schema_version, scope_model_id, planner_model_id, clarifier_model_id, answer_model_id, "
            "max_agent_steps, max_budget_usd, prompt_version, created_at, updated_at) "
            "VALUES (:id, :schema_version, :scope_model_id, :planner_model_id, :clarifier_model_id, "
            ":answer_model_id, :max_agent_steps, :max_budget_usd, :prompt_version, :created_at, :updated_at)"
        ).bindparams(
            id="rc_m15_default",
            schema_version="m15",
            scope_model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
            planner_model_id="global.anthropic.claude-sonnet-4-6",
            clarifier_model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
            answer_model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
            max_agent_steps=10,
            max_budget_usd=None,
            prompt_version="v1",
            created_at=now,
            updated_at=now,
        )
    )


def downgrade():
    op.drop_index("ix_agent_runs_runtime_config_id", table_name="agent_runs")
    op.drop_column("agent_runs", "runtime_config_id")
    op.drop_table("runtime_configs")
