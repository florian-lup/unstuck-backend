"""add_subscription_fields

Revision ID: 72c8f88c437d
Revises: 289fa352ebc0
Create Date: 2025-10-02 20:32:39.227745

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72c8f88c437d"
down_revision: str | Sequence[str] | None = "289fa352ebc0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add subscription fields to users table
    op.add_column(
        "users",
        sa.Column(
            "subscription_tier",
            sa.String(length=20),
            nullable=False,
            server_default="free",
        ),
    )
    op.add_column(
        "users", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users", sa.Column("subscription_status", sa.String(length=50), nullable=True)
    )

    # Create indexes
    op.create_index(
        "idx_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_users_stripe_customer_id", table_name="users")

    # Remove subscription fields
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "subscription_tier")
