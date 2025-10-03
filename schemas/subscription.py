"""Subscription schemas for Stripe integration."""

from pydantic import BaseModel, Field


class CheckoutSessionRequest(BaseModel):
    """Request to create a Stripe checkout session."""

    # No additional fields needed - user info comes from JWT token


class CheckoutSessionResponse(BaseModel):
    """Response containing Stripe checkout session URL."""

    checkout_url: str = Field(..., description="Stripe checkout session URL")
    session_id: str = Field(..., description="Stripe session ID")


class CancelSubscriptionResponse(BaseModel):
    """Response after canceling subscription."""

    success: bool = Field(..., description="Whether cancellation was successful")
    message: str = Field(..., description="Cancellation message")


class SubscriptionStatusResponse(BaseModel):
    """User subscription status."""

    subscription_tier: str = Field(..., description="Current subscription tier (free/community)")
    subscription_status: str | None = Field(
        None, description="Stripe subscription status"
    )
    stripe_customer_id: str | None = Field(None, description="Stripe customer ID")


class WebhookEvent(BaseModel):
    """Stripe webhook event data."""

    type: str = Field(..., description="Event type")
    data: dict = Field(..., description="Event data")

