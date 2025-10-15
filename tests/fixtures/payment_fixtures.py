"""Payment and subscription test fixtures"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4, UUID
from decimal import Decimal
import random

# Import with fallbacks
try:
    from src.models.monetization import (
        Subscription, SubscriptionTier, SubscriptionStatus, BillingInterval,
        PaymentMethod, PaymentStatus, Invoice, InvoiceStatus, UsageTracker
    )
except ImportError:
    # Create fallback classes
    class SubscriptionTier:
        FREE = "free"
        PREMIUM = "premium"
        FAMILY = "family"
        ENTERPRISE = "enterprise"
    
    class SubscriptionStatus:
        ACTIVE = "active"
        TRIALING = "trialing"
        CANCELED = "canceled"
        PAST_DUE = "past_due"
        UNPAID = "unpaid"
    
    class BillingInterval:
        MONTHLY = "monthly"
        YEARLY = "yearly"
    
    class PaymentStatus:
        SUCCEEDED = "succeeded"
        FAILED = "failed"
        PENDING = "pending"
    
    class InvoiceStatus:
        PAID = "paid"
        OPEN = "open"
        PAYMENT_FAILED = "payment_failed"
        DRAFT = "draft"
    
    class Subscription:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class PaymentMethod:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class Invoice:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class UsageTracker:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)


class PaymentMethodFactory:
    """Factory for creating payment methods"""
    
    @staticmethod
    def create_credit_card(
        user_id: UUID = None,
        last_four: str = "4242",
        brand: str = "visa",
        exp_month: int = 12,
        exp_year: int = 2025
    ) -> PaymentMethod:
        if user_id is None:
            user_id = uuid4()
        
        return PaymentMethod(
            id=uuid4(),
            user_id=user_id,
            stripe_payment_method_id=f"pm_{random.randint(100000, 999999)}",
            type="card",
            card_brand=brand,
            card_last_four=last_four,
            card_exp_month=exp_month,
            card_exp_year=exp_year,
            is_default=True,
            created_at=datetime.now() - timedelta(days=random.randint(1, 365)),
            updated_at=datetime.now()
        )
    
    @staticmethod
    def create_paypal(user_id: UUID = None) -> PaymentMethod:
        if user_id is None:
            user_id = uuid4()
        
        return PaymentMethod(
            id=uuid4(),
            user_id=user_id,
            stripe_payment_method_id=f"pm_paypal_{random.randint(100000, 999999)}",
            type="paypal",
            paypal_email="user@example.com",
            is_default=False,
            created_at=datetime.now() - timedelta(days=random.randint(1, 365)),
            updated_at=datetime.now()
        )


class SubscriptionFactory:
    """Factory for creating subscriptions"""
    
    @staticmethod
    def create(
        user_id: UUID = None,
        tier: SubscriptionTier = SubscriptionTier.PREMIUM,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        billing_interval: BillingInterval = BillingInterval.MONTHLY
    ) -> Subscription:
        if user_id is None:
            user_id = uuid4()
        
        now = datetime.now()
        
        # Set prices based on tier and interval
        price_mapping = {
            (SubscriptionTier.PREMIUM, BillingInterval.MONTHLY): 999,  # $9.99
            (SubscriptionTier.PREMIUM, BillingInterval.YEARLY): 9999,  # $99.99
            (SubscriptionTier.FAMILY, BillingInterval.MONTHLY): 1499,  # $14.99
            (SubscriptionTier.FAMILY, BillingInterval.YEARLY): 14999,  # $149.99
        }
        
        price_cents = price_mapping.get((tier, billing_interval), 999)
        
        subscription = Subscription(
            id=uuid4(),
            user_id=user_id,
            tier=tier,
            status=status,
            billing_interval=billing_interval,
            created_at=now - timedelta(days=random.randint(1, 365)),
            started_at=now - timedelta(days=random.randint(1, 30)),
            current_period_start=now - timedelta(days=random.randint(1, 30)),
            current_period_end=now + timedelta(days=30 if billing_interval == BillingInterval.MONTHLY else 365),
            stripe_customer_id=f"cus_{random.randint(100000, 999999)}",
            stripe_subscription_id=f"sub_{random.randint(100000, 999999)}",
            stripe_price_id=f"price_{random.randint(100000, 999999)}",
            price_cents=price_cents,
            currency="USD"
        )
        
        return subscription
    
    @staticmethod
    def active_premium(user_id: UUID = None) -> Subscription:
        return SubscriptionFactory.create(
            user_id=user_id,
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY
        )
    
    @staticmethod
    def trialing_subscription(user_id: UUID = None) -> Subscription:
        subscription = SubscriptionFactory.create(
            user_id=user_id,
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.TRIALING,
            billing_interval=BillingInterval.MONTHLY
        )
        
        # Set trial dates
        subscription.trial_start = datetime.now() - timedelta(days=3)
        subscription.trial_end = datetime.now() + timedelta(days=11)  # 14-day trial
        subscription.trial_used = True
        subscription.trial_days_remaining = 11
        
        return subscription
    
    @staticmethod
    def canceled_subscription(user_id: UUID = None) -> Subscription:
        subscription = SubscriptionFactory.create(
            user_id=user_id,
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.CANCELED,
            billing_interval=BillingInterval.MONTHLY
        )
        
        subscription.canceled_at = datetime.now() - timedelta(days=5)
        subscription.cancel_at_period_end = True
        
        return subscription
    
    @staticmethod
    def family_subscription(user_id: UUID = None) -> Subscription:
        return SubscriptionFactory.create(
            user_id=user_id,
            tier=SubscriptionTier.FAMILY,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.YEARLY
        )


class InvoiceFactory:
    """Factory for creating invoices"""
    
    @staticmethod
    def create(
        user_id: UUID = None,
        subscription_id: UUID = None,
        amount_cents: int = 999,
        status: InvoiceStatus = InvoiceStatus.PAID
    ) -> Invoice:
        if user_id is None:
            user_id = uuid4()
        if subscription_id is None:
            subscription_id = uuid4()
        
        now = datetime.now()
        
        return Invoice(
            id=uuid4(),
            user_id=user_id,
            subscription_id=subscription_id,
            stripe_invoice_id=f"in_{random.randint(100000, 999999)}",
            amount_cents=amount_cents,
            tax_cents=int(amount_cents * 0.08),  # 8% tax
            currency="USD",
            status=status,
            billing_reason="subscription_cycle",
            created_at=now - timedelta(days=random.randint(1, 30)),
            due_date=now + timedelta(days=30),
            paid_at=now if status == InvoiceStatus.PAID else None,
            period_start=now - timedelta(days=30),
            period_end=now,
            metadata={
                "subscription_tier": "premium",
                "billing_interval": "monthly"
            }
        )
    
    @staticmethod
    def paid_invoice(user_id: UUID = None, subscription_id: UUID = None) -> Invoice:
        return InvoiceFactory.create(
            user_id=user_id,
            subscription_id=subscription_id,
            status=InvoiceStatus.PAID
        )
    
    @staticmethod
    def pending_invoice(user_id: UUID = None, subscription_id: UUID = None) -> Invoice:
        invoice = InvoiceFactory.create(
            user_id=user_id,
            subscription_id=subscription_id,
            status=InvoiceStatus.OPEN
        )
        invoice.paid_at = None
        return invoice
    
    @staticmethod
    def failed_invoice(user_id: UUID = None, subscription_id: UUID = None) -> Invoice:
        invoice = InvoiceFactory.create(
            user_id=user_id,
            subscription_id=subscription_id,
            status=InvoiceStatus.PAYMENT_FAILED,
            amount_cents=1499
        )
        invoice.paid_at = None
        invoice.last_payment_attempt = datetime.now() - timedelta(days=1)
        return invoice


class UsageTrackerFactory:
    """Factory for creating usage trackers"""
    
    @staticmethod
    def create(
        user_id: UUID = None,
        subscription_id: UUID = None,
        period_start: datetime = None,
        period_end: datetime = None
    ) -> UsageTracker:
        if user_id is None:
            user_id = uuid4()
        if subscription_id is None:
            subscription_id = uuid4()
        if period_start is None:
            period_start = datetime.now().replace(day=1)  # Start of current month
        if period_end is None:
            # End of current month
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        
        return UsageTracker(
            user_id=user_id,
            subscription_id=subscription_id,
            period_start=period_start,
            period_end=period_end,
            meal_plans_created=random.randint(0, 20),
            sms_sent=random.randint(0, 100),
            widget_views=random.randint(0, 500),
            crew_interactions=random.randint(0, 50),
            calendar_events_created=random.randint(0, 30),
            grocery_exports=random.randint(0, 15),
            last_updated=datetime.now()
        )
    
    @staticmethod
    def heavy_usage(user_id: UUID = None, subscription_id: UUID = None) -> UsageTracker:
        tracker = UsageTrackerFactory.create(user_id, subscription_id)
        tracker.meal_plans_created = 25
        tracker.sms_sent = 150
        tracker.widget_views = 800
        tracker.crew_interactions = 75
        tracker.calendar_events_created = 40
        tracker.grocery_exports = 25
        return tracker
    
    @staticmethod
    def light_usage(user_id: UUID = None, subscription_id: UUID = None) -> UsageTracker:
        tracker = UsageTrackerFactory.create(user_id, subscription_id)
        tracker.meal_plans_created = 3
        tracker.sms_sent = 10
        tracker.widget_views = 50
        tracker.crew_interactions = 5
        tracker.calendar_events_created = 2
        tracker.grocery_exports = 1
        return tracker


# Pytest fixtures
@pytest.fixture
def payment_method_factory():
    """Factory fixture for creating payment methods"""
    return PaymentMethodFactory


@pytest.fixture
def subscription_factory():
    """Factory fixture for creating subscriptions"""
    return SubscriptionFactory


@pytest.fixture
def invoice_factory():
    """Factory fixture for creating invoices"""
    return InvoiceFactory


@pytest.fixture
def usage_tracker_factory():
    """Factory fixture for creating usage trackers"""
    return UsageTrackerFactory


@pytest.fixture
def create_payment_method():
    """Create a basic credit card payment method"""
    return PaymentMethodFactory.create_credit_card()


@pytest.fixture
def create_subscription():
    """Create a basic active subscription"""
    return SubscriptionFactory.active_premium()


@pytest.fixture
def create_invoice():
    """Create a basic paid invoice"""
    return InvoiceFactory.paid_invoice()


@pytest.fixture
def subscription_scenarios():
    """Collection of different subscription scenarios"""
    user_id = uuid4()
    return {
        'active_premium': SubscriptionFactory.active_premium(user_id),
        'trialing': SubscriptionFactory.trialing_subscription(user_id),
        'canceled': SubscriptionFactory.canceled_subscription(user_id),
        'family': SubscriptionFactory.family_subscription(user_id)
    }


@pytest.fixture
def payment_methods_collection():
    """Collection of different payment methods"""
    user_id = uuid4()
    return {
        'visa': PaymentMethodFactory.create_credit_card(user_id, "4242", "visa"),
        'mastercard': PaymentMethodFactory.create_credit_card(user_id, "5555", "mastercard"),
        'amex': PaymentMethodFactory.create_credit_card(user_id, "3782", "amex"),
        'paypal': PaymentMethodFactory.create_paypal(user_id)
    }


@pytest.fixture
def invoice_scenarios():
    """Collection of different invoice scenarios"""
    user_id = uuid4()
    subscription_id = uuid4()
    return {
        'paid': InvoiceFactory.paid_invoice(user_id, subscription_id),
        'pending': InvoiceFactory.pending_invoice(user_id, subscription_id),
        'failed': InvoiceFactory.failed_invoice(user_id, subscription_id)
    }


@pytest.fixture
def billing_history():
    """Generate billing history for a user"""
    user_id = uuid4()
    subscription_id = uuid4()
    
    invoices = []
    for i in range(6):  # 6 months of history
        invoice_date = datetime.now() - timedelta(days=30 * i)
        invoice = InvoiceFactory.create(
            user_id=user_id,
            subscription_id=subscription_id,
            status=InvoiceStatus.PAID
        )
        invoice.created_at = invoice_date
        invoice.paid_at = invoice_date + timedelta(days=1)
        invoices.append(invoice)
    
    return invoices


@pytest.fixture
def usage_analytics():
    """Generate usage analytics data"""
    user_id = uuid4()
    subscription_id = uuid4()
    
    # Generate 3 months of usage data
    usage_data = []
    for i in range(3):
        month_start = datetime.now().replace(day=1) - timedelta(days=30 * i)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        
        usage = UsageTrackerFactory.create(
            user_id=user_id,
            subscription_id=subscription_id,
            period_start=month_start,
            period_end=month_end
        )
        usage_data.append(usage)
    
    return usage_data


@pytest.fixture
def complete_billing_profile():
    """Complete billing profile with subscription, payment methods, and invoices"""
    user_id = uuid4()
    
    # Create subscription
    subscription = SubscriptionFactory.active_premium(user_id)
    
    # Create payment methods
    payment_methods = [
        PaymentMethodFactory.create_credit_card(user_id),
        PaymentMethodFactory.create_paypal(user_id)
    ]
    
    # Create invoices
    invoices = []
    for i in range(3):
        invoice = InvoiceFactory.paid_invoice(user_id, subscription.id)
        invoice.created_at = datetime.now() - timedelta(days=30 * i)
        invoices.append(invoice)
    
    # Create usage tracker
    usage_tracker = UsageTrackerFactory.create(user_id, subscription.id)
    
    return {
        'user_id': user_id,
        'subscription': subscription,
        'payment_methods': payment_methods,
        'invoices': invoices,
        'usage_tracker': usage_tracker
    }
