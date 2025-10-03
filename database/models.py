"""Database models for the gaming AI chat overlay."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    """User model linked to Auth0 user ID."""

    __tablename__ = "users"

    # Primary key - UUID for security (prevents enumeration attacks)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Auth0 integration - this links to your Auth0 user
    auth0_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # User metadata (optional)
    username: Mapped[str | None] = mapped_column(String(100))  # Display name from Auth0 or custom
    email: Mapped[str | None] = mapped_column(String(320))  # Email from Auth0 (for support purposes)

    # Subscription fields
    subscription_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="free"
    )  # 'free' or 'community'
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)  # Stripe customer ID
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))  # Current active subscription ID
    subscription_status: Mapped[str | None] = mapped_column(
        String(50)
    )  # active, canceled, past_due, etc. (mirrors Stripe status)

    # Request tracking fields for subscription limits
    total_requests: Mapped[int] = mapped_column(
        nullable=False, default=0
    )  # Total lifetime requests (for free tier)
    monthly_requests: Mapped[int] = mapped_column(
        nullable=False, default=0
    )  # Monthly requests (for community tier)
    request_count_reset_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )  # Date when monthly counter was last reset

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # User preferences (stored as JSON for flexibility)
    preferences: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Relationships
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )

    # Security: Add index for fast Auth0 lookups
    __table_args__ = (
        Index("idx_users_auth0_user_id", "auth0_user_id"),
        Index("idx_users_last_active", "last_active_at"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, auth0_user_id={self.auth0_user_id})>"


class Conversation(Base):
    """Conversation model for organizing chat sessions."""

    __tablename__ = "conversations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to user (for security isolation)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Conversation metadata
    title = Column(String(500))  # Auto-generated or user-provided title
    game_name = Column(String(200), nullable=False)  # Game this conversation is about
    game_version = Column(String(100))  # Optional game version

    # Conversation type and status
    conversation_type = Column(
        String(50), nullable=False, default="chat"
    )  # chat, lore, etc.
    is_archived = Column(String(20), default="active")  # active, archived, deleted

    # Audit timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Conversation metadata (stored as JSON)
    conversation_metadata = Column(JSONB, default=dict)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    # Security and performance indexes
    __table_args__ = (
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_user_updated", "user_id", "updated_at"),
        Index("idx_conversations_game", "game_name"),
        Index("idx_conversations_type", "conversation_type"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, game={self.game_name})>"


class Message(Base):
    """Message model for individual chat messages."""

    __tablename__ = "messages"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to conversation
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )

    # Message content
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)  # The actual message content

    # AI-specific fields (stored as JSON for flexibility)
    search_results = Column(JSONB)  # Search results from Perplexity
    usage_stats = Column(JSONB)  # Token usage and other metrics
    model_info = Column(JSONB)  # Model used, temperature, etc.

    # Message metadata
    response_time_ms = Column(String(10))  # How long the AI took to respond
    finish_reason = Column(String(50))  # Why the AI stopped generating

    # Audit timestamp
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Performance indexes
    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
        Index("idx_messages_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"


# Security note: All queries should include user_id filtering to ensure users
# can only access their own data. This will be enforced in the service layer.
