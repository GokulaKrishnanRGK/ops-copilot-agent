from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
    )
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("agent_run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("agent_node", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=False),
        sa.Column("tokens_output", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("agent_run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("args_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("bytes_returned", sa.Integer(), nullable=False),
        sa.Column("truncated", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "budget_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("agent_run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("delta_usd", sa.Numeric(), nullable=False),
        sa.Column("total_usd", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"])
    op.create_index("ix_llm_calls_agent_run_id", "llm_calls", ["agent_run_id"])
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])
    op.create_index("ix_budget_events_agent_run_id", "budget_events", ["agent_run_id"])


def downgrade():
    op.drop_index("ix_budget_events_agent_run_id", table_name="budget_events")
    op.drop_index("ix_tool_calls_agent_run_id", table_name="tool_calls")
    op.drop_index("ix_llm_calls_agent_run_id", table_name="llm_calls")
    op.drop_index("ix_agent_runs_session_id", table_name="agent_runs")
    op.drop_index("ix_messages_session_id", table_name="messages")
    op.drop_table("budget_events")
    op.drop_table("tool_calls")
    op.drop_table("llm_calls")
    op.drop_table("agent_runs")
    op.drop_table("messages")
    op.drop_table("sessions")
