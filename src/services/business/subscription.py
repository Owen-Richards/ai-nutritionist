"""
Subscription Management Service

Comprehensive subscription lifecycle management with advanced billing,
tier management, and revenue optimization capabilities.

Consolidates functionality from:
- subscription_service.py
- billing_service.py
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)


class SubscriptionTier(Enum):
    """Subscription tier levels."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(Enum):
    """Subscription status states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"
    TRIAL = "trial"


class BillingCycle(Enum):
    """Billing cycle options."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class PaymentMethod(Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"


class RevenueMetric(Enum):
    """Revenue tracking metrics."""
    MRR = "monthly_recurring_revenue"
    ARR = "annual_recurring_revenue"
    LTV = "lifetime_value"
    CAC = "customer_acquisition_cost"
    CHURN_RATE = "churn_rate"
    CONVERSION_RATE = "conversion_rate"


@dataclass
class SubscriptionFeature:
    """Individual subscription feature."""
    feature_id: str
    name: str
    description: str
    included_in_tiers: List[SubscriptionTier]
    usage_limits: Dict[SubscriptionTier, Optional[int]]
    is_premium: bool = False
    feature_group: Optional[str] = None


@dataclass
class TierConfiguration:
    """Configuration for a subscription tier."""
    tier: SubscriptionTier
    name: str
    description: str
    monthly_price: Decimal
    yearly_price: Decimal
    trial_days: int
    features: List[str]
    usage_limits: Dict[str, int]
    priority_support: bool
    api_rate_limit: int
    storage_limit_gb: int
    custom_branding: bool
    analytics_retention_days: int


@dataclass
class PaymentInformation:
    """Payment method information."""
    payment_id: str
    method: PaymentMethod
    last_four: Optional[str]
    expiry_month: Optional[int]
    expiry_year: Optional[int]
    billing_address: Dict[str, str]
    is_default: bool
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BillingHistory:
    """Billing transaction record."""
    transaction_id: str
    user_id: str
    amount: Decimal
    currency: str
    description: str
    status: str  # success, failed, pending, refunded
    payment_method: PaymentMethod
    billing_date: datetime
    due_date: Optional[datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageMetrics:
    """User usage metrics for billing."""
    user_id: str
    tier: SubscriptionTier
    period_start: datetime
    period_end: datetime
    api_calls: int
    storage_used_gb: float
    features_accessed: Dict[str, int]
    overage_charges: Dict[str, Decimal]
    total_overage: Decimal


@dataclass
class SubscriptionAnalytics:
    """Subscription analytics and insights."""
    metric_type: RevenueMetric
    value: Decimal
    period: str
    growth_rate: float
    trend: str  # increasing, decreasing, stable
    benchmark_comparison: Optional[float]
    calculated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChurnPrediction:
    """Churn prediction analysis."""
    user_id: str
    churn_probability: float
    risk_level: str  # low, medium, high, critical
    key_risk_factors: List[Tuple[str, float]]
    recommended_actions: List[str]
    prediction_confidence: float
    analysis_date: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Subscription:
    """Complete subscription record."""
    subscription_id: str
    user_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    start_date: datetime
    end_date: Optional[datetime]
    trial_end_date: Optional[datetime]
    auto_renew: bool
    payment_method: Optional[PaymentInformation]
    current_period_start: datetime
    current_period_end: datetime
    usage_metrics: Optional[UsageMetrics]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class SubscriptionService:
    """
    Advanced subscription management service with comprehensive billing.
    
    Features:
    - Multi-tier subscription management with flexible configurations
    - Advanced billing system with multiple payment methods
    - Usage-based billing with overage protection
    - Churn prediction and retention optimization
    - Revenue analytics and growth tracking
    - Automated billing workflows and notifications
    - Enterprise-grade security and compliance
    - International billing and tax management
    """

    def __init__(self):
        self.subscriptions: Dict[str, Subscription] = {}
        self.tier_configurations: Dict[SubscriptionTier, TierConfiguration] = {}
        self.subscription_features: Dict[str, SubscriptionFeature] = {}
        self.billing_history: List[BillingHistory] = []
        self.usage_metrics: Dict[str, UsageMetrics] = {}
        self.analytics_cache: Dict[str, SubscriptionAnalytics] = {}
        self.churn_predictions: Dict[str, ChurnPrediction] = {}
        
        # Initialize default configurations
        self._initialize_tier_configurations()
        self._initialize_subscription_features()

    def create_subscription(
        self,
        user_id: str,
        tier: str,
        billing_cycle: str = "monthly",
        payment_method: Optional[Dict[str, Any]] = None,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a new subscription for a user.
        
        Args:
            user_id: User identifier
            tier: Subscription tier
            billing_cycle: Billing cycle
            payment_method: Payment method information
            trial_days: Trial period duration
            metadata: Additional subscription data
            
        Returns:
            Subscription ID if successful
        """
        try:
            tier_enum = SubscriptionTier(tier.lower())
            cycle_enum = BillingCycle(billing_cycle.lower())
            
            # Check if user already has an active subscription
            existing_sub = self._get_active_subscription(user_id)
            if existing_sub:
                logger.warning(f"User {user_id} already has active subscription")
                return None
            
            # Generate subscription ID
            subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
            
            # Get tier configuration
            tier_config = self.tier_configurations.get(tier_enum)
            if not tier_config:
                logger.error(f"Invalid tier configuration: {tier}")
                return None
            
            # Set up trial period
            trial_end_date = None
            if trial_days or tier_config.trial_days > 0:
                trial_days = trial_days or tier_config.trial_days
                trial_end_date = datetime.utcnow() + timedelta(days=trial_days)
            
            # Process payment method
            payment_info = None
            if payment_method:
                payment_info = self._process_payment_method(payment_method)
            
            # Calculate billing periods
            start_date = datetime.utcnow()
            if trial_end_date:
                period_start = trial_end_date
                status = SubscriptionStatus.TRIAL
            else:
                period_start = start_date
                status = SubscriptionStatus.ACTIVE
            
            period_end = self._calculate_period_end(period_start, cycle_enum)
            
            # Create subscription
            subscription = Subscription(
                subscription_id=subscription_id,
                user_id=user_id,
                tier=tier_enum,
                status=status,
                billing_cycle=cycle_enum,
                start_date=start_date,
                end_date=None,
                trial_end_date=trial_end_date,
                auto_renew=True,
                payment_method=payment_info,
                current_period_start=period_start,
                current_period_end=period_end,
                usage_metrics=None,
                metadata=metadata or {}
            )
            
            # Store subscription
            self.subscriptions[subscription_id] = subscription
            
            # Initialize usage tracking
            self._initialize_usage_tracking(subscription_id)
            
            # Process initial payment if not trial
            if status == SubscriptionStatus.ACTIVE and payment_info:
                self._process_subscription_payment(subscription)
            
            logger.info(f"Created subscription {subscription_id} for user {user_id}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None

    def upgrade_subscription(
        self,
        subscription_id: str,
        new_tier: str,
        immediate: bool = True
    ) -> bool:
        """
        Upgrade subscription to a higher tier.
        
        Args:
            subscription_id: Subscription identifier
            new_tier: Target tier
            immediate: Whether to upgrade immediately
            
        Returns:
            Success status
        """
        try:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            new_tier_enum = SubscriptionTier(new_tier.lower())
            current_tier_config = self.tier_configurations[subscription.tier]
            new_tier_config = self.tier_configurations[new_tier_enum]
            
            # Validate upgrade path
            if not self._is_valid_upgrade(subscription.tier, new_tier_enum):
                logger.warning(f"Invalid upgrade from {subscription.tier} to {new_tier_enum}")
                return False
            
            if immediate:
                # Calculate prorated charges
                prorated_amount = self._calculate_prorated_amount(
                    subscription, new_tier_config
                )
                
                # Process upgrade payment
                if prorated_amount > 0 and subscription.payment_method:
                    payment_success = self._process_payment(
                        subscription.user_id,
                        prorated_amount,
                        f"Upgrade to {new_tier_config.name}",
                        subscription.payment_method
                    )
                    
                    if not payment_success:
                        logger.error("Failed to process upgrade payment")
                        return False
                
                # Update subscription
                subscription.tier = new_tier_enum
                subscription.updated_at = datetime.utcnow()
                
                # Update usage limits
                self._update_usage_limits(subscription)
                
                logger.info(f"Upgraded subscription {subscription_id} to {new_tier}")
                return True
            else:
                # Schedule upgrade for next billing cycle
                subscription.metadata["scheduled_tier_change"] = {
                    "new_tier": new_tier,
                    "effective_date": subscription.current_period_end.isoformat()
                }
                subscription.updated_at = datetime.utcnow()
                
                logger.info(f"Scheduled upgrade for subscription {subscription_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error upgrading subscription: {e}")
            return False

    def downgrade_subscription(
        self,
        subscription_id: str,
        new_tier: str,
        immediate: bool = False
    ) -> bool:
        """
        Downgrade subscription to a lower tier.
        
        Args:
            subscription_id: Subscription identifier
            new_tier: Target tier
            immediate: Whether to downgrade immediately
            
        Returns:
            Success status
        """
        try:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            new_tier_enum = SubscriptionTier(new_tier.lower())
            
            # Validate downgrade
            if not self._is_valid_downgrade(subscription.tier, new_tier_enum):
                logger.warning(f"Invalid downgrade from {subscription.tier} to {new_tier_enum}")
                return False
            
            if immediate:
                # Check if downgrade affects current usage
                usage_conflicts = self._check_usage_conflicts(subscription, new_tier_enum)
                if usage_conflicts:
                    logger.warning(f"Usage conflicts prevent immediate downgrade: {usage_conflicts}")
                    return False
                
                # Update subscription
                subscription.tier = new_tier_enum
                subscription.updated_at = datetime.utcnow()
                
                # Update usage limits
                self._update_usage_limits(subscription)
                
                logger.info(f"Downgraded subscription {subscription_id} to {new_tier}")
                return True
            else:
                # Schedule downgrade for next billing cycle
                subscription.metadata["scheduled_tier_change"] = {
                    "new_tier": new_tier,
                    "effective_date": subscription.current_period_end.isoformat()
                }
                subscription.updated_at = datetime.utcnow()
                
                logger.info(f"Scheduled downgrade for subscription {subscription_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error downgrading subscription: {e}")
            return False

    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False,
        reason: Optional[str] = None
    ) -> bool:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription identifier
            immediate: Whether to cancel immediately
            reason: Cancellation reason
            
        Returns:
            Success status
        """
        try:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            if immediate:
                # Cancel immediately
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.end_date = datetime.utcnow()
                subscription.auto_renew = False
            else:
                # Cancel at end of current period
                subscription.auto_renew = False
                subscription.metadata["cancellation_scheduled"] = True
                subscription.metadata["cancellation_date"] = subscription.current_period_end.isoformat()
            
            # Record cancellation reason
            if reason:
                subscription.metadata["cancellation_reason"] = reason
            
            subscription.updated_at = datetime.utcnow()
            
            # Process any refunds if applicable
            if immediate and self._is_refund_eligible(subscription):
                self._process_refund(subscription)
            
            logger.info(f"Cancelled subscription {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False

    def process_billing_cycle(self, subscription_id: str) -> bool:
        """
        Process billing for the next cycle.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            Success status
        """
        try:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            # Check if subscription should renew
            if not subscription.auto_renew:
                subscription.status = SubscriptionStatus.EXPIRED
                subscription.end_date = subscription.current_period_end
                logger.info(f"Subscription {subscription_id} expired (auto-renew disabled)")
                return True
            
            # Apply any scheduled tier changes
            if "scheduled_tier_change" in subscription.metadata:
                tier_change = subscription.metadata["scheduled_tier_change"]
                subscription.tier = SubscriptionTier(tier_change["new_tier"])
                del subscription.metadata["scheduled_tier_change"]
            
            # Calculate billing amount
            tier_config = self.tier_configurations[subscription.tier]
            base_amount = self._get_tier_price(tier_config, subscription.billing_cycle)
            
            # Add overage charges
            usage_metrics = self.usage_metrics.get(subscription_id)
            overage_amount = usage_metrics.total_overage if usage_metrics else Decimal("0")
            
            total_amount = base_amount + overage_amount
            
            # Process payment
            if total_amount > 0 and subscription.payment_method:
                payment_success = self._process_payment(
                    subscription.user_id,
                    total_amount,
                    f"Subscription renewal - {tier_config.name}",
                    subscription.payment_method
                )
                
                if not payment_success:
                    # Handle payment failure
                    subscription.status = SubscriptionStatus.SUSPENDED
                    logger.error(f"Payment failed for subscription {subscription_id}")
                    return False
            
            # Update billing period
            subscription.current_period_start = subscription.current_period_end
            subscription.current_period_end = self._calculate_period_end(
                subscription.current_period_start, subscription.billing_cycle
            )
            
            # Reset usage metrics
            self._reset_usage_metrics(subscription_id)
            
            subscription.updated_at = datetime.utcnow()
            
            logger.info(f"Processed billing for subscription {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing billing cycle: {e}")
            return False

    def track_usage(
        self,
        subscription_id: str,
        feature: str,
        amount: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track feature usage for a subscription.
        
        Args:
            subscription_id: Subscription identifier
            feature: Feature being used
            amount: Usage amount
            metadata: Additional usage data
            
        Returns:
            Success status
        """
        try:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            # Get or create usage metrics
            usage_metrics = self.usage_metrics.get(subscription_id)
            if not usage_metrics:
                usage_metrics = self._create_usage_metrics(subscription)
                self.usage_metrics[subscription_id] = usage_metrics
            
            # Track feature usage
            current_usage = usage_metrics.features_accessed.get(feature, 0)
            usage_metrics.features_accessed[feature] = current_usage + amount
            
            # Check for overages
            tier_config = self.tier_configurations[subscription.tier]
            feature_limit = tier_config.usage_limits.get(feature)
            
            if feature_limit and usage_metrics.features_accessed[feature] > feature_limit:
                overage_amount = self._calculate_overage_charge(
                    feature, usage_metrics.features_accessed[feature] - feature_limit, tier_config
                )
                usage_metrics.overage_charges[feature] = overage_amount
                usage_metrics.total_overage = sum(usage_metrics.overage_charges.values())
            
            logger.debug(f"Tracked usage for subscription {subscription_id}: {feature} +{amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
            return False

    def get_subscription_details(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed subscription information.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            Subscription details
        """
        try:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription:
                return None
            
            tier_config = self.tier_configurations[subscription.tier]
            usage_metrics = self.usage_metrics.get(subscription_id)
            
            # Calculate days remaining
            days_remaining = (subscription.current_period_end - datetime.utcnow()).days
            
            # Get available features
            available_features = self._get_available_features(subscription.tier)
            
            details = {
                "subscription_id": subscription.subscription_id,
                "user_id": subscription.user_id,
                "tier": {
                    "name": tier_config.name,
                    "level": subscription.tier.value,
                    "description": tier_config.description
                },
                "status": subscription.status.value,
                "billing": {
                    "cycle": subscription.billing_cycle.value,
                    "current_period_start": subscription.current_period_start.isoformat(),
                    "current_period_end": subscription.current_period_end.isoformat(),
                    "days_remaining": days_remaining,
                    "auto_renew": subscription.auto_renew
                },
                "features": available_features,
                "usage": {
                    "current_period": usage_metrics.features_accessed if usage_metrics else {},
                    "limits": tier_config.usage_limits,
                    "overage_charges": usage_metrics.overage_charges if usage_metrics else {}
                },
                "trial": {
                    "is_trial": subscription.status == SubscriptionStatus.TRIAL,
                    "trial_end": subscription.trial_end_date.isoformat() if subscription.trial_end_date else None
                },
                "payment_method": {
                    "type": subscription.payment_method.method.value if subscription.payment_method else None,
                    "last_four": subscription.payment_method.last_four if subscription.payment_method else None
                }
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting subscription details: {e}")
            return None

    def get_revenue_analytics(
        self,
        metric_type: str,
        period: str = "monthly"
    ) -> Optional[SubscriptionAnalytics]:
        """
        Get revenue analytics and insights.
        
        Args:
            metric_type: Type of metric to calculate
            period: Analysis period
            
        Returns:
            Analytics data
        """
        try:
            metric_enum = RevenueMetric(metric_type.lower())
            cache_key = f"{metric_type}_{period}"
            
            # Check cache
            if cache_key in self.analytics_cache:
                cached_analytics = self.analytics_cache[cache_key]
                if (datetime.utcnow() - cached_analytics.calculated_at).seconds < 3600:  # 1 hour cache
                    return cached_analytics
            
            # Calculate analytics
            analytics = self._calculate_revenue_metric(metric_enum, period)
            
            # Cache results
            if analytics:
                self.analytics_cache[cache_key] = analytics
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}")
            return None

    def predict_churn(self, user_id: str) -> Optional[ChurnPrediction]:
        """
        Predict churn probability for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Churn prediction analysis
        """
        try:
            # Get user's subscription
            subscription = self._get_active_subscription(user_id)
            if not subscription:
                return None
            
            # Check cache
            if user_id in self.churn_predictions:
                prediction = self.churn_predictions[user_id]
                if (datetime.utcnow() - prediction.analysis_date).days < 7:  # 1 week cache
                    return prediction
            
            # Calculate churn probability
            churn_factors = self._analyze_churn_factors(subscription)
            churn_probability = self._calculate_churn_probability(churn_factors)
            
            # Determine risk level
            if churn_probability >= 0.8:
                risk_level = "critical"
            elif churn_probability >= 0.6:
                risk_level = "high"
            elif churn_probability >= 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Generate recommendations
            recommendations = self._generate_retention_recommendations(churn_factors, risk_level)
            
            # Create prediction
            prediction = ChurnPrediction(
                user_id=user_id,
                churn_probability=churn_probability,
                risk_level=risk_level,
                key_risk_factors=churn_factors,
                recommended_actions=recommendations,
                prediction_confidence=0.85  # Mock confidence
            )
            
            # Cache prediction
            self.churn_predictions[user_id] = prediction
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting churn: {e}")
            return None

    def get_billing_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[BillingHistory]:
        """
        Get billing history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of records
            
        Returns:
            List of billing records
        """
        try:
            user_billing = [
                record for record in self.billing_history
                if record.user_id == user_id
            ]
            
            # Sort by billing date (newest first)
            user_billing.sort(key=lambda x: x.billing_date, reverse=True)
            
            return user_billing[:limit]
            
        except Exception as e:
            logger.error(f"Error getting billing history: {e}")
            return []

    def apply_discount(
        self,
        subscription_id: str,
        discount_code: str,
        discount_amount: Optional[Decimal] = None,
        discount_percentage: Optional[float] = None
    ) -> bool:
        """
        Apply discount to subscription.
        
        Args:
            subscription_id: Subscription identifier
            discount_code: Discount code
            discount_amount: Fixed discount amount
            discount_percentage: Percentage discount
            
        Returns:
            Success status
        """
        try:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription:
                return False
            
            # Validate discount code
            if not self._validate_discount_code(discount_code, subscription):
                return False
            
            # Apply discount
            discount_info = {
                "code": discount_code,
                "applied_at": datetime.utcnow().isoformat()
            }
            
            if discount_amount:
                discount_info["amount"] = str(discount_amount)
            if discount_percentage:
                discount_info["percentage"] = discount_percentage
            
            subscription.metadata["active_discount"] = discount_info
            subscription.updated_at = datetime.utcnow()
            
            logger.info(f"Applied discount {discount_code} to subscription {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying discount: {e}")
            return False

    # Helper methods (continued in implementation)
    def _get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get active subscription for user."""
        for subscription in self.subscriptions.values():
            if (subscription.user_id == user_id and 
                subscription.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]):
                return subscription
        return None

    def _process_payment_method(self, payment_data: Dict[str, Any]) -> PaymentInformation:
        """Process and validate payment method."""
        return PaymentInformation(
            payment_id=f"pm_{uuid.uuid4().hex[:8]}",
            method=PaymentMethod(payment_data.get("method", "credit_card")),
            last_four=payment_data.get("last_four"),
            expiry_month=payment_data.get("expiry_month"),
            expiry_year=payment_data.get("expiry_year"),
            billing_address=payment_data.get("billing_address", {}),
            is_default=True
        )

    def _calculate_period_end(self, start_date: datetime, cycle: BillingCycle) -> datetime:
        """Calculate period end date."""
        if cycle == BillingCycle.MONTHLY:
            return start_date + timedelta(days=30)
        elif cycle == BillingCycle.QUARTERLY:
            return start_date + timedelta(days=90)
        elif cycle == BillingCycle.YEARLY:
            return start_date + timedelta(days=365)
        else:
            return start_date + timedelta(days=36500)  # Lifetime

    def _initialize_usage_tracking(self, subscription_id: str) -> None:
        """Initialize usage tracking for subscription."""
        subscription = self.subscriptions[subscription_id]
        usage_metrics = self._create_usage_metrics(subscription)
        self.usage_metrics[subscription_id] = usage_metrics

    def _create_usage_metrics(self, subscription: Subscription) -> UsageMetrics:
        """Create usage metrics for subscription."""
        return UsageMetrics(
            user_id=subscription.user_id,
            tier=subscription.tier,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            api_calls=0,
            storage_used_gb=0.0,
            features_accessed={},
            overage_charges={},
            total_overage=Decimal("0")
        )

    def _process_subscription_payment(self, subscription: Subscription) -> bool:
        """Process subscription payment."""
        tier_config = self.tier_configurations[subscription.tier]
        amount = self._get_tier_price(tier_config, subscription.billing_cycle)
        
        return self._process_payment(
            subscription.user_id,
            amount,
            f"Subscription - {tier_config.name}",
            subscription.payment_method
        )

    def _process_payment(
        self,
        user_id: str,
        amount: Decimal,
        description: str,
        payment_method: PaymentInformation
    ) -> bool:
        """Process payment transaction."""
        try:
            # Mock payment processing
            transaction = BillingHistory(
                transaction_id=f"txn_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                amount=amount,
                currency="USD",
                description=description,
                status="success",
                payment_method=payment_method.method,
                billing_date=datetime.utcnow(),
                due_date=None
            )
            
            self.billing_history.append(transaction)
            logger.info(f"Processed payment: ${amount} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            return False

    def _get_tier_price(self, tier_config: TierConfiguration, cycle: BillingCycle) -> Decimal:
        """Get price for tier and billing cycle."""
        if cycle == BillingCycle.YEARLY:
            return tier_config.yearly_price
        elif cycle == BillingCycle.QUARTERLY:
            return tier_config.yearly_price / 4
        else:
            return tier_config.monthly_price

    def _is_valid_upgrade(self, current_tier: SubscriptionTier, new_tier: SubscriptionTier) -> bool:
        """Check if upgrade path is valid."""
        tier_hierarchy = [
            SubscriptionTier.FREE,
            SubscriptionTier.BASIC,
            SubscriptionTier.PREMIUM,
            SubscriptionTier.ENTERPRISE
        ]
        
        current_index = tier_hierarchy.index(current_tier)
        new_index = tier_hierarchy.index(new_tier)
        
        return new_index > current_index

    def _is_valid_downgrade(self, current_tier: SubscriptionTier, new_tier: SubscriptionTier) -> bool:
        """Check if downgrade path is valid."""
        tier_hierarchy = [
            SubscriptionTier.FREE,
            SubscriptionTier.BASIC,
            SubscriptionTier.PREMIUM,
            SubscriptionTier.ENTERPRISE
        ]
        
        current_index = tier_hierarchy.index(current_tier)
        new_index = tier_hierarchy.index(new_tier)
        
        return new_index < current_index

    def _calculate_prorated_amount(
        self,
        subscription: Subscription,
        new_tier_config: TierConfiguration
    ) -> Decimal:
        """Calculate prorated amount for tier change."""
        # Simplified prorated calculation
        days_remaining = (subscription.current_period_end - datetime.utcnow()).days
        total_period_days = (subscription.current_period_end - subscription.current_period_start).days
        
        old_daily_rate = self._get_tier_price(
            self.tier_configurations[subscription.tier], subscription.billing_cycle
        ) / total_period_days
        
        new_daily_rate = self._get_tier_price(
            new_tier_config, subscription.billing_cycle
        ) / total_period_days
        
        return (new_daily_rate - old_daily_rate) * days_remaining

    def _update_usage_limits(self, subscription: Subscription) -> None:
        """Update usage limits after tier change."""
        usage_metrics = self.usage_metrics.get(subscription.subscription_id)
        if usage_metrics:
            usage_metrics.tier = subscription.tier

    def _check_usage_conflicts(self, subscription: Subscription, new_tier: SubscriptionTier) -> List[str]:
        """Check for usage conflicts when downgrading."""
        conflicts = []
        
        usage_metrics = self.usage_metrics.get(subscription.subscription_id)
        if not usage_metrics:
            return conflicts
        
        new_tier_config = self.tier_configurations[new_tier]
        
        for feature, current_usage in usage_metrics.features_accessed.items():
            new_limit = new_tier_config.usage_limits.get(feature, 0)
            if current_usage > new_limit:
                conflicts.append(f"{feature}: {current_usage} > {new_limit}")
        
        return conflicts

    def _is_refund_eligible(self, subscription: Subscription) -> bool:
        """Check if subscription is eligible for refund."""
        # Simple refund eligibility (within 30 days of start)
        return (datetime.utcnow() - subscription.start_date).days <= 30

    def _process_refund(self, subscription: Subscription) -> bool:
        """Process refund for cancelled subscription."""
        # Mock refund processing
        logger.info(f"Processing refund for subscription {subscription.subscription_id}")
        return True

    def _reset_usage_metrics(self, subscription_id: str) -> None:
        """Reset usage metrics for new billing period."""
        subscription = self.subscriptions[subscription_id]
        self.usage_metrics[subscription_id] = self._create_usage_metrics(subscription)

    def _calculate_overage_charge(self, feature: str, overage_amount: int, tier_config: TierConfiguration) -> Decimal:
        """Calculate overage charges for feature usage."""
        # Mock overage calculation (would be configured per feature)
        overage_rates = {
            "api_calls": Decimal("0.001"),  # $0.001 per call
            "storage": Decimal("0.1"),      # $0.1 per GB
            "users": Decimal("5.0")         # $5 per additional user
        }
        
        rate = overage_rates.get(feature, Decimal("0.01"))
        return rate * overage_amount

    def _get_available_features(self, tier: SubscriptionTier) -> List[Dict[str, Any]]:
        """Get available features for tier."""
        available = []
        
        for feature in self.subscription_features.values():
            if tier in feature.included_in_tiers:
                usage_limit = feature.usage_limits.get(tier)
                available.append({
                    "id": feature.feature_id,
                    "name": feature.name,
                    "description": feature.description,
                    "usage_limit": usage_limit,
                    "is_premium": feature.is_premium
                })
        
        return available

    def _calculate_revenue_metric(self, metric: RevenueMetric, period: str) -> Optional[SubscriptionAnalytics]:
        """Calculate revenue metrics."""
        # Mock revenue calculation
        if metric == RevenueMetric.MRR:
            value = Decimal("15750.00")
            growth_rate = 0.12
            trend = "increasing"
        elif metric == RevenueMetric.ARR:
            value = Decimal("189000.00")
            growth_rate = 0.15
            trend = "increasing"
        elif metric == RevenueMetric.CHURN_RATE:
            value = Decimal("0.05")
            growth_rate = -0.02
            trend = "decreasing"
        else:
            return None
        
        return SubscriptionAnalytics(
            metric_type=metric,
            value=value,
            period=period,
            growth_rate=growth_rate,
            trend=trend,
            benchmark_comparison=0.08
        )

    def _analyze_churn_factors(self, subscription: Subscription) -> List[Tuple[str, float]]:
        """Analyze factors contributing to churn risk."""
        factors = []
        
        # Usage level
        usage_metrics = self.usage_metrics.get(subscription.subscription_id)
        if usage_metrics:
            api_usage_ratio = usage_metrics.api_calls / 1000  # Normalize
            if api_usage_ratio < 0.3:
                factors.append(("low_usage", 0.4))
        
        # Payment issues
        recent_failures = self._count_recent_payment_failures(subscription.user_id)
        if recent_failures > 0:
            factors.append(("payment_failures", 0.3 * recent_failures))
        
        # Support tickets
        support_tickets = self._count_recent_support_tickets(subscription.user_id)
        if support_tickets > 2:
            factors.append(("support_issues", 0.2))
        
        # Trial conversion
        if subscription.status == SubscriptionStatus.TRIAL:
            days_in_trial = (datetime.utcnow() - subscription.start_date).days
            trial_length = (subscription.trial_end_date - subscription.start_date).days
            if days_in_trial / trial_length > 0.8:  # Near end of trial
                factors.append(("trial_ending", 0.5))
        
        return factors

    def _calculate_churn_probability(self, factors: List[Tuple[str, float]]) -> float:
        """Calculate overall churn probability from factors."""
        if not factors:
            return 0.1  # Base churn rate
        
        # Simple weighted average
        total_weight = sum(weight for _, weight in factors)
        return min(total_weight, 0.95)  # Cap at 95%

    def _generate_retention_recommendations(
        self,
        churn_factors: List[Tuple[str, float]],
        risk_level: str
    ) -> List[str]:
        """Generate recommendations to reduce churn risk."""
        recommendations = []
        
        factor_names = [factor for factor, _ in churn_factors]
        
        if "low_usage" in factor_names:
            recommendations.append("Provide onboarding assistance and usage tutorials")
        
        if "payment_failures" in factor_names:
            recommendations.append("Contact customer to update payment information")
        
        if "support_issues" in factor_names:
            recommendations.append("Proactive customer success outreach")
        
        if "trial_ending" in factor_names:
            recommendations.append("Offer trial extension or limited-time discount")
        
        if risk_level == "critical":
            recommendations.append("Immediate personal outreach from account manager")
            recommendations.append("Consider offering significant discount or free upgrade")
        
        return recommendations

    def _count_recent_payment_failures(self, user_id: str) -> int:
        """Count recent payment failures for user."""
        failures = 0
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        for record in self.billing_history:
            if (record.user_id == user_id and 
                record.status == "failed" and 
                record.billing_date >= cutoff_date):
                failures += 1
        
        return failures

    def _count_recent_support_tickets(self, user_id: str) -> int:
        """Count recent support tickets for user."""
        # Mock support ticket count
        return 1

    def _validate_discount_code(self, discount_code: str, subscription: Subscription) -> bool:
        """Validate discount code."""
        # Mock validation
        valid_codes = ["SAVE10", "WELCOME20", "PREMIUM15"]
        return discount_code in valid_codes

    def _initialize_tier_configurations(self) -> None:
        """Initialize default tier configurations."""
        self.tier_configurations = {
            SubscriptionTier.FREE: TierConfiguration(
                tier=SubscriptionTier.FREE,
                name="Free",
                description="Basic nutrition tracking",
                monthly_price=Decimal("0"),
                yearly_price=Decimal("0"),
                trial_days=0,
                features=["basic_tracking", "food_logging"],
                usage_limits={"api_calls": 100, "storage": 1},
                priority_support=False,
                api_rate_limit=10,
                storage_limit_gb=1,
                custom_branding=False,
                analytics_retention_days=7
            ),
            SubscriptionTier.BASIC: TierConfiguration(
                tier=SubscriptionTier.BASIC,
                name="Basic",
                description="Enhanced nutrition tracking with meal planning",
                monthly_price=Decimal("9.99"),
                yearly_price=Decimal("99.99"),
                trial_days=14,
                features=["basic_tracking", "food_logging", "meal_planning", "basic_analytics"],
                usage_limits={"api_calls": 1000, "storage": 5},
                priority_support=False,
                api_rate_limit=50,
                storage_limit_gb=5,
                custom_branding=False,
                analytics_retention_days=30
            ),
            SubscriptionTier.PREMIUM: TierConfiguration(
                tier=SubscriptionTier.PREMIUM,
                name="Premium",
                description="Advanced features with AI recommendations",
                monthly_price=Decimal("19.99"),
                yearly_price=Decimal("199.99"),
                trial_days=30,
                features=["all_basic", "ai_recommendations", "advanced_analytics", "custom_goals"],
                usage_limits={"api_calls": 10000, "storage": 20},
                priority_support=True,
                api_rate_limit=200,
                storage_limit_gb=20,
                custom_branding=True,
                analytics_retention_days=90
            ),
            SubscriptionTier.ENTERPRISE: TierConfiguration(
                tier=SubscriptionTier.ENTERPRISE,
                name="Enterprise",
                description="Full platform access with priority support",
                monthly_price=Decimal("49.99"),
                yearly_price=Decimal("499.99"),
                trial_days=30,
                features=["all_premium", "priority_support", "custom_integrations", "white_labeling"],
                usage_limits={"api_calls": 100000, "storage": 100},
                priority_support=True,
                api_rate_limit=1000,
                storage_limit_gb=100,
                custom_branding=True,
                analytics_retention_days=365
            )
        }

    def _initialize_subscription_features(self) -> None:
        """Initialize subscription features."""
        self.subscription_features = {
            "basic_tracking": SubscriptionFeature(
                feature_id="basic_tracking",
                name="Basic Nutrition Tracking",
                description="Track calories, macros, and basic nutrients",
                included_in_tiers=[SubscriptionTier.FREE, SubscriptionTier.BASIC, 
                                 SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE],
                usage_limits={
                    SubscriptionTier.FREE: 50,
                    SubscriptionTier.BASIC: 500,
                    SubscriptionTier.PREMIUM: None,
                    SubscriptionTier.ENTERPRISE: None
                }
            ),
            "meal_planning": SubscriptionFeature(
                feature_id="meal_planning",
                name="AI Meal Planning",
                description="Personalized meal plans with shopping lists",
                included_in_tiers=[SubscriptionTier.BASIC, SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE],
                usage_limits={
                    SubscriptionTier.BASIC: 10,
                    SubscriptionTier.PREMIUM: 50,
                    SubscriptionTier.ENTERPRISE: None
                },
                is_premium=True
            ),
            "ai_recommendations": SubscriptionFeature(
                feature_id="ai_recommendations",
                name="AI Nutrition Recommendations",
                description="Personalized nutrition advice powered by AI",
                included_in_tiers=[SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE],
                usage_limits={
                    SubscriptionTier.PREMIUM: 100,
                    SubscriptionTier.ENTERPRISE: None
                },
                is_premium=True
            )
        }
