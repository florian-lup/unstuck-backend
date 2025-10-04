"""add_request_tracking_fields

Revision ID: a8f3d9e2b1c5
Revises: 72c8f88c437d
Create Date: 2025-10-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8f3d9e2b1c5"
down_revision: str | Sequence[str] | None = "72c8f88c437d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add request tracking fields to users table
    op.add_column(
        "users",
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("monthly_requests", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column(
            "request_count_reset_date", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove request tracking fields
    op.drop_column("users", "request_count_reset_date")
    op.drop_column("users", "monthly_requests")
    op.drop_column("users", "total_requests")
