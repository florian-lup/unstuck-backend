"""Application constants and enumerations."""

from enum import Enum
from typing import Any


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SubscriptionTier(str, Enum):
    """Subscription tier types."""

    FREE = "free"
    COMMUNITY = "community"


# Subscription tier limits
SUBSCRIPTION_LIMITS: dict[SubscriptionTier, dict[str, Any]] = {
    SubscriptionTier.FREE: {
        "max_total_requests": 150,  # Lifetime limit for GAMING CHAT, never resets
        "restricted_features": [
            "builds",
            "guides",
            "lore",
        ],  # No access to these features
    },
    SubscriptionTier.COMMUNITY: {
        "max_monthly_requests": 300,  # Monthly limit for GAMING CHAT
        "restricted_features": [
            "builds",
            "guides",
            "lore",
        ],  # No access to these features
    },
}
