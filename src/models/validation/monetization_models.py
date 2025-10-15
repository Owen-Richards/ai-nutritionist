"""Comprehensive Pydantic models for monetization and analytics services."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .user_models import BaseValidationModel, APIBaseModel


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class BillingInterval(str, Enum):
    """Billing interval options."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    """Subscription status options."""
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    INCOMPLETE = "incomplete"


class PaymentStatus(str, Enum):
    """Payment status options."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    BANK_TRANSFER = "bank_transfer"


class EventType(str, Enum):
    """Analytics event types."""
    USER_REGISTRATION = "user_registration"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PROFILE_UPDATE = "profile_update"
    MEAL_PLAN_GENERATED = "meal_plan_generated"
    MEAL_PLAN_VIEWED = "meal_plan_viewed"
    MEAL_COMPLETED = "meal_completed"
    RECIPE_VIEWED = "recipe_viewed"
    RECIPE_RATED = "recipe_rated"
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    FEATURE_USED = "feature_used"
    ERROR_OCCURRED = "error_occurred"


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"


class Price(BaseValidationModel):
    """Price information with currency support."""
    
    amount: Annotated[Decimal, Field(ge=0, le=100000)] = Field(
        ...,
        description="Price amount"
    )
    currency: Currency = Field(
        default=Currency.USD,
        description="Currency code"
    )
    
    @field_validator('amount')
    @classmethod
    def validate_amount_precision(cls, v: Decimal) -> Decimal:
        """Validate amount has appropriate precision for currency."""
        # Most currencies use 2 decimal places, JPY uses 0
        if v.as_tuple().exponent < -2:
            return v.quantize(Decimal('0.01'))
        return v
    
    def to_cents(self) -> int:
        """Convert to cents/smallest currency unit."""
        if self.currency == Currency.JPY:
            return int(self.amount)
        return int(self.amount * 100)
    
    @classmethod
    def from_cents(cls, cents: int, currency: Currency = Currency.USD) -> 'Price':
        """Create Price from cents/smallest currency unit."""
        if currency == Currency.JPY:
            amount = Decimal(cents)
        else:
            amount = Decimal(cents) / 100
        return cls(amount=amount, currency=currency)


class Subscription(BaseValidationModel):
    """User subscription information."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique subscription identifier")
    user_id: UUID = Field(
        ...,
        description="ID of the subscribed user"
    )
    tier: SubscriptionTier = Field(
        ...,
        description="Subscription tier"
    )
    status: SubscriptionStatus = Field(
        ...,
        description="Current subscription status"
    )
    billing_interval: BillingInterval = Field(
        ...,
        description="Billing frequency"
    )
    price: Price = Field(
        ...,
        description="Subscription price"
    )
    current_period_start: datetime = Field(
        ...,
        description="Start of current billing period"
    )
    current_period_end: datetime = Field(
        ...,
        description="End of current billing period"
    )
    trial_start: Optional[datetime] = Field(
        None,
        description="Trial period start date"
    )
    trial_end: Optional[datetime] = Field(
        None,
        description="Trial period end date"
    )
    cancelled_at: Optional[datetime] = Field(
        None,
        description="Cancellation timestamp"
    )
    cancel_at_period_end: bool = Field(
        default=False,
        description="Whether to cancel at end of current period"
    )
    payment_method_id: Optional[str] = Field(
        None,
        description="ID of the payment method"
    )
    
    @model_validator(mode='after')
    def validate_subscription_periods(self) -> 'Subscription':
        """Validate subscription period consistency."""
        if self.current_period_end <= self.current_period_start:
            raise ValueError("Current period end must be after start")
        
        if self.trial_start and self.trial_end:
            if self.trial_end <= self.trial_start:
                raise ValueError("Trial end must be after trial start")
        
        if self.cancelled_at and self.status not in [SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED]:
            raise ValueError("Cancelled timestamp requires cancelled or expired status")
        
        return self
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
    
    @property
    def is_in_trial(self) -> bool:
        """Check if subscription is in trial period."""
        if not self.trial_start or not self.trial_end:
            return False
        
        now = datetime.utcnow()
        return self.trial_start <= now <= self.trial_end
    
    @property
    def days_until_renewal(self) -> Optional[int]:
        """Calculate days until next renewal."""
        if not self.is_active:
            return None
        
        now = datetime.utcnow()
        if now > self.current_period_end:
            return 0
        
        return (self.current_period_end - now).days


class Payment(BaseValidationModel):
    """Payment transaction record."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique payment identifier")
    subscription_id: Optional[UUID] = Field(
        None,
        description="Associated subscription ID"
    )
    user_id: UUID = Field(
        ...,
        description="ID of the paying user"
    )
    amount: Price = Field(
        ...,
        description="Payment amount"
    )
    status: PaymentStatus = Field(
        ...,
        description="Payment status"
    )
    payment_method: PaymentMethod = Field(
        ...,
        description="Payment method used"
    )
    payment_method_id: Optional[str] = Field(
        None,
        description="External payment method identifier"
    )
    transaction_id: Optional[str] = Field(
        None,
        description="External transaction identifier"
    )
    description: Annotated[str, Field(min_length=1, max_length=500)] = Field(
        ...,
        description="Payment description"
    )
    invoice_id: Optional[str] = Field(
        None,
        description="Associated invoice ID"
    )
    failure_reason: Optional[Annotated[str, Field(max_length=1000)]] = Field(
        None,
        description="Reason for payment failure"
    )
    refunded_amount: Optional[Price] = Field(
        None,
        description="Amount refunded if applicable"
    )
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Payment processing timestamp"
    )
    
    @model_validator(mode='after')
    def validate_payment_consistency(self) -> 'Payment':
        """Validate payment data consistency."""
        if self.status == PaymentStatus.FAILED and not self.failure_reason:
            raise ValueError("Failed payments must have a failure reason")
        
        if self.refunded_amount:
            if self.status not in [PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED]:
                raise ValueError("Refunded amount requires refunded status")
            
            if self.refunded_amount.currency != self.amount.currency:
                raise ValueError("Refunded amount currency must match payment currency")
            
            if self.refunded_amount.amount > self.amount.amount:
                raise ValueError("Refunded amount cannot exceed payment amount")
        
        return self


class UsageMetrics(BaseValidationModel):
    """Usage tracking for subscription limits."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique metrics identifier")
    user_id: UUID = Field(
        ...,
        description="ID of the user"
    )
    subscription_id: Optional[UUID] = Field(
        None,
        description="Associated subscription ID"
    )
    period_start: date = Field(
        ...,
        description="Start of measurement period"
    )
    period_end: date = Field(
        ...,
        description="End of measurement period"
    )
    meal_plans_generated: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="Number of meal plans generated"
    )
    recipes_accessed: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="Number of recipes accessed"
    )
    ai_consultations: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="Number of AI nutrition consultations"
    )
    grocery_lists_generated: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="Number of grocery lists generated"
    )
    export_operations: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="Number of export operations"
    )
    api_calls: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="Number of API calls made"
    )
    storage_used_mb: Annotated[float, Field(ge=0)] = Field(
        default=0.0,
        description="Storage used in megabytes"
    )
    
    @model_validator(mode='after')
    def validate_period(self) -> 'UsageMetrics':
        """Validate measurement period."""
        if self.period_end <= self.period_start:
            raise ValueError("Period end must be after period start")
        
        if (self.period_end - self.period_start).days > 367:  # Allow leap year
            raise ValueError("Measurement period cannot exceed 1 year")
        
        return self


class AnalyticsEvent(BaseValidationModel):
    """Analytics event for tracking user behavior."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    user_id: Optional[UUID] = Field(
        None,
        description="ID of the user (null for anonymous events)"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session identifier"
    )
    event_type: EventType = Field(
        ...,
        description="Type of event"
    )
    event_name: Annotated[str, Field(min_length=1, max_length=100)] = Field(
        ...,
        description="Specific event name"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event properties and metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp"
    )
    ip_address: Optional[Annotated[str, Field(max_length=45)]] = Field(
        None,
        description="User IP address"
    )
    user_agent: Optional[Annotated[str, Field(max_length=1000)]] = Field(
        None,
        description="User agent string"
    )
    platform: Optional[Annotated[str, Field(max_length=50)]] = Field(
        None,
        description="Platform (web, ios, android, etc.)"
    )
    app_version: Optional[Annotated[str, Field(max_length=20)]] = Field(
        None,
        description="Application version"
    )
    referrer: Optional[Annotated[str, Field(max_length=500)]] = Field(
        None,
        description="Referrer URL"
    )
    
    @field_validator('properties')
    @classmethod
    def validate_properties_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate event properties don't exceed size limits."""
        import json
        
        try:
            serialized = json.dumps(v)
            if len(serialized) > 10000:  # 10KB limit
                raise ValueError("Event properties cannot exceed 10KB when serialized")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Event properties must be JSON serializable: {e}")
        
        return v
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate IP address format."""
        if v is None:
            return v
        
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


# API Request/Response Models

class SubscriptionCreateRequest(APIBaseModel):
    """Request model for creating a subscription."""
    
    tier: SubscriptionTier = Field(
        ...,
        description="Subscription tier to create"
    )
    billing_interval: BillingInterval = Field(
        default=BillingInterval.MONTHLY,
        description="Billing frequency"
    )
    payment_method_id: Optional[str] = Field(
        None,
        description="Payment method ID for billing"
    )
    coupon_code: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        None,
        description="Coupon code for discounts"
    )
    trial_days: Optional[Annotated[int, Field(gt=0, le=365)]] = Field(
        None,
        description="Trial period in days"
    )


class SubscriptionUpdateRequest(APIBaseModel):
    """Request model for updating a subscription."""
    
    tier: Optional[SubscriptionTier] = None
    billing_interval: Optional[BillingInterval] = None
    payment_method_id: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None


class PaymentCreateRequest(APIBaseModel):
    """Request model for creating a payment."""
    
    amount: Price = Field(
        ...,
        description="Payment amount"
    )
    payment_method_id: str = Field(
        ...,
        description="Payment method to use"
    )
    description: Annotated[str, Field(min_length=1, max_length=500)] = Field(
        ...,
        description="Payment description"
    )
    subscription_id: Optional[UUID] = Field(
        None,
        description="Associated subscription ID"
    )


class AnalyticsEventRequest(APIBaseModel):
    """Request model for tracking analytics events."""
    
    event_type: EventType = Field(
        ...,
        description="Type of event"
    )
    event_name: Annotated[str, Field(min_length=1, max_length=100)] = Field(
        ...,
        description="Specific event name"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event properties"
    )
    user_id: Optional[UUID] = Field(
        None,
        description="User ID (if applicable)"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session identifier"
    )


class UsageReportRequest(APIBaseModel):
    """Request model for usage reports."""
    
    user_id: Optional[UUID] = Field(
        None,
        description="User ID for user-specific report"
    )
    start_date: date = Field(
        ...,
        description="Report start date"
    )
    end_date: date = Field(
        ...,
        description="Report end date"
    )
    metrics: List[str] = Field(
        default_factory=lambda: ["meal_plans_generated", "recipes_accessed"],
        description="Metrics to include in report"
    )
    
    @model_validator(mode='after')
    def validate_date_range(self) -> 'UsageReportRequest':
        """Validate report date range."""
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")
        
        if (self.end_date - self.start_date).days > 365:
            raise ValueError("Report period cannot exceed 1 year")
        
        return self


class SubscriptionResponse(APIBaseModel):
    """Response model for subscription data."""
    
    subscription: Subscription = Field(
        ...,
        description="Subscription information"
    )
    usage_metrics: Optional[UsageMetrics] = Field(
        None,
        description="Current usage metrics"
    )
    limits: Dict[str, int] = Field(
        default_factory=dict,
        description="Usage limits for subscription tier"
    )


class PaymentResponse(APIBaseModel):
    """Response model for payment data."""
    
    payment: Payment = Field(
        ...,
        description="Payment information"
    )
    client_secret: Optional[str] = Field(
        None,
        description="Client secret for payment confirmation"
    )


class UsageReportResponse(APIBaseModel):
    """Response model for usage reports."""
    
    period: Dict[str, date] = Field(
        ...,
        description="Report period"
    )
    user_metrics: Optional[UsageMetrics] = Field(
        None,
        description="User-specific metrics (if requested)"
    )
    aggregated_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated metrics across users"
    )
    trends: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Trending data for metrics"
    )


class AnalyticsReportResponse(APIBaseModel):
    """Response model for analytics reports."""
    
    period: Dict[str, datetime] = Field(
        ...,
        description="Report period"
    )
    event_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of events by type"
    )
    user_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="User behavior metrics"
    )
    funnel_analysis: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Conversion funnel data"
    )
    retention_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="User retention metrics"
    )
