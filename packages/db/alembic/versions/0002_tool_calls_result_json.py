from alembic import op
import sqlalchemy as sa

revision = "0002_tool_calls_result_json"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tool_calls", sa.Column("result_json", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("tool_calls", "result_json")
