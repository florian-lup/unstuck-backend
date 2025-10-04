"""Subscription management routes."""

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.config import settings
from core.rate_limit import RateLimited
from database.connection import get_db_session
from database.service import DatabaseService
from schemas.auth import AuthenticatedUser
from schemas.subscription import (
    CancelSubscriptionResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    SubscriptionStatusResponse,
)
from services.subscription_service import SubscriptionService

router = APIRouter()


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: Request,
    checkout_request: CheckoutSessionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> CheckoutSessionResponse:
    """
    Create a Stripe checkout session for Community subscription.

    This endpoint creates a Stripe checkout session and returns the URL
    where the user should be redirected to complete payment.
    """
    # Get user from database
    db_service = DatabaseService(db_session)
    user = await db_service.get_or_create_user(
        auth0_user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.name,
    )

    # Check if user already has an active subscription
    if user.subscription_tier == "community" and user.subscription_status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active Community subscription",
        )

    # Create checkout session
    subscription_service = SubscriptionService(db_session)
    session_data = await subscription_service.create_checkout_session(
        user=user, user_email=current_user.email or ""
    )

    return CheckoutSessionResponse(
        checkout_url=session_data["checkout_url"],
        session_id=session_data["session_id"],
    )


@router.post("/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> CancelSubscriptionResponse:
    """
    Cancel the user's active subscription.

    The subscription will be canceled at the end of the current billing period,
    so the user retains access until then.
    """
    # Get user from database
    db_service = DatabaseService(db_session)
    user = await db_service.get_or_create_user(
        auth0_user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.name,
    )

    # Cancel subscription
    subscription_service = SubscriptionService(db_session)
    result = await subscription_service.cancel_subscription(user)

    success = result["success"]
    message = result["message"]

    return CancelSubscriptionResponse(success=bool(success), message=str(message))


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> SubscriptionStatusResponse:
    """
    Get the current user's subscription status.

    Returns the subscription tier (free/community) and Stripe subscription status.
    """
    # Get user from database
    db_service = DatabaseService(db_session)
    user = await db_service.get_or_create_user(
        auth0_user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.name,
    )

    return SubscriptionStatusResponse(
        subscription_tier=user.subscription_tier,
        subscription_status=user.subscription_status,
        stripe_customer_id=user.stripe_customer_id,
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict[str, str]:
    """
    Handle Stripe webhook events.

    This endpoint receives and processes webhook events from Stripe,
    such as successful payments, subscription updates, and cancellations.

    Security: Verifies webhook signature to ensure requests come from Stripe.
    """
    import logging

    logger = logging.getLogger(__name__)

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    logger.info("Received Stripe webhook request")

    if not sig_header:
        logger.error("Stripe webhook missing signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        logger.info(
            f"Webhook signature verified. Event type: {event['type']}, Event ID: {event.get('id')}"
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
        ) from None
    except stripe.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
        ) from None

    # Handle the event
    subscription_service = SubscriptionService(db_session)

    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            logger.info(
                f"Processing checkout.session.completed. Session ID: {session.get('id')}, Customer: {session.get('customer')}, Subscription: {session.get('subscription')}"
            )
            await subscription_service.handle_checkout_completed(session)
            logger.info("Successfully processed checkout.session.completed")

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            logger.info(
                f"Processing customer.subscription.updated. Subscription ID: {subscription.get('id')}, Status: {subscription.get('status')}"
            )
            await subscription_service.handle_subscription_updated(subscription)
            logger.info("Successfully processed customer.subscription.updated")

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            logger.info(
                f"Processing customer.subscription.deleted. Subscription ID: {subscription.get('id')}"
            )
            await subscription_service.handle_subscription_deleted(subscription)
            logger.info("Successfully processed customer.subscription.deleted")
        else:
            logger.info(f"Unhandled webhook event type: {event['type']}")

    except Exception as e:
        logger.error(
            f"Error processing webhook event {event['type']}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}",
        ) from e

    return {"status": "success"}


@router.get("/webhook-test")
async def webhook_test_endpoint() -> dict[str, str]:
    """
    Test endpoint to verify webhook URL is accessible.
    Returns 200 OK if the endpoint is reachable.
    """
    return {
        "status": "ok",
        "message": "Webhook endpoint is accessible",
        "webhook_url": "/subscription/webhook",
    }
