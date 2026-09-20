"""Use 50-minute lessons with 10-minute breaks.

Revision ID: 7d0d8f4b8c21
Revises: 3bc41875de94
Create Date: 2026-09-19
"""

from typing import Sequence, Union

from alembic import op


revision: str = "7d0d8f4b8c21"
down_revision: Union[str, Sequence[str], None] = "3bc41875de94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE time_slots
        SET start_time = slots.start_time,
            end_time = slots.end_time
        FROM (
            VALUES
                (1, TIME '08:00', TIME '08:50'),
                (2, TIME '09:00', TIME '09:50'),
                (3, TIME '10:00', TIME '10:50'),
                (4, TIME '11:00', TIME '11:50'),
                (5, TIME '12:00', TIME '12:50'),
                (6, TIME '13:00', TIME '13:50'),
                (7, TIME '14:00', TIME '14:50')
        ) AS slots(lesson_number, start_time, end_time)
        WHERE time_slots.lesson_number = slots.lesson_number
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE time_slots
        SET start_time = slots.start_time,
            end_time = slots.end_time
        FROM (
            VALUES
                (1, TIME '08:00', TIME '09:30'),
                (2, TIME '09:40', TIME '11:10'),
                (3, TIME '11:20', TIME '12:50'),
                (4, TIME '13:00', TIME '14:30'),
                (5, TIME '14:40', TIME '16:10'),
                (6, TIME '16:20', TIME '17:50'),
                (7, TIME '18:00', TIME '19:30')
        ) AS slots(lesson_number, start_time, end_time)
        WHERE time_slots.lesson_number = slots.lesson_number
        """
    )
