"""Monetization models for Track E1 - Subscription Tiers.

Defines subscription tiers, entitlements, and pricing models.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class BillingInterval(str, Enum):
    """Billing frequency options."""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    """Subscription status states."""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"


class FeatureFlag(str, Enum):
    """Available feature flags."""
    # Core features
    BASIC_MEAL_PLANS = "basic_meal_plans"
    SMS_NUDGES = "sms_nudges"
    
    # Premium features
    ADAPTIVE_PLANNING = "adaptive_planning"
    WIDGETS = "widgets"
    ADVANCED_NUTRITION = "advanced_nutrition"
    MEAL_CUSTOMIZATION = "meal_customization"
    
    # Enterprise features
    CREWS = "crews"
    CALENDAR_INTEGRATION = "calendar_integration"
    GROCERY_EXPORT = "grocery_export"
    FITNESS_INTEGRATION = "fitness_integration"
    PRIORITY_SUPPORT = "priority_support"
    UNLIMITED_PLANS = "unlimited_plans"


class PricingConfig(BaseModel):
    """Pricing configuration for a tier."""
    tier: SubscriptionTier
    monthly_price_cents: int
    yearly_price_cents: int
    trial_days: int = 7
    currency: str = "USD"
    
    @property
    def monthly_price_usd(self) -> Decimal:
        """Get monthly price in USD."""
        return Decimal(self.monthly_price_cents) / 100
    
    @property
    def yearly_price_usd(self) -> Decimal:
        """Get yearly price in USD."""
        return Decimal(self.yearly_price_cents) / 100
    
    @property
    def yearly_discount_percent(self) -> Decimal:
        """Calculate yearly discount percentage."""
        monthly_annual = self.monthly_price_cents * 12
        if monthly_annual == 0:
            return Decimal("0")
        return ((monthly_annual - self.yearly_price_cents) / monthly_annual) * 100


class FeatureEntitlement(BaseModel):
    """Feature entitlement definition."""
    feature: FeatureFlag
    enabled: bool = True
    limit: Optional[int] = None  # None = unlimited
    metadata: Dict = Field(default_factory=dict)


class TierDefinition(BaseModel):
    """Complete tier definition with features and pricing."""
    tier: SubscriptionTier
    name: str
    description: str
    pricing: PricingConfig
    features: List[FeatureEntitlement]
    
    def get_feature_entitlement(self, feature: FeatureFlag) -> Optional[FeatureEntitlement]:
        """Get entitlement for a specific feature."""
        for entitlement in self.features:
            if entitlement.feature == feature:
                return entitlement
        return None
    
    def has_feature(self, feature: FeatureFlag) -> bool:
        """Check if tier has access to a feature."""
        entitlement = self.get_feature_entitlement(feature)
        return entitlement is not None and entitlement.enabled


class Subscription(BaseModel):
    """User subscription model."""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    tier: SubscriptionTier
    status: SubscriptionStatus
    billing_interval: BillingInterval
    
    # Dates
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Stripe references
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    
    # Pricing
    price_cents: int = 0
    currency: str = "USD"
    
    # Trial tracking
    trial_used: bool = False
    trial_days_remaining: int = 0
    
    # Experiment tracking
    experiment_cohort: Optional[str] = None
    pricing_variant: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
    
    @property
    def is_in_trial(self) -> bool:
        """Check if subscription is in trial period."""
        return (
            self.status == SubscriptionStatus.TRIALING and
            self.trial_end and
            self.trial_end > datetime.now()
        )
    
    @property
    def days_until_renewal(self) -> Optional[int]:
        """Get days until next renewal."""
        if not self.current_period_end:
            return None
        delta = self.current_period_end - datetime.now()
        return max(0, delta.days)
    
    def get_price_usd(self) -> Decimal:
        """Get subscription price in USD."""
        return Decimal(self.price_cents) / 100


class MonetizationConfig:
    """Central configuration for monetization system."""
    
    def __init__(self):
        self._pricing_configs = self._create_pricing_configs()
        self._tier_definitions = self._create_tier_definitions()
    
    def _create_pricing_configs(self) -> Dict[SubscriptionTier, PricingConfig]:
        """Create pricing configurations for all tiers."""
        return {
            SubscriptionTier.FREE: PricingConfig(
                tier=SubscriptionTier.FREE,
                monthly_price_cents=0,
                yearly_price_cents=0,
                trial_days=0
            ),
            SubscriptionTier.PREMIUM: PricingConfig(
                tier=SubscriptionTier.PREMIUM,
                monthly_price_cents=799,  # $7.99
                yearly_price_cents=7990,  # $79.90 (17% discount - 2 months free)
                trial_days=7
            ),
            SubscriptionTier.ENTERPRISE: PricingConfig(
                tier=SubscriptionTier.ENTERPRISE,
                monthly_price_cents=9900,  # $99.00
                yearly_price_cents=99000,  # $990.00 (17% discount - 2 months free)
                trial_days=7
            )
        }
    
    def _create_tier_definitions(self) -> Dict[SubscriptionTier, TierDefinition]:
        """Create complete tier definitions."""
        return {
            SubscriptionTier.FREE: TierDefinition(
                tier=SubscriptionTier.FREE,
                name="Free",
                description="Basic meal planning with SMS nudges",
                pricing=self._pricing_configs[SubscriptionTier.FREE],
                features=[
                    FeatureEntitlement(
                        feature=FeatureFlag.BASIC_MEAL_PLANS,
                        enabled=True,
                        limit=1,  # 1 active plan at a time
                        metadata={"plans_per_week": 1}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.SMS_NUDGES,
                        enabled=True,
                        limit=3,  # 3 SMS per week max
                        metadata={"sms_per_week": 3}
                    )
                ]
            ),
            SubscriptionTier.PREMIUM: TierDefinition(
                tier=SubscriptionTier.PREMIUM,
                name="Premium",
                description="Unlimited plans, nutrition analysis with widgets and advanced features",
                pricing=self._pricing_configs[SubscriptionTier.PREMIUM],
                features=[
                    # Inherit free features
                    FeatureEntitlement(
                        feature=FeatureFlag.BASIC_MEAL_PLANS,
                        enabled=True,
                        limit=5,  # 5 active plans
                        metadata={"plans_per_week": 3}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.SMS_NUDGES,
                        enabled=True,
                        limit=7,  # Daily SMS
                        metadata={"sms_per_week": 7}
                    ),
                    # Premium exclusive features
                    FeatureEntitlement(
                        feature=FeatureFlag.ADAPTIVE_PLANNING,
                        enabled=True,
                        metadata={"ai_recommendations": True, "learning_enabled": True}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.WIDGETS,
                        enabled=True,
                        metadata={"ios_widget": True, "android_widget": True}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.ADVANCED_NUTRITION,
                        enabled=True,
                        metadata={"macro_tracking": True, "nutrient_analysis": True}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.MEAL_CUSTOMIZATION,
                        enabled=True,
                        metadata={"ingredient_swaps": True, "portion_adjustment": True}
                    )
                ]
            ),
            SubscriptionTier.ENTERPRISE: TierDefinition(
                tier=SubscriptionTier.ENTERPRISE,
                name="Enterprise",
                description="Complete nutrition platform with 10 seats, API access, and analytics",
                pricing=self._pricing_configs[SubscriptionTier.ENTERPRISE],
                features=[
                    # Inherit Premium features (unlimited for Enterprise)
                    FeatureEntitlement(
                        feature=FeatureFlag.BASIC_MEAL_PLANS,
                        enabled=True,
                        limit=None,  # Unlimited
                        metadata={"plans_per_week": None}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.SMS_NUDGES,
                        enabled=True,
                        limit=None,  # Unlimited
                        metadata={"sms_per_week": None}
                    ),
                    FeatureEntitlement(feature=FeatureFlag.ADAPTIVE_PLANNING, enabled=True),
                    FeatureEntitlement(feature=FeatureFlag.WIDGETS, enabled=True),
                    FeatureEntitlement(feature=FeatureFlag.ADVANCED_NUTRITION, enabled=True),
                    FeatureEntitlement(feature=FeatureFlag.MEAL_CUSTOMIZATION, enabled=True),
                    # Enterprise exclusive features
                    FeatureEntitlement(
                        feature=FeatureFlag.CREWS,
                        enabled=True,
                        metadata={"max_crews": 10, "crew_admin": True}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.CALENDAR_INTEGRATION,
                        enabled=True,
                        metadata={"google_calendar": True, "outlook": True, "meal_events": True}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.GROCERY_EXPORT,
                        enabled=True,
                        metadata={"csv_export": True, "partner_links": True, "auto_order": True}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.FITNESS_INTEGRATION,
                        enabled=True,
                        metadata={"apple_health": True, "google_fit": True, "recovery_meals": True}
                    ),
                    FeatureEntitlement(
                        feature=FeatureFlag.PRIORITY_SUPPORT,
                        enabled=True,
                        metadata={"response_time_hours": 4, "dedicated_support": True}
                    ),
                    FeatureEntitlement(feature=FeatureFlag.UNLIMITED_PLANS, enabled=True)
                ]
            )
        }
    
    def get_tier_definition(self, tier: SubscriptionTier) -> TierDefinition:
        """Get tier definition by tier."""
        return self._tier_definitions[tier]
    
    def get_pricing_config(self, tier: SubscriptionTier) -> PricingConfig:
        """Get pricing config by tier."""
        return self._pricing_configs[tier]
    
    def get_all_tiers(self) -> List[TierDefinition]:
        """Get all tier definitions."""
        return list(self._tier_definitions.values())
    
    def get_upgrade_path(self, current_tier: SubscriptionTier) -> List[SubscriptionTier]:
        """Get available upgrade tiers."""
        tier_order = [SubscriptionTier.FREE, SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE]
        current_index = tier_order.index(current_tier)
        return tier_order[current_index + 1:]
    
    def calculate_upgrade_cost(self, current_tier: SubscriptionTier, 
                             target_tier: SubscriptionTier,
                             billing_interval: BillingInterval = BillingInterval.MONTHLY) -> Decimal:
        """Calculate cost to upgrade between tiers."""
        current_pricing = self.get_pricing_config(current_tier)
        target_pricing = self.get_pricing_config(target_tier)
        
        if billing_interval == BillingInterval.MONTHLY:
            return target_pricing.monthly_price_usd - current_pricing.monthly_price_usd
        else:
            return target_pricing.yearly_price_usd - current_pricing.yearly_price_usd


class UsageTracker(BaseModel):
    """Track feature usage against entitlements."""
    user_id: UUID
    subscription_id: UUID
    period_start: datetime
    period_end: datetime
    
    # Usage counters
    meal_plans_created: int = 0
    sms_sent: int = 0
    widget_views: int = 0
    crew_interactions: int = 0
    calendar_events_created: int = 0
    grocery_exports: int = 0
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)
    
    def reset_for_new_period(self, period_start: datetime, period_end: datetime) -> UsageTracker:
        """Reset usage counters for new billing period."""
        return UsageTracker(
            user_id=self.user_id,
            subscription_id=self.subscription_id,
            period_start=period_start,
            period_end=period_end
        )
    
    def increment_usage(self, feature: FeatureFlag, amount: int = 1) -> None:
        """Increment usage counter for a feature."""
        if feature == FeatureFlag.BASIC_MEAL_PLANS:
            self.meal_plans_created += amount
        elif feature == FeatureFlag.SMS_NUDGES:
            self.sms_sent += amount
        elif feature == FeatureFlag.WIDGETS:
            self.widget_views += amount
        elif feature == FeatureFlag.CREWS:
            self.crew_interactions += amount
        elif feature == FeatureFlag.CALENDAR_INTEGRATION:
            self.calendar_events_created += amount
        elif feature == FeatureFlag.GROCERY_EXPORT:
            self.grocery_exports += amount
        
        self.last_updated = datetime.now()
    
    def get_usage(self, feature: FeatureFlag) -> int:
        """Get current usage for a feature."""
        if feature == FeatureFlag.BASIC_MEAL_PLANS:
            return self.meal_plans_created
        elif feature == FeatureFlag.SMS_NUDGES:
            return self.sms_sent
        elif feature == FeatureFlag.WIDGETS:
            return self.widget_views
        elif feature == FeatureFlag.CREWS:
            return self.crew_interactions
        elif feature == FeatureFlag.CALENDAR_INTEGRATION:
            return self.calendar_events_created
        elif feature == FeatureFlag.GROCERY_EXPORT:
            return self.grocery_exports
        return 0


# Export main classes
__all__ = [
    "SubscriptionTier",
    "BillingInterval", 
    "SubscriptionStatus",
    "FeatureFlag",
    "PricingConfig",
    "FeatureEntitlement",
    "TierDefinition",
    "Subscription",
    "MonetizationConfig",
    "UsageTracker"
]
