"""Add persistent schedule generation jobs.

Revision ID: b7e4d9a1c2f0
Revises: 7d0d8f4b8c21
Create Date: 2026-09-19
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b7e4d9a1c2f0"
down_revision: Union[str, Sequence[str], None] = "7d0d8f4b8c21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS generation_jobs (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            academic_period_id INTEGER NOT NULL
                REFERENCES academic_periods(id) ON DELETE CASCADE,
            schedule_version_id INTEGER NULL
                REFERENCES schedule_versions(id) ON DELETE SET NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'queued',
            error TEXT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_generation_jobs_academic_period_id
        ON generation_jobs (academic_period_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_generation_jobs_status
        ON generation_jobs (status)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_generation_jobs_active_period
        ON generation_jobs (academic_period_id)
        WHERE status IN ('queued', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_generation_jobs_active_period")
    op.execute("DROP INDEX IF EXISTS ix_generation_jobs_status")
    op.execute(
        "DROP INDEX IF EXISTS ix_generation_jobs_academic_period_id"
    )
    op.execute("DROP TABLE IF EXISTS generation_jobs")
