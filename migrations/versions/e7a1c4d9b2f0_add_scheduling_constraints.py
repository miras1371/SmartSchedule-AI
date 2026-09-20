"""add scheduling constraints

Revision ID: e7a1c4d9b2f0
"""

from alembic import op
import sqlalchemy as sa


revision = "e7a1c4d9b2f0"
down_revision = "d4f8a2c1b9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduling_constraints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("constraint_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("classroom_id", sa.Integer(), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.String(length=5), nullable=True),
        sa.Column("end_time", sa.String(length=5), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduling_constraints_constraint_type", "scheduling_constraints", ["constraint_type"])
    op.create_index("ix_scheduling_constraints_teacher_id", "scheduling_constraints", ["teacher_id"])
    op.create_index("ix_scheduling_constraints_classroom_id", "scheduling_constraints", ["classroom_id"])


def downgrade() -> None:
    op.drop_index("ix_scheduling_constraints_classroom_id", table_name="scheduling_constraints")
    op.drop_index("ix_scheduling_constraints_teacher_id", table_name="scheduling_constraints")
    op.drop_index("ix_scheduling_constraints_constraint_type", table_name="scheduling_constraints")
    op.drop_table("scheduling_constraints")
