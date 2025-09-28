"""add_conversation_type_field

Revision ID: 289fa352ebc0
Revises: f82c79f71014
Create Date: 2025-09-28 13:58:50.946930

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '289fa352ebc0'
down_revision: str | Sequence[str] | None = 'f82c79f71014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add conversation_type field to conversations table."""
    # Add conversation_type column with default value
    op.add_column('conversations', 
        sa.Column('conversation_type', sa.String(length=50), nullable=False, server_default='chat')
    )
    
    # Create index for better query performance
    op.create_index('idx_conversations_type', 'conversations', ['conversation_type'])
    
    # Migrate existing data from metadata to new field (if any exists)
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE conversations 
        SET conversation_type = conversation_metadata->>'conversation_type'
        WHERE conversation_metadata->>'conversation_type' IS NOT NULL
    """))


def downgrade() -> None:
    """Remove conversation_type field from conversations table."""
    # Remove the index
    op.drop_index('idx_conversations_type', table_name='conversations')
    
    # Remove the column
    op.drop_column('conversations', 'conversation_type')
