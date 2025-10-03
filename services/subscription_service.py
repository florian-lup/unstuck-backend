"""Stripe subscription service."""

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from database.models import User

# Configure Stripe
stripe.api_key = settings.stripe_api_key


class SubscriptionService:
    """Service for managing Stripe subscriptions."""

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize subscription service."""
        self.db_session = db_session

    async def create_checkout_session(
        self, user: User, user_email: str
    ) -> dict[str, str]:
        """
        Create a Stripe checkout session for Community subscription.

        Args:
            user: The database user object
            user_email: User's email address

        Returns:
            Dictionary with checkout_url and session_id
        """
        # Create or retrieve Stripe customer
        if user.stripe_customer_id:
            customer_id = user.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=user_email,
                metadata={"user_id": str(user.id), "auth0_user_id": str(user.auth0_user_id)},
            )
            customer_id = customer.id

            # Save customer ID to database
            user.stripe_customer_id = customer_id
            await self.db_session.commit()

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": settings.stripe_price_id_community,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=settings.stripe_success_url,
            cancel_url=settings.stripe_cancel_url,
            metadata={
                "user_id": str(user.id),
                "auth0_user_id": str(user.auth0_user_id),
            },
        )

        return {
            "checkout_url": session.url or "",
            "session_id": session.id or "",
        }

    async def cancel_subscription(self, user: User) -> dict[str, str | bool]:
        """
        Cancel user's active subscription.

        Args:
            user: The database user object

        Returns:
            Dictionary with success status and message
        """
        if not user.stripe_subscription_id:
            return {"success": False, "message": "No active subscription found"}

        try:
            subscription_id = user.stripe_subscription_id
            # Cancel the subscription at period end (user keeps access until end of billing period)
            stripe.Subscription.modify(
                subscription_id, cancel_at_period_end=True
            )

            # Update user status
            user.subscription_status = "canceling"
            await self.db_session.commit()

            return {
                "success": True,
                "message": "Subscription will be canceled at the end of the billing period",
            }
        except stripe.StripeError as e:
            return {"success": False, "message": f"Failed to cancel subscription: {str(e)}"}

    async def handle_checkout_completed(self, session: dict) -> None:
        """
        Handle successful checkout completion.

        Args:
            session: Stripe checkout session data
        """
        # Extract user info from metadata
        user_id = session.get("metadata", {}).get("user_id")
        if not user_id:
            return

        # Get the subscription
        subscription_id = session.get("subscription")
        if not subscription_id:
            return

        # Update user in database
        result = await self.db_session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            old_tier = user.subscription_tier
            user.stripe_subscription_id = subscription_id
            user.subscription_status = "active"
            
            # Handle tier change with proper counter resets
            if old_tier != "community":
                from database.service import DatabaseService
                db_service = DatabaseService(self.db_session)
                await db_service.handle_subscription_tier_change(
                    user_id=user.id,
                    new_tier="community",
                    old_tier=old_tier
                )
            else:
                await self.db_session.commit()

    async def handle_subscription_updated(self, subscription: dict) -> None:
        """
        Handle subscription status updates.

        Args:
            subscription: Stripe subscription data
        """
        customer_id = subscription.get("customer")
        if not customer_id:
            return

        # Find user by customer ID
        result = await self.db_session.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        # Store old tier for comparison
        old_tier = user.subscription_tier

        # Update subscription status
        status = subscription.get("status")
        user.subscription_status = status
        user.stripe_subscription_id = subscription.get("id")

        # Determine new tier based on status
        new_tier = old_tier
        if status in ["active", "trialing"]:
            new_tier = "community"
        elif status in ["canceled", "incomplete_expired", "past_due", "unpaid"]:
            new_tier = "free"

        # Handle tier change with proper counter resets
        if new_tier != old_tier:
            from database.service import DatabaseService
            db_service = DatabaseService(self.db_session)
            await db_service.handle_subscription_tier_change(
                user_id=user.id,
                new_tier=new_tier,
                old_tier=old_tier
            )
        else:
            await self.db_session.commit()

    async def handle_subscription_deleted(self, subscription: dict) -> None:
        """
        Handle subscription deletion/cancellation.

        Args:
            subscription: Stripe subscription data
        """
        customer_id = subscription.get("customer")
        if not customer_id:
            return

        # Find user by customer ID
        result = await self.db_session.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        # Store old tier for logging
        old_tier = user.subscription_tier

        # Update subscription metadata
        user.subscription_status = "canceled"
        user.stripe_subscription_id = None

        # Downgrade to free tier with proper counter resets
        from database.service import DatabaseService
        db_service = DatabaseService(self.db_session)
        await db_service.handle_subscription_tier_change(
            user_id=user.id,
            new_tier="free",
            old_tier=old_tier
        )

