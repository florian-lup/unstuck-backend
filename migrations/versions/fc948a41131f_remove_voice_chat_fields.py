"""remove_voice_chat_fields

Revision ID: fc948a41131f
Revises: a8f3d9e2b1c5
Create Date: 2025-10-11 20:32:40.630460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc948a41131f'
down_revision: Union[str, Sequence[str], None] = 'a8f3d9e2b1c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove voice chat fields from users table."""
    # Remove voice chat tracking columns
    op.drop_column('users', 'voice_request_count_reset_date')
    op.drop_column('users', 'monthly_voice_requests')
    op.drop_column('users', 'total_voice_requests')


def downgrade() -> None:
    """Downgrade schema - restore voice chat fields to users table."""
    # Restore voice chat tracking columns
    op.add_column('users', sa.Column('total_voice_requests', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('monthly_voice_requests', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('voice_request_count_reset_date', sa.DateTime(timezone=True), nullable=True))
