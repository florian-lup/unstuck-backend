"""add_voice_chat_request_tracking_fields

Revision ID: b0d61f95e068
Revises: a8f3d9e2b1c5
Create Date: 2025-10-10 22:06:21.924228

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b0d61f95e068'
down_revision: str | Sequence[str] | None = 'a8f3d9e2b1c5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add voice chat request tracking fields to users table
    op.add_column(
        "users",
        sa.Column(
            "total_voice_requests", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "monthly_voice_requests", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "voice_request_count_reset_date", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove voice chat request tracking fields
    op.drop_column("users", "voice_request_count_reset_date")
    op.drop_column("users", "monthly_voice_requests")
    op.drop_column("users", "total_voice_requests")
