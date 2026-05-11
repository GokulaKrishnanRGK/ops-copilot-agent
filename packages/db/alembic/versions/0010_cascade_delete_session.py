"""cascade delete from session

Revision ID: 0010_cascade_delete_session
Revises: 0009_title_gen_config_seed
Create Date: 2026-05-11
"""

from alembic import op

revision = "0010_cascade_delete_session"
down_revision = "0009_title_gen_config_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("messages_session_id_fkey", "messages", type_="foreignkey")
    op.create_foreign_key(
        "messages_session_id_fkey",
        "messages", "sessions",
        ["session_id"], ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("agent_runs_session_id_fkey", "agent_runs", type_="foreignkey")
    op.create_foreign_key(
        "agent_runs_session_id_fkey",
        "agent_runs", "sessions",
        ["session_id"], ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("llm_calls_agent_run_id_fkey", "llm_calls", type_="foreignkey")
    op.create_foreign_key(
        "llm_calls_agent_run_id_fkey",
        "llm_calls", "agent_runs",
        ["agent_run_id"], ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("tool_calls_agent_run_id_fkey", "tool_calls", type_="foreignkey")
    op.create_foreign_key(
        "tool_calls_agent_run_id_fkey",
        "tool_calls", "agent_runs",
        ["agent_run_id"], ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("budget_events_agent_run_id_fkey", "budget_events", type_="foreignkey")
    op.create_foreign_key(
        "budget_events_agent_run_id_fkey",
        "budget_events", "agent_runs",
        ["agent_run_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("budget_events_agent_run_id_fkey", "budget_events", type_="foreignkey")
    op.create_foreign_key(
        "budget_events_agent_run_id_fkey",
        "budget_events", "agent_runs",
        ["agent_run_id"], ["id"],
    )

    op.drop_constraint("tool_calls_agent_run_id_fkey", "tool_calls", type_="foreignkey")
    op.create_foreign_key(
        "tool_calls_agent_run_id_fkey",
        "tool_calls", "agent_runs",
        ["agent_run_id"], ["id"],
    )

    op.drop_constraint("llm_calls_agent_run_id_fkey", "llm_calls", type_="foreignkey")
    op.create_foreign_key(
        "llm_calls_agent_run_id_fkey",
        "llm_calls", "agent_runs",
        ["agent_run_id"], ["id"],
    )

    op.drop_constraint("agent_runs_session_id_fkey", "agent_runs", type_="foreignkey")
    op.create_foreign_key(
        "agent_runs_session_id_fkey",
        "agent_runs", "sessions",
        ["session_id"], ["id"],
    )

    op.drop_constraint("messages_session_id_fkey", "messages", type_="foreignkey")
    op.create_foreign_key(
        "messages_session_id_fkey",
        "messages", "sessions",
        ["session_id"], ["id"],
    )
