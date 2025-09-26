"""Database service layer with security best practices."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Conversation, Message, User
from schemas.gaming_search import ConversationMessage

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service layer for secure database operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize with database session."""
        self.db = db_session

    # ==================== USER MANAGEMENT ====================

    async def get_or_create_user(
        self, auth0_user_id: str, username: str | None = None, email: str | None = None
    ) -> User:
        """
        Get or create user by Auth0 ID.

        This is called on every authenticated request to ensure the user exists
        in our database. It's safe to call repeatedly.

        Args:
            auth0_user_id: Auth0 user identifier
            username: Optional username from Auth0
            email: Optional email from Auth0

        Returns:
            User: The user record
        """
        try:
            # Try to find existing user
            query = select(User).where(User.auth0_user_id == auth0_user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()

            if user:
                # Update last active time and any new info
                user.last_active_at = datetime.utcnow()  # type: ignore[assignment]
                if username and user.username != username:
                    user.username = username  # type: ignore[assignment]
                if email and user.email != email:
                    user.email = email  # type: ignore[assignment]
                await self.db.commit()
                return user
            # Create new user
            user = User(
                auth0_user_id=auth0_user_id,
                username=username,
                email=email,
                last_active_at=datetime.utcnow(),
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"Created new user: {auth0_user_id}")
            return user

        except Exception as e:
            logger.error(f"Error getting/creating user {auth0_user_id}: {e}")
            await self.db.rollback()
            raise

    async def update_user_preferences(
        self, user_id: UUID, preferences: dict[str, Any]
    ) -> User:
        """
        Update user preferences.

        Args:
            user_id: User ID
            preferences: User preferences dictionary

        Returns:
            User: Updated user record
        """
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User {user_id} not found")

            user.preferences = preferences  # type: ignore[assignment]
            user.updated_at = datetime.utcnow()  # type: ignore[assignment]
            await self.db.commit()
            return user

        except Exception as e:
            logger.error(f"Error updating user preferences {user_id}: {e}")
            await self.db.rollback()
            raise

    # ==================== CONVERSATION MANAGEMENT ====================

    async def create_conversation(
        self,
        user_id: UUID,
        game_name: str,
        game_version: str | None = None,
        title: str | None = None,
    ) -> Conversation:
        """
        Create a new conversation for a user.

        Security: Only the authenticated user can create conversations for themselves.

        Args:
            user_id: User ID (from Auth0 token)
            game_name: Name of the game
            game_version: Optional game version
            title: Optional conversation title

        Returns:
            Conversation: Created conversation
        """
        try:
            conversation = Conversation(
                user_id=user_id,
                game_name=game_name,
                game_version=game_version,
                title=title or f"{game_name} Chat",
            )

            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)

            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            return conversation

        except Exception as e:
            logger.error(f"Error creating conversation for user {user_id}: {e}")
            await self.db.rollback()
            raise

    async def get_user_conversations(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
    ) -> list[Conversation]:
        """
        Get conversations for a user.

        Security: Only returns conversations owned by the user.

        Args:
            user_id: User ID
            limit: Maximum number of conversations to return
            offset: Pagination offset
            include_archived: Whether to include archived conversations

        Returns:
            list[Conversation]: User's conversations
        """
        try:
            query = select(Conversation).where(Conversation.user_id == user_id)

            if not include_archived:
                query = query.where(Conversation.is_archived == "active")

            query = (
                query.order_by(desc(Conversation.updated_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.db.execute(query)
            conversations = result.scalars().all()

            return list(conversations)

        except Exception as e:
            logger.error(f"Error getting conversations for user {user_id}: {e}")
            raise

    async def get_conversation_with_messages(
        self, conversation_id: UUID, user_id: UUID, limit: int = 100
    ) -> Conversation | None:
        """
        Get conversation with its messages.

        Security: Only returns conversation if owned by the user.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            limit: Maximum number of messages to return

        Returns:
            Optional[Conversation]: Conversation with messages, or None if not found/not owned
        """
        try:
            # First check if user owns the conversation
            query = (
                select(Conversation)
                .where(
                    and_(
                        Conversation.id == conversation_id,
                        Conversation.user_id
                        == user_id,  # Security: user can only access their own data
                    )
                )
                .options(selectinload(Conversation.messages))
            )

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                f"Error getting conversation {conversation_id} for user {user_id}: {e}"
            )
            raise

    async def update_conversation_title(
        self, conversation_id: UUID, user_id: UUID, title: str
    ) -> Conversation | None:
        """
        Update conversation title.

        Security: Only allows updating conversations owned by the user.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            title: New title

        Returns:
            Optional[Conversation]: Updated conversation or None if not found/not owned
        """
        try:
            query = select(Conversation).where(
                and_(
                    Conversation.id == conversation_id, Conversation.user_id == user_id
                )
            )

            result = await self.db.execute(query)
            conversation = result.scalar_one_or_none()

            if conversation:
                conversation.title = title  # type: ignore[assignment]
                conversation.updated_at = datetime.utcnow()  # type: ignore[assignment]
                await self.db.commit()

            return conversation

        except Exception as e:
            logger.error(f"Error updating conversation title {conversation_id}: {e}")
            await self.db.rollback()
            raise

    # ==================== MESSAGE MANAGEMENT ====================

    async def add_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
        search_results: dict[str, Any] | list[dict[str, Any]] | None = None,
        usage_stats: dict[str, Any] | None = None,
        model_info: dict[str, Any] | None = None,
    ) -> Message | None:
        """
        Add a message to a conversation.

        Security: Only allows adding messages to conversations owned by the user.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            search_results: Optional search results from AI
            usage_stats: Optional usage statistics
            model_info: Optional model information

        Returns:
            Optional[Message]: Created message or None if conversation not found/not owned
        """
        try:
            # First verify user owns the conversation
            conv_query = select(Conversation).where(
                and_(
                    Conversation.id == conversation_id, Conversation.user_id == user_id
                )
            )

            conv_result = await self.db.execute(conv_query)
            conversation = conv_result.scalar_one_or_none()

            if not conversation:
                logger.warning(
                    f"User {user_id} attempted to add message to conversation {conversation_id} they don't own"
                )
                return None

            # Create message
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                search_results=search_results,
                usage_stats=usage_stats,
                model_info=model_info,
            )

            self.db.add(message)

            # Update conversation timestamp
            conversation.updated_at = datetime.utcnow()  # type: ignore[assignment]

            await self.db.commit()
            await self.db.refresh(message)

            return message

        except Exception as e:
            logger.error(f"Error adding message to conversation {conversation_id}: {e}")
            await self.db.rollback()
            raise

    async def get_conversation_messages(
        self, conversation_id: UUID, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ConversationMessage]:
        """
        Get messages from a conversation.

        Security: Only returns messages from conversations owned by the user.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            limit: Maximum number of messages
            offset: Pagination offset

        Returns:
            list[ConversationMessage]: List of conversation messages
        """
        try:
            # First verify user owns the conversation
            conv_query = select(Conversation).where(
                and_(
                    Conversation.id == conversation_id, Conversation.user_id == user_id
                )
            )

            conv_result = await self.db.execute(conv_query)
            conversation = conv_result.scalar_one_or_none()

            if not conversation:
                return []  # Return empty list instead of error for security

            # Get messages
            query = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
                .limit(limit)
                .offset(offset)
            )

            result = await self.db.execute(query)
            messages = result.scalars().all()

            # Convert to ConversationMessage format
            return [
                ConversationMessage(role=msg.role, content=msg.content)  # type: ignore[arg-type]
                for msg in messages
            ]

        except Exception as e:
            logger.error(
                f"Error getting messages for conversation {conversation_id}: {e}"
            )
            raise

    # ==================== CLEANUP OPERATIONS ====================

    async def archive_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        """
        Archive a conversation.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)

        Returns:
            bool: True if archived, False if not found/not owned
        """
        try:
            query = select(Conversation).where(
                and_(
                    Conversation.id == conversation_id, Conversation.user_id == user_id
                )
            )

            result = await self.db.execute(query)
            conversation = result.scalar_one_or_none()

            if conversation:
                conversation.is_archived = "archived"  # type: ignore[assignment]
                conversation.updated_at = datetime.utcnow()  # type: ignore[assignment]
                await self.db.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"Error archiving conversation {conversation_id}: {e}")
            await self.db.rollback()
            raise

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        """
        Permanently delete a conversation and all its messages.

        ⚠️ WARNING: This is irreversible! All messages will be permanently deleted.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)

        Returns:
            bool: True if deleted, False if not found/not owned
        """
        try:
            # First verify user owns the conversation
            query = select(Conversation).where(
                and_(
                    Conversation.id == conversation_id, Conversation.user_id == user_id
                )
            )

            result = await self.db.execute(query)
            conversation = result.scalar_one_or_none()

            if conversation:
                # Delete conversation (cascade will automatically delete all messages)
                await self.db.delete(conversation)
                await self.db.commit()

                logger.info(
                    f"User {user_id} permanently deleted conversation {conversation_id}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            await self.db.rollback()
            raise
