"""Register the existing SmartSchedule schema.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-19
"""

from typing import Sequence, Union


revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing installations are stamped with this revision.
    pass


def downgrade() -> None:
    pass
