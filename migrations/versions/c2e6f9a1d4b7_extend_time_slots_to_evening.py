"""Extend default timetable to evening slots.

Revision ID: c2e6f9a1d4b7
Revises: b7e4d9a1c2f0
Create Date: 2026-09-19
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c2e6f9a1d4b7"
down_revision: Union[str, Sequence[str], None] = "b7e4d9a1c2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO time_slots
            (day_of_week, lesson_number, start_time, end_time, is_active)
        SELECT days.day_of_week, slots.lesson_number,
               slots.start_time, slots.end_time, TRUE
        FROM generate_series(1, 6) AS days(day_of_week)
        CROSS JOIN (
            VALUES
                (8, TIME '15:00', TIME '15:50'),
                (9, TIME '16:00', TIME '16:50'),
                (10, TIME '17:00', TIME '17:50'),
                (11, TIME '18:00', TIME '18:50'),
                (12, TIME '19:00', TIME '19:50'),
                (13, TIME '20:00', TIME '20:50')
        ) AS slots(lesson_number, start_time, end_time)
        WHERE NOT EXISTS (
            SELECT 1
            FROM time_slots existing
            WHERE existing.day_of_week = days.day_of_week
              AND existing.lesson_number = slots.lesson_number
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM time_slots
        WHERE lesson_number BETWEEN 8 AND 13
        """
    )
