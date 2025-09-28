"""Common schemas shared across different modules."""

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """Individual message in a conversation."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
