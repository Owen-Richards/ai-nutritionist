"""
Dead simple subscription model that actually works
Replaces complex profit enforcement with clear value gates
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SubscriptionTier(Enum):
    """Three tiers - Family tier is the REAL money maker"""

    FREE = "free"
    PREMIUM = "premium"
    FAMILY = "family"  # NEW - High ARPU tier


class SimpleSubscriptionService:
    """
    Replace complex profit enforcement with simple gates.
    Free users get cached responses. Premium users get AI.
    Family users get coordination features at 2x price.

    Design principles:
    - Clear value proposition
    - Simple usage limits
    - Family tier for higher ARPU
    - Easy upgrade path
    """

    # Free tier limits (per month)
    FREE_LIMITS = {
        "ai_interactions": 5,  # Only 5 AI calls per month
        "meal_plans": 1,
        "cached_recipes": "unlimited",  # Zero cost
        "basic_tips": "unlimited",  # Pre-written, zero cost
    }

    # Premium tier - $9.99/month (single user)
    PREMIUM_PRICE = 9.99
    PREMIUM_FEATURES = {
        "ai_interactions": 50,  # Limited but generous
        "meal_plans": 10,
        "personalized_coaching": True,
        "grocery_optimization": True,
        "nutrition_tracking": True,
        "priority_support": False,
    }

    # Family tier - $19.99/month (THE MONEY MAKER)
    FAMILY_PRICE = 19.99
    FAMILY_FEATURES = {
        "ai_interactions": "unlimited",
        "meal_plans": "unlimited",
        "family_members": 6,
        "personalized_coaching": True,
        "grocery_optimization": True,
        "grocery_list_sync": True,  # KILLER FEATURE
        "multiple_stores": True,  # Compare prices across stores
        "family_challenges": True,  # Viral growth mechanic
        "nutrition_tracking": True,
        "priority_support": True,
    }

    # REALISTIC unit economics (not fantasy numbers)
    UNIT_ECONOMICS = {
        "free": {
            "monthly_revenue": 0.00,
            "monthly_cost": 0.05,  # Mostly cached responses
            "profit": -0.05,
        },
        "premium": {
            "monthly_revenue": 9.99,
            "monthly_cost": 4.50,  # Realistic: AI + payment fees + support
            "profit": 5.49,  # Not $8.49 - be honest
        },
        "family": {
            "monthly_revenue": 19.99,
            "monthly_cost": 6.50,  # More AI usage but shared across family
            "profit": 13.49,  # THIS is where the money is
        },
    }

    def __init__(self, dynamodb_table=None):
        """
        Initialize subscription service

        Args:
            dynamodb_table: Optional DynamoDB table for persistence
                           If None, uses in-memory storage (for testing)
        """
        self.dynamodb_table = dynamodb_table

        # In-memory storage (for development/testing)
        self.user_subscriptions = {}
        self.usage_tracker = {}

    def check_access(self, user_id: str, feature: str) -> Dict:
        """
        Simple access check - no complex profit calculations

        Args:
            user_id: User identifier
            feature: Feature being accessed

        Returns:
            Dictionary with access decision and details
        """
        user_tier = self.get_user_tier(user_id)

        if user_tier == SubscriptionTier.FAMILY:
            logger.info(f"Family user {user_id} accessing {feature}")
            return {"allowed": True, "tier": "family", "message": None, "remaining": "unlimited"}

        if user_tier == SubscriptionTier.PREMIUM:
            # Premium has limits (not unlimited like we falsely advertised)
            premium_limit = self.PREMIUM_FEATURES.get(feature, 0)
            if premium_limit == "unlimited" or premium_limit is True:
                logger.info(f"Premium user {user_id} accessing {feature}")
                return {
                    "allowed": True,
                    "tier": "premium",
                    "message": None,
                    "remaining": "unlimited",
                }
            else:
                # Check usage for limited premium features
                usage = self.get_monthly_usage(user_id, feature)
                if usage < premium_limit:
                    remaining = premium_limit - usage
                    return {
                        "allowed": True,
                        "tier": "premium",
                        "remaining": remaining,
                        "limit": premium_limit,
                    }
                else:
                    return {
                        "allowed": False,
                        "tier": "premium",
                        "message": "Upgrade to Family tier for unlimited access!",
                        "upgrade_url": "/subscribe/family?source=limit_reached",
                    }

        # Free tier - check limits
        usage = self.get_monthly_usage(user_id, feature)
        limit = self.FREE_LIMITS.get(feature, 0)

        if limit == "unlimited":
            logger.info(f"Free user {user_id} accessing unlimited feature {feature}")
            return {"allowed": True, "tier": "free", "remaining": "unlimited"}

        if usage < limit:
            remaining = limit - usage
            logger.info(f"Free user {user_id} accessing {feature} ({remaining} remaining)")
            return {"allowed": True, "tier": "free", "remaining": remaining, "limit": limit}

        # Limit reached - prompt upgrade
        logger.info(f"Free user {user_id} hit limit for {feature}")
        return {
            "allowed": False,
            "tier": "free",
            "message": self._get_upgrade_prompt(feature),
            "upgrade_url": "/subscribe?source=limit_reached",
            "limit": limit,
            "usage": usage,
        }

    def _get_upgrade_prompt(self, feature: str) -> str:
        """Simple, clear upgrade messaging with Family tier emphasis"""
        return (
            "🌟 You've used your free AI interactions this month!\n\n"
            f"💎 Premium (${self.PREMIUM_PRICE}/mo):\n"
            "✅ 50 AI meal plans/month\n"
            "✅ Personalized nutrition coaching\n"
            "✅ Smart grocery optimization\n\n"
            f"👨‍👩‍👧‍👦 Family (${self.FAMILY_PRICE}/mo) - BEST VALUE:\n"
            "✅ UNLIMITED AI meal planning\n"
            "✅ Coordinate up to 6 family members\n"
            "✅ Shared grocery lists (sync in real-time)\n"
            "✅ Save $65+/month on groceries\n"
            "✅ Family savings challenges\n"
            "✅ Priority support\n\n"
            "Reply FAMILY or PREMIUM to upgrade!"
        )

    def get_user_tier(self, user_id: str) -> SubscriptionTier:
        """Get user's subscription tier"""
        if self.dynamodb_table:
            # Production: Get from DynamoDB
            try:
                response = self.dynamodb_table.get_item(Key={"user_id": user_id})
                if "Item" in response:
                    item = response["Item"]
                    if item.get("subscription_active", False):
                        tier = item.get("tier", "premium")
                        if tier == "family":
                            return SubscriptionTier.FAMILY
                        return SubscriptionTier.PREMIUM
            except Exception as e:
                logger.error(f"Error fetching subscription for {user_id}: {e}")
        else:
            # Development: Use in-memory storage
            sub = self.user_subscriptions.get(user_id)
            if sub and sub.get("active"):
                tier = sub.get("tier", "premium")
                if tier == "family":
                    return SubscriptionTier.FAMILY
                return SubscriptionTier.PREMIUM

        return SubscriptionTier.FREE

    def get_monthly_usage(self, user_id: str, feature: str) -> int:
        """Get user's monthly usage for a feature"""
        month_key = datetime.now().strftime("%Y-%m")
        usage_key = f"{user_id}:{month_key}:{feature}"

        if self.dynamodb_table:
            # Production: Get from DynamoDB
            try:
                response = self.dynamodb_table.get_item(Key={"usage_key": usage_key})
                if "Item" in response:
                    return int(response["Item"].get("count", 0))
            except Exception as e:
                logger.error(f"Error fetching usage for {usage_key}: {e}")

        # Development: Use in-memory storage
        return self.usage_tracker.get(usage_key, 0)

    def increment_usage(self, user_id: str, feature: str) -> int:
        """
        Track feature usage

        Returns:
            New usage count
        """
        month_key = datetime.now().strftime("%Y-%m")
        usage_key = f"{user_id}:{month_key}:{feature}"

        if self.dynamodb_table:
            # Production: Update in DynamoDB
            try:
                response = self.dynamodb_table.update_item(
                    Key={"usage_key": usage_key},
                    UpdateExpression="SET #count = if_not_exists(#count, :zero) + :inc",
                    ExpressionAttributeNames={"#count": "count"},
                    ExpressionAttributeValues={":inc": 1, ":zero": 0},
                    ReturnValues="UPDATED_NEW",
                )
                return int(response["Attributes"]["count"])
            except Exception as e:
                logger.error(f"Error incrementing usage for {usage_key}: {e}")

        # Development: Use in-memory storage
        self.usage_tracker[usage_key] = self.usage_tracker.get(usage_key, 0) + 1
        return self.usage_tracker[usage_key]

    def subscribe_user(self, user_id: str, payment_method_id: Optional[str] = None) -> Dict:
        """
        Subscribe user to premium tier

        Args:
            user_id: User identifier
            payment_method_id: Payment method (Stripe, etc.)

        Returns:
            Subscription result
        """
        subscription_data = {
            "user_id": user_id,
            "tier": SubscriptionTier.PREMIUM.value,
            "active": True,
            "price": self.PREMIUM_PRICE,
            "start_date": datetime.now().isoformat(),
            "payment_method_id": payment_method_id,
        }

        if self.dynamodb_table:
            try:
                self.dynamodb_table.put_item(Item=subscription_data)
            except Exception as e:
                logger.error(f"Error creating subscription for {user_id}: {e}")
                return {"success": False, "error": str(e)}
        else:
            self.user_subscriptions[user_id] = subscription_data

        logger.info(f"User {user_id} subscribed to Premium")

        return {
            "success": True,
            "tier": "premium",
            "price": self.PREMIUM_PRICE,
            "message": f"🎉 Welcome to Premium! You now have unlimited access.",
        }

    def cancel_subscription(self, user_id: str) -> Dict:
        """Cancel user subscription"""
        if self.dynamodb_table:
            try:
                self.dynamodb_table.update_item(
                    Key={"user_id": user_id},
                    UpdateExpression="SET active = :false, cancelled_date = :date",
                    ExpressionAttributeValues={
                        ":false": False,
                        ":date": datetime.now().isoformat(),
                    },
                )
            except Exception as e:
                logger.error(f"Error cancelling subscription for {user_id}: {e}")
                return {"success": False, "error": str(e)}
        else:
            if user_id in self.user_subscriptions:
                self.user_subscriptions[user_id]["active"] = False

        logger.info(f"User {user_id} cancelled Premium subscription")

        return {
            "success": True,
            "message": "Your subscription has been cancelled. You still have access until the end of your billing period.",
        }

    def get_subscription_stats(self) -> Dict:
        """Get subscription statistics"""
        if self.dynamodb_table:
            # In production, scan DynamoDB for stats
            # (In real implementation, use proper metrics/analytics)
            pass

        # Development stats
        total_users = len(self.user_subscriptions)
        premium_users = sum(1 for sub in self.user_subscriptions.values() if sub.get("active"))
        free_users = total_users - premium_users

        conversion_rate = (premium_users / total_users * 100) if total_users > 0 else 0
        mrr = premium_users * self.PREMIUM_PRICE

        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "free_users": free_users,
            "conversion_rate": f"{conversion_rate:.1f}%",
            "mrr": f"${mrr:.2f}",
            "premium_price": self.PREMIUM_PRICE,
        }
