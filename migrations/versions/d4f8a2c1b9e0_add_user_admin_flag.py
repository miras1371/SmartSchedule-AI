"""Add administrator role flag to users."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a2c1b9e0"
down_revision: Union[str, Sequence[str], None] = "c2e6f9a1d4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_admin" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_admin" in columns:
        op.drop_column("users", "is_admin")
