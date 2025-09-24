"""API routes for Track E - Monetization.

Handles subscription management, billing, paywall configuration, and experiments.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ...models.monetization import (
    BillingInterval,
    SubscriptionStatus,
    SubscriptionTier
)
from ...services.monetization.billing_service import BillingService
from ...services.monetization.entitlement_service import (
    EntitlementService,
    create_entitlement_middleware
)
from ...services.monetization.paywall_service import (
    PaywallService,
    PaywallTrigger
)
from ...services.monetization.experiment_service import (
    ExperimentService,
    ExperimentType
)

logger = logging.getLogger(__name__)

# Create router
monetization_router = APIRouter(prefix="/v1", tags=["monetization"])

# Initialize services
billing_service = BillingService()
entitlement_service = EntitlementService(billing_service)
paywall_service = PaywallService()
experiment_service = ExperimentService()
entitlement_middleware = create_entitlement_middleware(billing_service)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SubscriptionCreateRequest(BaseModel):
    tier: SubscriptionTier
    interval: BillingInterval = BillingInterval.MONTHLY
    payment_method_id: Optional[str] = None
    coupon_code: Optional[str] = None

class SubscriptionCreateResponse(BaseModel):
    subscription_id: str
    client_secret: Optional[str] = None  # For payment confirmation
    status: SubscriptionStatus
    trial_end: Optional[datetime] = None

class SubscriptionUpdateRequest(BaseModel):
    tier: Optional[SubscriptionTier] = None
    interval: Optional[BillingInterval] = None

class SubscriptionResponse(BaseModel):
    id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    interval: BillingInterval
    price_usd: float
    trial_end: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False

class PaywallConfigRequest(BaseModel):
    trigger: PaywallTrigger
    context: Optional[Dict] = None

class EntitlementCheckResponse(BaseModel):
    has_access: bool
    tier: str
    feature: str
    is_subscription_active: bool
    limit: Optional[int] = None
    usage: int = 0
    remaining: Optional[int] = None
    upgrade_required: bool = False
    trial_eligible: bool = False

class UsageSummaryResponse(BaseModel):
    user_id: str
    tier: str
    billing_period: Optional[Dict] = None
    features: Dict[str, Dict] = Field(default_factory=dict)

class WebhookRequest(BaseModel):
    type: str
    data: Dict


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_current_user_id(request: Request) -> UUID:
    """Extract user ID from request. In production, use proper authentication."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    try:
        return UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

async def get_current_user_email(request: Request) -> str:
    """Extract user email from request."""
    email = request.headers.get("X-User-Email", "user@example.com")
    return email


# ============================================================================
# SUBSCRIPTION MANAGEMENT ROUTES
# ============================================================================

@monetization_router.post("/subscriptions", response_model=SubscriptionCreateResponse)
async def create_subscription(
    request: SubscriptionCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    user_email: str = Depends(get_current_user_email)
):
    """Create a new subscription."""
    try:
        # Check if user already has a subscription
        existing_subscription = billing_service.get_subscription(user_id)
        if existing_subscription and existing_subscription.is_active:
            raise HTTPException(
                status_code=400, 
                detail="User already has an active subscription"
            )
        
        # Create customer and subscription
        customer, stripe_subscription = await billing_service.create_customer_and_subscription(
            user_id=user_id,
            email=user_email,
            name=None,  # Could extract from request
            tier=request.tier,
            interval=request.interval,
            payment_method_id=request.payment_method_id,
            coupon=request.coupon_code
        )
        
        # Get client secret for payment confirmation if needed
        client_secret = None
        if stripe_subscription.status == "incomplete":
            latest_invoice = stripe_subscription.latest_invoice
            if hasattr(latest_invoice, 'payment_intent'):
                client_secret = latest_invoice.payment_intent.client_secret
        
        return SubscriptionCreateResponse(
            subscription_id=stripe_subscription.id,
            client_secret=client_secret,
            status=SubscriptionStatus(stripe_subscription.status),
            trial_end=(
                datetime.fromtimestamp(stripe_subscription.trial_end) 
                if stripe_subscription.trial_end else None
            )
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@monetization_router.get("/subscriptions/current", response_model=SubscriptionResponse)
async def get_current_subscription(user_id: UUID = Depends(get_current_user_id)):
    """Get user's current subscription."""
    subscription = billing_service.get_subscription(user_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    
    return SubscriptionResponse(
        id=subscription.stripe_subscription_id or str(subscription.id),
        tier=subscription.tier,
        status=subscription.status,
        interval=subscription.billing_interval,
        price_usd=float(subscription.get_price_usd()),
        trial_end=subscription.trial_end,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.canceled_at is not None
    )


@monetization_router.put("/subscriptions/current", response_model=SubscriptionResponse)
async def update_subscription(
    request: SubscriptionUpdateRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Update user's subscription (upgrade/downgrade)."""
    subscription = billing_service.get_subscription(user_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    
    try:
        if request.tier:
            updated_subscription = await billing_service.upgrade_subscription(
                user_id, request.tier, request.interval
            )
        else:
            updated_subscription = subscription
        
        return SubscriptionResponse(
            id=updated_subscription.stripe_subscription_id or str(updated_subscription.id),
            tier=updated_subscription.tier,
            status=updated_subscription.status,
            interval=updated_subscription.billing_interval,
            price_usd=float(updated_subscription.get_price_usd()),
            trial_end=updated_subscription.trial_end,
            current_period_end=updated_subscription.current_period_end,
            cancel_at_period_end=updated_subscription.canceled_at is not None
        )
        
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to update subscription")


@monetization_router.delete("/subscriptions/current")
async def cancel_subscription(
    at_period_end: bool = True,
    user_id: UUID = Depends(get_current_user_id)
):
    """Cancel user's subscription."""
    subscription = billing_service.get_subscription(user_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    
    try:
        await billing_service.cancel_subscription(user_id, at_period_end)
        return {"success": True, "cancel_at_period_end": at_period_end}
        
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


# ============================================================================
# PAYWALL CONFIGURATION ROUTES
# ============================================================================

@monetization_router.get("/paywall/config")
async def get_paywall_config(
    trigger: PaywallTrigger,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get server-driven paywall configuration."""
    try:
        # Get user's current tier
        subscription = billing_service.get_subscription(user_id)
        current_tier = subscription.tier if subscription else SubscriptionTier.FREE
        
        # Get paywall configuration
        config = paywall_service.get_paywall_config(
            user_id=user_id,
            current_tier=current_tier,
            trigger=trigger
        )
        
        # Track paywall view
        paywall_service.track_paywall_view(user_id, config)
        
        return config.dict()
        
    except Exception as e:
        logger.error(f"Error getting paywall config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get paywall configuration")


@monetization_router.post("/paywall/action")
async def track_paywall_action(
    paywall_id: str,
    action: str,
    tier_selected: Optional[SubscriptionTier] = None,
    interval_selected: Optional[BillingInterval] = None,
    user_id: UUID = Depends(get_current_user_id)
):
    """Track paywall user action."""
    try:
        # Get user's current tier for config reconstruction
        subscription = billing_service.get_subscription(user_id)
        current_tier = subscription.tier if subscription else SubscriptionTier.FREE
        
        # For tracking, we need the original config - simplified approach
        # In production, store configs or reconstruct properly
        from ...services.monetization.paywall_service import PaywallConfig, PaywallTemplate, PaywallVariant
        
        dummy_config = PaywallConfig(
            id=paywall_id,
            template=PaywallTemplate.UPGRADE_PROMPT,
            trigger=PaywallTrigger.PLAN_GENERATION,
            variant=PaywallVariant(
                id="default", name="Default", weight=1.0,
                headline="Upgrade", description="Get more features"
            ),
            offers=[],
            features=[]
        )
        
        paywall_service.track_paywall_action(
            user_id, dummy_config, action, tier_selected, interval_selected
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error tracking paywall action: {e}")
        raise HTTPException(status_code=500, detail="Failed to track paywall action")


# ============================================================================
# ENTITLEMENT ROUTES
# ============================================================================

@monetization_router.get("/entitlements/check")
async def check_feature_entitlement(
    feature: str,
    user_id: UUID = Depends(get_current_user_id)
) -> EntitlementCheckResponse:
    """Check user's entitlement to a specific feature."""
    try:
        from ...models.monetization import FeatureFlag
        
        # Convert string to FeatureFlag enum
        try:
            feature_flag = FeatureFlag(feature)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid feature: {feature}")
        
        result = entitlement_service.check_feature_access(user_id, feature_flag)
        
        return EntitlementCheckResponse(**result)
        
    except Exception as e:
        logger.error(f"Error checking entitlement: {e}")
        raise HTTPException(status_code=500, detail="Failed to check feature entitlement")


@monetization_router.get("/entitlements/usage", response_model=UsageSummaryResponse)
async def get_usage_summary(user_id: UUID = Depends(get_current_user_id)):
    """Get comprehensive usage summary for user."""
    try:
        summary = entitlement_service.get_usage_summary(user_id)
        return UsageSummaryResponse(**summary)
        
    except Exception as e:
        logger.error(f"Error getting usage summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage summary")


@monetization_router.get("/entitlements/tiers")
async def get_tier_comparison(user_id: UUID = Depends(get_current_user_id)):
    """Get feature comparison across subscription tiers."""
    try:
        subscription = billing_service.get_subscription(user_id)
        current_tier = subscription.tier if subscription else SubscriptionTier.FREE
        
        comparison = entitlement_service.get_tier_comparison(current_tier)
        return comparison
        
    except Exception as e:
        logger.error(f"Error getting tier comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tier comparison")


# ============================================================================
# EXPERIMENT ROUTES
# ============================================================================

@monetization_router.get("/experiments/{experiment_type}/config")
async def get_experiment_config(
    experiment_type: ExperimentType,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get experiment configuration for user."""
    try:
        config = experiment_service.get_experiment_config_for_user(user_id, experiment_type)
        
        if not config:
            return {"message": "No active experiment of this type"}
        
        return config
        
    except Exception as e:
        logger.error(f"Error getting experiment config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get experiment configuration")


@monetization_router.post("/experiments/track")
async def track_experiment_event(
    experiment_id: str,
    event_type: str,
    event_data: Optional[Dict] = None,
    user_id: UUID = Depends(get_current_user_id)
):
    """Track experiment event."""
    try:
        experiment_service.track_experiment_event(
            user_id, experiment_id, event_type, event_data
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error tracking experiment event: {e}")
        raise HTTPException(status_code=500, detail="Failed to track experiment event")


@monetization_router.get("/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    """Get experiment results (admin endpoint)."""
    try:
        results = experiment_service.get_experiment_results(experiment_id)
        return results
        
    except Exception as e:
        logger.error(f"Error getting experiment results: {e}")
        raise HTTPException(status_code=500, detail="Failed to get experiment results")


# ============================================================================
# WEBHOOK ROUTES
# ============================================================================

@monetization_router.post("/webhooks/stripe")
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")
        
        # Verify webhook signature
        webhook_handler = billing_service.webhook_handler
        if not webhook_handler.verify_webhook_signature(payload, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        # Parse event
        try:
            event = stripe.Event.construct_from(
                stripe.util.json.loads(payload.decode('utf-8')),
                stripe.api_key
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        
        # Handle event
        await webhook_handler.handle_webhook(event.type, event.data)
        
        return {"received": True}
        
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle webhook")


# ============================================================================
# ADMIN ROUTES (for monitoring and management)
# ============================================================================

@monetization_router.get("/admin/experiments")
async def list_experiments():
    """List all experiments (admin endpoint)."""
    try:
        experiments = []
        for exp_id, exp in experiment_service.experiments.items():
            experiments.append({
                "id": exp.id,
                "name": exp.name,
                "type": exp.type.value,
                "status": exp.status.value,
                "start_date": exp.start_date.isoformat() if exp.start_date else None,
                "variants": len(exp.variants)
            })
        
        return {"experiments": experiments}
        
    except Exception as e:
        logger.error(f"Error listing experiments: {e}")
        raise HTTPException(status_code=500, detail="Failed to list experiments")


@monetization_router.post("/admin/experiments/{experiment_id}/pause")
async def pause_experiment(experiment_id: str, reason: str = "Manual pause"):
    """Pause experiment (admin endpoint)."""
    try:
        success = experiment_service.pause_experiment(experiment_id, reason)
        if not success:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        return {"success": True, "experiment_id": experiment_id}
        
    except Exception as e:
        logger.error(f"Error pausing experiment: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause experiment")


@monetization_router.get("/admin/guardrails/{experiment_id}")
async def check_experiment_guardrails(experiment_id: str):
    """Check experiment guardrails (admin endpoint)."""
    try:
        violations = experiment_service.check_guardrails(experiment_id)
        return {
            "experiment_id": experiment_id,
            "violations": violations,
            "status": "warning" if violations else "ok"
        }
        
    except Exception as e:
        logger.error(f"Error checking guardrails: {e}")
        raise HTTPException(status_code=500, detail="Failed to check guardrails")


# Export router
__all__ = ["monetization_router"]
