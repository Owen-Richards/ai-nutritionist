"""Stripe billing integration for Track E2.

Handles Stripe customers, subscriptions, webhooks, and entitlement middleware.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import stripe
from fastapi import HTTPException

from ...models.monetization import (
    BillingInterval,
    FeatureFlag,
    MonetizationConfig,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    UsageTracker
)

logger = logging.getLogger(__name__)


class StripeConfig:
    """Stripe configuration and credentials."""
    
    def __init__(self):
        # In production, load from environment variables
        self.secret_key = "sk_test_..."  # Stripe secret key
        self.publishable_key = "pk_test_..."  # Stripe publishable key
        self.webhook_secret = "whsec_..."  # Webhook endpoint secret
        
        # Price IDs for each tier/interval combination
        self.price_ids = {
            (SubscriptionTier.PLUS, BillingInterval.MONTHLY): "price_plus_monthly",
            (SubscriptionTier.PLUS, BillingInterval.YEARLY): "price_plus_yearly",
            (SubscriptionTier.PRO, BillingInterval.MONTHLY): "price_pro_monthly",
            (SubscriptionTier.PRO, BillingInterval.YEARLY): "price_pro_yearly"
        }
        
        # Initialize Stripe
        stripe.api_key = self.secret_key


class StripeCustomerService:
    """Manages Stripe customer lifecycle."""
    
    def __init__(self, config: StripeConfig):
        self.config = config
    
    async def create_customer(self, user_id: UUID, email: str, 
                            name: Optional[str] = None,
                            metadata: Optional[Dict] = None) -> stripe.Customer:
        """Create a new Stripe customer."""
        try:
            customer_metadata = {"user_id": str(user_id)}
            if metadata:
                customer_metadata.update(metadata)
            
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create customer")
    
    async def get_customer(self, customer_id: str) -> Optional[stripe.Customer]:
        """Get Stripe customer by ID."""
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve customer {customer_id}: {e}")
            return None
    
    async def update_customer(self, customer_id: str, 
                            email: Optional[str] = None,
                            name: Optional[str] = None,
                            metadata: Optional[Dict] = None) -> stripe.Customer:
        """Update Stripe customer information."""
        try:
            update_data = {}
            if email:
                update_data["email"] = email
            if name:
                update_data["name"] = name
            if metadata:
                update_data["metadata"] = metadata
            
            return stripe.Customer.modify(customer_id, **update_data)
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update customer {customer_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update customer")
    
    async def delete_customer(self, customer_id: str) -> None:
        """Delete Stripe customer (for GDPR compliance)."""
        try:
            stripe.Customer.delete(customer_id)
            logger.info(f"Deleted Stripe customer {customer_id}")
        except stripe.error.StripeError as e:
            logger.error(f"Failed to delete customer {customer_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete customer")


class StripeSubscriptionService:
    """Manages Stripe subscription lifecycle."""
    
    def __init__(self, config: StripeConfig):
        self.config = config
    
    async def create_subscription(self, customer_id: str, user_id: UUID,
                                tier: SubscriptionTier, interval: BillingInterval,
                                trial_days: Optional[int] = None,
                                coupon: Optional[str] = None) -> stripe.Subscription:
        """Create a new Stripe subscription."""
        try:
            price_id = self.config.price_ids.get((tier, interval))
            if not price_id:
                raise ValueError(f"No price ID configured for {tier} {interval}")
            
            subscription_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": {
                    "user_id": str(user_id),
                    "tier": tier.value,
                    "interval": interval.value
                },
                "payment_behavior": "default_incomplete",
                "payment_settings": {"save_default_payment_method": "on_subscription"},
                "expand": ["latest_invoice.payment_intent"]
            }
            
            if trial_days and trial_days > 0:
                subscription_data["trial_period_days"] = trial_days
            
            if coupon:
                subscription_data["coupon"] = coupon
            
            subscription = stripe.Subscription.create(**subscription_data)
            
            logger.info(f"Created Stripe subscription {subscription.id} for user {user_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create subscription")
    
    async def update_subscription(self, subscription_id: str,
                                new_tier: Optional[SubscriptionTier] = None,
                                new_interval: Optional[BillingInterval] = None,
                                prorate: bool = True) -> stripe.Subscription:
        """Update an existing subscription (upgrade/downgrade)."""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            if new_tier and new_interval:
                price_id = self.config.price_ids.get((new_tier, new_interval))
                if not price_id:
                    raise ValueError(f"No price ID configured for {new_tier} {new_interval}")
                
                # Update subscription item
                stripe.Subscription.modify(
                    subscription_id,
                    items=[{
                        "id": subscription["items"]["data"][0]["id"],
                        "price": price_id,
                    }],
                    proration_behavior="create_prorations" if prorate else "none",
                    metadata={
                        **subscription.metadata,
                        "tier": new_tier.value,
                        "interval": new_interval.value
                    }
                )
            
            return stripe.Subscription.retrieve(subscription_id)
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription {subscription_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update subscription")
    
    async def cancel_subscription(self, subscription_id: str,
                                at_period_end: bool = True) -> stripe.Subscription:
        """Cancel a subscription."""
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Canceled subscription {subscription_id} (at_period_end={at_period_end})")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to cancel subscription")
    
    async def reactivate_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Reactivate a canceled subscription."""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False
            )
            
            logger.info(f"Reactivated subscription {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to reactivate subscription {subscription_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to reactivate subscription")


class StripeWebhookHandler:
    """Handles Stripe webhook events."""
    
    def __init__(self, config: StripeConfig, billing_service: BillingService):
        self.config = config
        self.billing_service = billing_service
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature for security."""
        try:
            stripe.Webhook.construct_event(
                payload, signature, self.config.webhook_secret
            )
            return True
        except ValueError:
            logger.error("Invalid webhook payload")
            return False
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            return False
    
    async def handle_webhook(self, event_type: str, event_data: Dict) -> None:
        """Route webhook events to appropriate handlers."""
        handlers = {
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "customer.subscription.trial_will_end": self._handle_trial_will_end,
            "invoice.payment_succeeded": self._handle_payment_succeeded,
            "invoice.payment_failed": self._handle_payment_failed,
            "customer.created": self._handle_customer_created,
            "customer.updated": self._handle_customer_updated,
            "customer.deleted": self._handle_customer_deleted
        }
        
        handler = handlers.get(event_type)
        if handler:
            try:
                await handler(event_data)
                logger.info(f"Successfully handled webhook event: {event_type}")
            except Exception as e:
                logger.error(f"Failed to handle webhook event {event_type}: {e}")
                raise
        else:
            logger.warning(f"Unhandled webhook event type: {event_type}")
    
    async def _handle_subscription_created(self, data: Dict) -> None:
        """Handle subscription creation."""
        stripe_subscription = data["object"]
        user_id = UUID(stripe_subscription["metadata"]["user_id"])
        
        await self.billing_service.sync_subscription_from_stripe(
            user_id, stripe_subscription["id"]
        )
    
    async def _handle_subscription_updated(self, data: Dict) -> None:
        """Handle subscription updates."""
        stripe_subscription = data["object"]
        user_id = UUID(stripe_subscription["metadata"]["user_id"])
        
        await self.billing_service.sync_subscription_from_stripe(
            user_id, stripe_subscription["id"]
        )
    
    async def _handle_subscription_deleted(self, data: Dict) -> None:
        """Handle subscription cancellation."""
        stripe_subscription = data["object"]
        user_id = UUID(stripe_subscription["metadata"]["user_id"])
        
        await self.billing_service.handle_subscription_cancellation(
            user_id, stripe_subscription["id"]
        )
    
    async def _handle_trial_will_end(self, data: Dict) -> None:
        """Handle trial ending soon."""
        stripe_subscription = data["object"]
        user_id = UUID(stripe_subscription["metadata"]["user_id"])
        
        # Send trial ending notification
        await self.billing_service.send_trial_ending_notification(user_id)
    
    async def _handle_payment_succeeded(self, data: Dict) -> None:
        """Handle successful payment."""
        invoice = data["object"]
        subscription_id = invoice.get("subscription")
        
        if subscription_id:
            await self.billing_service.handle_successful_payment(subscription_id)
    
    async def _handle_payment_failed(self, data: Dict) -> None:
        """Handle failed payment."""
        invoice = data["object"]
        subscription_id = invoice.get("subscription")
        
        if subscription_id:
            await self.billing_service.handle_failed_payment(subscription_id)
    
    async def _handle_customer_created(self, data: Dict) -> None:
        """Handle customer creation."""
        customer = data["object"]
        logger.info(f"Stripe customer created: {customer['id']}")
    
    async def _handle_customer_updated(self, data: Dict) -> None:
        """Handle customer updates."""
        customer = data["object"]
        logger.info(f"Stripe customer updated: {customer['id']}")
    
    async def _handle_customer_deleted(self, data: Dict) -> None:
        """Handle customer deletion."""
        customer = data["object"]
        logger.info(f"Stripe customer deleted: {customer['id']}")


class BillingService:
    """Main billing service orchestrating Stripe operations."""
    
    def __init__(self):
        self.config = StripeConfig()
        self.customer_service = StripeCustomerService(self.config)
        self.subscription_service = StripeSubscriptionService(self.config)
        self.webhook_handler = StripeWebhookHandler(self.config, self)
        self.monetization_config = MonetizationConfig()
        
        # In-memory storage for demo (use database in production)
        self.subscriptions: Dict[UUID, Subscription] = {}
        self.usage_trackers: Dict[UUID, UsageTracker] = {}
    
    async def create_customer_and_subscription(
        self, user_id: UUID, email: str, name: Optional[str],
        tier: SubscriptionTier, interval: BillingInterval,
        payment_method_id: Optional[str] = None,
        trial_days: Optional[int] = None,
        coupon: Optional[str] = None
    ) -> Tuple[stripe.Customer, stripe.Subscription]:
        """Create customer and subscription in one operation."""
        
        # Create Stripe customer
        customer = await self.customer_service.create_customer(
            user_id, email, name, {"subscription_tier": tier.value}
        )
        
        # Attach payment method if provided
        if payment_method_id:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": payment_method_id}
            )
        
        # Get trial days from config if not specified
        if trial_days is None:
            pricing_config = self.monetization_config.get_pricing_config(tier)
            trial_days = pricing_config.trial_days
        
        # Create subscription
        subscription = await self.subscription_service.create_subscription(
            customer.id, user_id, tier, interval, trial_days, coupon
        )
        
        # Create local subscription record
        await self.sync_subscription_from_stripe(user_id, subscription.id)
        
        return customer, subscription
    
    async def sync_subscription_from_stripe(self, user_id: UUID, 
                                          stripe_subscription_id: str) -> Subscription:
        """Sync subscription data from Stripe to local storage."""
        try:
            stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
            
            # Map Stripe status to our status
            status_mapping = {
                "active": SubscriptionStatus.ACTIVE,
                "trialing": SubscriptionStatus.TRIALING,
                "past_due": SubscriptionStatus.PAST_DUE,
                "canceled": SubscriptionStatus.CANCELED,
                "unpaid": SubscriptionStatus.UNPAID,
                "incomplete": SubscriptionStatus.INCOMPLETE,
                "incomplete_expired": SubscriptionStatus.INCOMPLETE_EXPIRED,
                "paused": SubscriptionStatus.PAUSED
            }
            
            # Extract subscription details
            tier = SubscriptionTier(stripe_sub.metadata.get("tier", "free"))
            interval = BillingInterval(stripe_sub.metadata.get("interval", "monthly"))
            status = status_mapping.get(stripe_sub.status, SubscriptionStatus.INCOMPLETE)
            
            # Get price information
            price_item = stripe_sub["items"]["data"][0]
            price_cents = price_item["price"]["unit_amount"]
            currency = price_item["price"]["currency"].upper()
            
            # Create or update local subscription
            subscription = Subscription(
                user_id=user_id,
                tier=tier,
                status=status,
                billing_interval=interval,
                stripe_customer_id=stripe_sub.customer,
                stripe_subscription_id=stripe_sub.id,
                stripe_price_id=price_item["price"]["id"],
                price_cents=price_cents,
                currency=currency,
                started_at=datetime.fromtimestamp(stripe_sub.created) if stripe_sub.created else None,
                trial_start=datetime.fromtimestamp(stripe_sub.trial_start) if stripe_sub.trial_start else None,
                trial_end=datetime.fromtimestamp(stripe_sub.trial_end) if stripe_sub.trial_end else None,
                current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start) if stripe_sub.current_period_start else None,
                current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end) if stripe_sub.current_period_end else None,
                canceled_at=datetime.fromtimestamp(stripe_sub.canceled_at) if stripe_sub.canceled_at else None,
                ended_at=datetime.fromtimestamp(stripe_sub.ended_at) if stripe_sub.ended_at else None
            )
            
            # Store subscription
            self.subscriptions[user_id] = subscription
            
            # Initialize usage tracker if not exists
            if user_id not in self.usage_trackers:
                self.usage_trackers[user_id] = UsageTracker(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    period_start=subscription.current_period_start or datetime.now(),
                    period_end=subscription.current_period_end or datetime.now() + timedelta(days=30)
                )
            
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to sync subscription from Stripe: {e}")
            raise HTTPException(status_code=500, detail="Failed to sync subscription")
    
    async def upgrade_subscription(self, user_id: UUID, new_tier: SubscriptionTier,
                                 new_interval: Optional[BillingInterval] = None) -> Subscription:
        """Upgrade user's subscription to a higher tier."""
        subscription = self.subscriptions.get(user_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        if not subscription.stripe_subscription_id:
            raise HTTPException(status_code=400, detail="Invalid subscription state")
        
        # Use current interval if not specified
        if new_interval is None:
            new_interval = subscription.billing_interval
        
        # Update Stripe subscription
        await self.subscription_service.update_subscription(
            subscription.stripe_subscription_id, new_tier, new_interval
        )
        
        # Sync back from Stripe
        return await self.sync_subscription_from_stripe(user_id, subscription.stripe_subscription_id)
    
    async def cancel_subscription(self, user_id: UUID, at_period_end: bool = True) -> Subscription:
        """Cancel user's subscription."""
        subscription = self.subscriptions.get(user_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        if not subscription.stripe_subscription_id:
            raise HTTPException(status_code=400, detail="Invalid subscription state")
        
        # Cancel in Stripe
        await self.subscription_service.cancel_subscription(
            subscription.stripe_subscription_id, at_period_end
        )
        
        # Sync back from Stripe
        return await self.sync_subscription_from_stripe(user_id, subscription.stripe_subscription_id)
    
    def get_subscription(self, user_id: UUID) -> Optional[Subscription]:
        """Get user's current subscription."""
        return self.subscriptions.get(user_id)
    
    def get_usage_tracker(self, user_id: UUID) -> Optional[UsageTracker]:
        """Get user's usage tracker."""
        return self.usage_trackers.get(user_id)
    
    async def handle_subscription_cancellation(self, user_id: UUID, 
                                             stripe_subscription_id: str) -> None:
        """Handle subscription cancellation from webhook."""
        await self.sync_subscription_from_stripe(user_id, stripe_subscription_id)
        logger.info(f"Handled subscription cancellation for user {user_id}")
    
    async def send_trial_ending_notification(self, user_id: UUID) -> None:
        """Send notification that trial is ending soon."""
        # Implementation would send SMS/email notification
        logger.info(f"Sending trial ending notification to user {user_id}")
    
    async def handle_successful_payment(self, stripe_subscription_id: str) -> None:
        """Handle successful payment from webhook."""
        # Find subscription by Stripe ID
        for user_id, subscription in self.subscriptions.items():
            if subscription.stripe_subscription_id == stripe_subscription_id:
                await self.sync_subscription_from_stripe(user_id, stripe_subscription_id)
                
                # Reset usage tracker for new period
                if user_id in self.usage_trackers:
                    tracker = self.usage_trackers[user_id]
                    new_period_start = subscription.current_period_start or datetime.now()
                    new_period_end = subscription.current_period_end or new_period_start + timedelta(days=30)
                    
                    self.usage_trackers[user_id] = tracker.reset_for_new_period(
                        new_period_start, new_period_end
                    )
                
                logger.info(f"Handled successful payment for subscription {stripe_subscription_id}")
                break
    
    async def handle_failed_payment(self, stripe_subscription_id: str) -> None:
        """Handle failed payment from webhook."""
        # Find subscription and sync status
        for user_id, subscription in self.subscriptions.items():
            if subscription.stripe_subscription_id == stripe_subscription_id:
                await self.sync_subscription_from_stripe(user_id, stripe_subscription_id)
                # Send payment failure notification
                logger.warning(f"Handled failed payment for subscription {stripe_subscription_id}")
                break


# Export main classes
__all__ = [
    "StripeConfig",
    "StripeCustomerService",
    "StripeSubscriptionService", 
    "StripeWebhookHandler",
    "BillingService"
]
