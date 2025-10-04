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
        import logging
        logger = logging.getLogger(__name__)
        
        # Create or retrieve Stripe customer
        customer_id = None
        if user.stripe_customer_id:
            try:
                # Try to retrieve the customer to verify it exists
                stripe.Customer.retrieve(user.stripe_customer_id)
                customer_id = user.stripe_customer_id
                logger.info(f"Using existing Stripe customer: {customer_id}")
            except stripe.StripeError as e:
                # Customer doesn't exist (likely switched from live to test mode)
                logger.warning(f"Stripe customer {user.stripe_customer_id} not found: {e}. Creating new customer.")
                customer_id = None
        
        if not customer_id:
            customer = stripe.Customer.create(
                email=user_email,
                metadata={"user_id": str(user.id), "auth0_user_id": str(user.auth0_user_id)},
            )
            customer_id = customer.id
            logger.info(f"Created new Stripe customer: {customer_id}")

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
        import logging
        logger = logging.getLogger(__name__)
        
        # Extract user info from metadata
        user_id = session.get("metadata", {}).get("user_id")
        logger.info(f"Checkout completed - User ID from metadata: {user_id}")
        
        if not user_id:
            logger.error("No user_id found in checkout session metadata")
            return

        # Get the subscription
        subscription_id = session.get("subscription")
        logger.info(f"Checkout completed - Subscription ID: {subscription_id}")
        
        if not subscription_id:
            logger.error("No subscription_id found in checkout session")
            return

        try:
            # Update user in database
            result = await self.db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User not found in database with ID: {user_id}")
                return

            logger.info(f"Found user: {user.auth0_user_id}, Current tier: {user.subscription_tier}, Current status: {user.subscription_status}")
            
            old_tier = user.subscription_tier
            user.stripe_subscription_id = subscription_id
            user.subscription_status = "active"
            
            # Handle tier change with proper counter resets
            if old_tier != "community":
                logger.info(f"Upgrading user from {old_tier} to community tier")
                from database.service import DatabaseService
                db_service = DatabaseService(self.db_session)
                await db_service.handle_subscription_tier_change(
                    user_id=user.id,
                    new_tier="community",
                    old_tier=old_tier
                )
                logger.info(f"Successfully upgraded user {user.id} to community tier")
            else:
                logger.info("User already on community tier, updating subscription status only")
                await self.db_session.commit()
                
        except Exception as e:
            logger.error(f"Error in handle_checkout_completed: {e}", exc_info=True)
            await self.db_session.rollback()
            raise

    async def handle_subscription_updated(self, subscription: dict) -> None:
        """
        Handle subscription status updates.

        Args:
            subscription: Stripe subscription data
        """
        import logging
        logger = logging.getLogger(__name__)
        
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

        # Check if subscription is set to cancel at period end
        cancel_at_period_end = subscription.get("cancel_at_period_end", False)
        status = subscription.get("status")
        
        logger.info(f"Subscription update for user {user.id}: status={status}, cancel_at_period_end={cancel_at_period_end}")

        # Update subscription status
        # If cancel_at_period_end is True, keep status as "canceling" even if Stripe says "active"
        if cancel_at_period_end and status == "active":
            user.subscription_status = "canceling"
            logger.info(f"Keeping subscription status as 'canceling' for user {user.id} (cancel_at_period_end=True)")
        else:
            user.subscription_status = status
        
        user.stripe_subscription_id = subscription.get("id")

        # Determine new tier based on status
        new_tier = old_tier
        
        # Don't upgrade if subscription is set to cancel
        if cancel_at_period_end:
            # Keep current tier until subscription is actually deleted
            new_tier = old_tier
            logger.info(f"Maintaining tier {old_tier} for user {user.id} (subscription set to cancel)")
        elif status in ["active", "trialing"]:
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

