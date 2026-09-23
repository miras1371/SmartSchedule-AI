"""store classroom assignments per schedule version

Revision ID: f1c2d3e4a5b6
Revises: e7a1c4d9b2f0
"""

from alembic import op
import sqlalchemy as sa


revision = "f1c2d3e4a5b6"
down_revision = "e7a1c4d9b2f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("schedule_item_classrooms"):
        op.create_table(
            "schedule_item_classrooms",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("schedule_item_id", sa.Integer(), nullable=False),
            sa.Column("lesson_target_id", sa.Integer(), nullable=False),
            sa.Column("classroom_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["schedule_item_id"], ["schedule_items.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["lesson_target_id"], ["lesson_targets.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["classroom_id"], ["classrooms.id"], ondelete="RESTRICT"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "schedule_item_id",
                "lesson_target_id",
                name="uq_schedule_item_lesson_target_classroom",
            ),
        )
        op.create_index(
            "ix_schedule_item_classrooms_schedule_item_id",
            "schedule_item_classrooms",
            ["schedule_item_id"],
        )
        op.create_index(
            "ix_schedule_item_classrooms_lesson_target_id",
            "schedule_item_classrooms",
            ["lesson_target_id"],
        )
        op.create_index(
            "ix_schedule_item_classrooms_classroom_id",
            "schedule_item_classrooms",
            ["classroom_id"],
        )

    # Existing versions did not preserve their own rooms. The current target
    # assignment is the only recoverable value, so use it as a baseline.
    op.execute(
        """
        INSERT INTO schedule_item_classrooms
            (schedule_item_id, lesson_target_id, classroom_id)
        SELECT schedule_items.id, lesson_targets.id, lesson_targets.classroom_id
        FROM schedule_items
        JOIN lesson_targets
          ON lesson_targets.lesson_id = schedule_items.lesson_id
        WHERE lesson_targets.classroom_id IS NOT NULL
        ON CONFLICT (schedule_item_id, lesson_target_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_schedule_item_classrooms_classroom_id",
        table_name="schedule_item_classrooms",
    )
    op.drop_index(
        "ix_schedule_item_classrooms_lesson_target_id",
        table_name="schedule_item_classrooms",
    )
    op.drop_index(
        "ix_schedule_item_classrooms_schedule_item_id",
        table_name="schedule_item_classrooms",
    )
    op.drop_table("schedule_item_classrooms")
