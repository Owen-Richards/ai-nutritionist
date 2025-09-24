"""Server-driven paywall system for Track E3.

Provides dynamic paywall configuration with A/B testing support.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ...models.monetization import BillingInterval, MonetizationConfig, SubscriptionTier

logger = logging.getLogger(__name__)


class PaywallTemplate(str, Enum):
    """Paywall template types."""
    FEATURE_GATE = "feature_gate"  # Block access to specific feature
    USAGE_LIMIT = "usage_limit"   # Hit usage limit
    TRIAL_EXPIRED = "trial_expired"  # Trial period ended
    UPGRADE_PROMPT = "upgrade_prompt"  # General upgrade suggestion
    ONBOARDING = "onboarding"     # During user onboarding


class PaywallTrigger(str, Enum):
    """Paywall trigger contexts."""
    PLAN_GENERATION = "plan_generation"
    WIDGET_ACCESS = "widget_access"
    CREW_JOIN = "crew_join"
    CALENDAR_SYNC = "calendar_sync"
    GROCERY_EXPORT = "grocery_export"
    FITNESS_SYNC = "fitness_sync"
    SMS_NUDGE = "sms_nudge"
    TRIAL_END = "trial_end"
    BILLING_FAILED = "billing_failed"
    ONBOARDING = "onboarding"
    UPGRADE_PROMPT = "upgrade_prompt"


class PaywallVariant(BaseModel):
    """A/B test variant for paywall."""
    id: str
    name: str
    weight: float = Field(ge=0, le=1)  # Percentage of traffic (0.0 to 1.0)
    
    # Content configuration
    headline: str
    subtitle: Optional[str] = None
    description: str
    cta_primary: str = "Upgrade Now"
    cta_secondary: Optional[str] = "Maybe Later"
    
    # Visual configuration
    theme: str = "default"  # default, minimal, premium
    show_discount: bool = True
    show_trial: bool = True
    show_features: bool = True
    
    # Behavioral configuration
    auto_start_trial: bool = False
    emphasize_yearly: bool = True
    
    # Experiment metadata
    experiment_id: Optional[str] = None
    experiment_name: Optional[str] = None


class PaywallOffer(BaseModel):
    """Pricing offer in paywall."""
    tier: SubscriptionTier
    interval: BillingInterval
    price_usd: float
    original_price_usd: Optional[float] = None  # For showing discounts
    discount_percent: Optional[int] = None
    trial_days: int = 7
    
    # Display configuration
    is_featured: bool = False
    badge: Optional[str] = None  # "Most Popular", "Best Value", etc.
    
    @property
    def has_discount(self) -> bool:
        """Check if offer has a discount."""
        return self.original_price_usd is not None and self.original_price_usd > self.price_usd


class PaywallFeature(BaseModel):
    """Feature highlight in paywall."""
    name: str
    description: str
    icon: Optional[str] = None
    tier_required: SubscriptionTier
    is_new: bool = False


class PaywallConfig(BaseModel):
    """Complete paywall configuration."""
    id: str = Field(default_factory=lambda: f"paywall_{int(datetime.now().timestamp())}")
    template: PaywallTemplate
    trigger: PaywallTrigger
    variant: PaywallVariant
    
    # Offers and features
    offers: List[PaywallOffer]
    features: List[PaywallFeature]
    
    # Targeting
    target_tiers: List[SubscriptionTier] = Field(default_factory=lambda: [SubscriptionTier.FREE])
    
    # Experiment configuration
    experiment_bucket: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    
    def get_featured_offer(self) -> Optional[PaywallOffer]:
        """Get the featured offer."""
        for offer in self.offers:
            if offer.is_featured:
                return offer
        return self.offers[0] if self.offers else None


class PaywallExperiment(BaseModel):
    """A/B experiment configuration."""
    id: str
    name: str
    description: str
    
    # Experiment configuration
    variants: List[PaywallVariant]
    active: bool = True
    start_date: datetime = Field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    
    # Targeting
    target_triggers: List[PaywallTrigger]
    target_tiers: List[SubscriptionTier] = Field(default_factory=lambda: [SubscriptionTier.FREE])
    
    # Traffic allocation
    traffic_percentage: float = Field(default=1.0, ge=0, le=1)
    
    def get_variant_for_user(self, user_id: UUID) -> PaywallVariant:
        """Get variant for user using consistent hashing."""
        if not self.active or not self.variants:
            return self.variants[0] if self.variants else None
        
        # Use user ID for consistent variant assignment
        hash_input = f"{self.id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        hash_ratio = (hash_value % 10000) / 10000.0  # 0.0000 to 0.9999
        
        # Check if user is in experiment traffic
        if hash_ratio >= self.traffic_percentage:
            return self.variants[0]  # Default variant
        
        # Assign variant based on weights
        cumulative_weight = 0.0
        for variant in self.variants:
            cumulative_weight += variant.weight
            if hash_ratio < cumulative_weight:
                return variant
        
        # Fallback to first variant
        return self.variants[0]


class PaywallService:
    """Service for managing paywall configurations and experiments."""
    
    def __init__(self):
        self.monetization_config = MonetizationConfig()
        
        # In-memory storage for demo (use database in production)
        self.experiments: Dict[str, PaywallExperiment] = {}
        self.templates: Dict[PaywallTemplate, Dict] = {}
        
        # Initialize default experiments
        self._initialize_default_experiments()
        self._initialize_templates()
    
    def _initialize_default_experiments(self) -> None:
        """Initialize default A/B experiments."""
        
        # Price point experiment
        price_experiment = PaywallExperiment(
            id="price_test_2024_q4",
            name="Price Point Testing Q4 2024",
            description="Test different price points for Plus tier",
            target_triggers=[PaywallTrigger.PLAN_GENERATION, PaywallTrigger.WIDGET_ACCESS],
            variants=[
                PaywallVariant(
                    id="price_control",
                    name="Control ($12.99)",
                    weight=0.33,
                    headline="Upgrade to Plus",
                    description="Get adaptive meal planning and widgets",
                    experiment_id="price_test_2024_q4",
                    experiment_name="Price Point Testing"
                ),
                PaywallVariant(
                    id="price_low",
                    name="Lower Price ($9.99)",
                    weight=0.33,
                    headline="Upgrade to Plus",
                    description="Get adaptive meal planning and widgets for just $9.99",
                    experiment_id="price_test_2024_q4",
                    experiment_name="Price Point Testing"
                ),
                PaywallVariant(
                    id="price_high",
                    name="Higher Price ($14.99)",
                    weight=0.34,
                    headline="Upgrade to Plus Premium",
                    description="Get our premium adaptive planning experience",
                    experiment_id="price_test_2024_q4",
                    experiment_name="Price Point Testing"
                )
            ]
        )
        
        # Trial length experiment
        trial_experiment = PaywallExperiment(
            id="trial_length_2024",
            name="Trial Length Testing",
            description="Test 7 vs 14 day trial periods",
            target_triggers=[PaywallTrigger.ONBOARDING, PaywallTrigger.UPGRADE_PROMPT],
            variants=[
                PaywallVariant(
                    id="trial_7_days",
                    name="7 Day Trial",
                    weight=0.5,
                    headline="Start Your 7-Day Free Trial",
                    description="Try all Plus features risk-free",
                    show_trial=True,
                    experiment_id="trial_length_2024"
                ),
                PaywallVariant(
                    id="trial_14_days",
                    name="14 Day Trial",
                    weight=0.5,
                    headline="Start Your 14-Day Free Trial",
                    description="Extended trial - try all Plus features risk-free",
                    show_trial=True,
                    experiment_id="trial_length_2024"
                )
            ]
        )
        
        self.experiments["price_test_2024_q4"] = price_experiment
        self.experiments["trial_length_2024"] = trial_experiment
    
    def _initialize_templates(self) -> None:
        """Initialize paywall templates."""
        
        self.templates[PaywallTemplate.FEATURE_GATE] = {
            "default_headline": "Unlock {feature_name}",
            "default_description": "This feature is available in {required_tier} and higher tiers.",
            "default_cta": "Upgrade Now"
        }
        
        self.templates[PaywallTemplate.USAGE_LIMIT] = {
            "default_headline": "You've reached your {feature_name} limit",
            "default_description": "Upgrade to get unlimited access to {feature_name} and more.",
            "default_cta": "Upgrade for Unlimited"
        }
        
        self.templates[PaywallTemplate.TRIAL_EXPIRED] = {
            "default_headline": "Your trial has expired",
            "default_description": "Continue enjoying all the features you love.",
            "default_cta": "Continue with Plus"
        }
        
        self.templates[PaywallTemplate.UPGRADE_PROMPT] = {
            "default_headline": "Ready to take your nutrition to the next level?",
            "default_description": "Unlock advanced features designed for serious nutrition enthusiasts.",
            "default_cta": "Upgrade Now"
        }
        
        self.templates[PaywallTemplate.ONBOARDING] = {
            "default_headline": "Welcome to AI Nutritionist",
            "default_description": "Start with a free trial and discover personalized nutrition planning.",
            "default_cta": "Start Free Trial"
        }
    
    def get_paywall_config(self, user_id: UUID, current_tier: SubscriptionTier,
                          trigger: PaywallTrigger, 
                          context: Optional[Dict] = None) -> PaywallConfig:
        """Get paywall configuration for user and context."""
        
        # Find applicable experiment
        experiment = self._find_experiment_for_context(trigger, current_tier)
        
        # Get variant for user
        if experiment:
            variant = experiment.get_variant_for_user(user_id)
            template = PaywallTemplate.UPGRADE_PROMPT  # Default template
        else:
            # Use default configuration
            variant = self._get_default_variant(trigger, context)
            template = self._get_template_for_trigger(trigger)
        
        # Generate offers based on current tier and variant
        offers = self._generate_offers(current_tier, variant)
        
        # Generate feature list
        features = self._generate_features(current_tier)
        
        # Create paywall config
        config = PaywallConfig(
            template=template,
            trigger=trigger,
            variant=variant,
            offers=offers,
            features=features,
            target_tiers=[current_tier],
            experiment_bucket=experiment.id if experiment else None
        )
        
        return config
    
    def _find_experiment_for_context(self, trigger: PaywallTrigger,
                                   tier: SubscriptionTier) -> Optional[PaywallExperiment]:
        """Find active experiment for given context."""
        for experiment in self.experiments.values():
            if (experiment.active and
                trigger in experiment.target_triggers and
                tier in experiment.target_tiers):
                return experiment
        return None
    
    def _get_default_variant(self, trigger: PaywallTrigger,
                           context: Optional[Dict] = None) -> PaywallVariant:
        """Get default variant when no experiment is active."""
        template_config = self.templates.get(
            self._get_template_for_trigger(trigger), {}
        )
        
        return PaywallVariant(
            id="default",
            name="Default",
            weight=1.0,
            headline=template_config.get("default_headline", "Upgrade your plan"),
            description=template_config.get("default_description", "Unlock more features"),
            cta_primary=template_config.get("default_cta", "Upgrade Now")
        )
    
    def _get_template_for_trigger(self, trigger: PaywallTrigger) -> PaywallTemplate:
        """Get appropriate template for trigger."""
        trigger_template_map = {
            PaywallTrigger.PLAN_GENERATION: PaywallTemplate.USAGE_LIMIT,
            PaywallTrigger.WIDGET_ACCESS: PaywallTemplate.FEATURE_GATE,
            PaywallTrigger.CREW_JOIN: PaywallTemplate.FEATURE_GATE,
            PaywallTrigger.CALENDAR_SYNC: PaywallTemplate.FEATURE_GATE,
            PaywallTrigger.GROCERY_EXPORT: PaywallTemplate.FEATURE_GATE,
            PaywallTrigger.FITNESS_SYNC: PaywallTemplate.FEATURE_GATE,
            PaywallTrigger.SMS_NUDGE: PaywallTemplate.USAGE_LIMIT,
            PaywallTrigger.TRIAL_END: PaywallTemplate.TRIAL_EXPIRED,
            PaywallTrigger.BILLING_FAILED: PaywallTemplate.TRIAL_EXPIRED
        }
        
        return trigger_template_map.get(trigger, PaywallTemplate.UPGRADE_PROMPT)
    
    def _generate_offers(self, current_tier: SubscriptionTier,
                        variant: PaywallVariant) -> List[PaywallOffer]:
        """Generate pricing offers based on tier and variant."""
        offers = []
        
        # Get upgrade path
        upgrade_tiers = self.monetization_config.get_upgrade_path(current_tier)
        
        for tier in upgrade_tiers:
            pricing_config = self.monetization_config.get_pricing_config(tier)
            
            # Monthly offer
            monthly_offer = PaywallOffer(
                tier=tier,
                interval=BillingInterval.MONTHLY,
                price_usd=float(pricing_config.monthly_price_usd),
                trial_days=pricing_config.trial_days
            )
            
            # Yearly offer with discount
            yearly_offer = PaywallOffer(
                tier=tier,
                interval=BillingInterval.YEARLY,
                price_usd=float(pricing_config.yearly_price_usd),
                original_price_usd=float(pricing_config.monthly_price_usd * 12),
                discount_percent=int(pricing_config.yearly_discount_percent),
                trial_days=pricing_config.trial_days,
                is_featured=variant.emphasize_yearly,
                badge="Best Value" if variant.emphasize_yearly else None
            )
            
            # Apply experimental pricing if variant has experiment
            if variant.experiment_id == "price_test_2024_q4":
                if variant.id == "price_low":
                    monthly_offer.price_usd = 9.99
                    yearly_offer.price_usd = 99.90
                elif variant.id == "price_high":
                    monthly_offer.price_usd = 14.99
                    yearly_offer.price_usd = 149.90
            
            # Apply experimental trial length
            if variant.experiment_id == "trial_length_2024":
                trial_days = 14 if variant.id == "trial_14_days" else 7
                monthly_offer.trial_days = trial_days
                yearly_offer.trial_days = trial_days
            
            offers.extend([monthly_offer, yearly_offer])
        
        return offers
    
    def _generate_features(self, current_tier: SubscriptionTier) -> List[PaywallFeature]:
        """Generate feature highlights for paywall."""
        features = []
        
        if current_tier == SubscriptionTier.FREE:
            # Show Plus features
            features.extend([
                PaywallFeature(
                    name="Adaptive Meal Planning",
                    description="AI learns your preferences and adjusts recommendations",
                    tier_required=SubscriptionTier.PLUS
                ),
                PaywallFeature(
                    name="Home Screen Widget",
                    description="Quick access to your meal plan and progress",
                    tier_required=SubscriptionTier.PLUS
                ),
                PaywallFeature(
                    name="Advanced Nutrition Tracking",
                    description="Detailed macro and micronutrient analysis",
                    tier_required=SubscriptionTier.PLUS
                ),
                PaywallFeature(
                    name="Unlimited SMS Nudges",
                    description="Stay motivated with personalized reminders",
                    tier_required=SubscriptionTier.PLUS
                )
            ])
        
        if current_tier in [SubscriptionTier.FREE, SubscriptionTier.PLUS]:
            # Show Pro features
            features.extend([
                PaywallFeature(
                    name="Nutrition Crews",
                    description="Join communities for motivation and support",
                    tier_required=SubscriptionTier.PRO
                ),
                PaywallFeature(
                    name="Calendar Integration",
                    description="Sync meal prep events with Google Calendar & Outlook",
                    tier_required=SubscriptionTier.PRO
                ),
                PaywallFeature(
                    name="Grocery Export & Partner Links",
                    description="Export shopping lists with direct store integration",
                    tier_required=SubscriptionTier.PRO
                ),
                PaywallFeature(
                    name="Fitness Integration",
                    description="Connect with Apple Health, Fitbit, and more",
                    tier_required=SubscriptionTier.PRO,
                    is_new=True
                )
            ])
        
        return features
    
    def track_paywall_view(self, user_id: UUID, config: PaywallConfig) -> None:
        """Track paywall view for analytics."""
        event_data = {
            "user_id": str(user_id),
            "paywall_id": config.id,
            "template": config.template.value,
            "trigger": config.trigger.value,
            "variant_id": config.variant.id,
            "experiment_id": config.variant.experiment_id,
            "offers_shown": len(config.offers),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Paywall viewed: {json.dumps(event_data)}")
        # In production, send to analytics service
    
    def track_paywall_action(self, user_id: UUID, config: PaywallConfig,
                           action: str, tier_selected: Optional[SubscriptionTier] = None,
                           interval_selected: Optional[BillingInterval] = None) -> None:
        """Track paywall action (upgrade, dismiss, etc.)."""
        event_data = {
            "user_id": str(user_id),
            "paywall_id": config.id,
            "action": action,  # "upgrade", "dismiss", "trial_start"
            "variant_id": config.variant.id,
            "experiment_id": config.variant.experiment_id,
            "tier_selected": tier_selected.value if tier_selected else None,
            "interval_selected": interval_selected.value if interval_selected else None,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Paywall action: {json.dumps(event_data)}")
        # In production, send to analytics service
    
    def get_experiment_results(self, experiment_id: str) -> Dict:
        """Get experiment results (placeholder for analytics integration)."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return {"error": "Experiment not found"}
        
        # Placeholder results - in production, query analytics database
        return {
            "experiment_id": experiment_id,
            "name": experiment.name,
            "status": "active" if experiment.active else "completed",
            "variants": [
                {
                    "variant_id": variant.id,
                    "name": variant.name,
                    "traffic_percentage": variant.weight,
                    "views": 1250,  # Placeholder
                    "conversions": 87,  # Placeholder
                    "conversion_rate": 0.0696,  # Placeholder
                    "revenue_per_user": 12.50  # Placeholder
                }
                for variant in experiment.variants
            ]
        }


# Export main classes
__all__ = [
    "PaywallTemplate",
    "PaywallTrigger", 
    "PaywallVariant",
    "PaywallOffer",
    "PaywallFeature",
    "PaywallConfig",
    "PaywallExperiment",
    "PaywallService"
]
