"""Integration tests for Track E - Monetization.

Tests for subscription tiers, billing, paywall, and experiments.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.monetization import (
    BillingInterval,
    FeatureFlag,
    SubscriptionStatus,
    SubscriptionTier,
    TierDefinition,
    Subscription,
    UsageTracker
)
from src.services.monetization.billing_service import BillingService
from src.services.monetization.entitlement_service import EntitlementService
from src.services.monetization.paywall_service import (
    PaywallService,
    PaywallTrigger,
    PaywallTemplate
)
from src.services.monetization.experiment_service import (
    ExperimentService,
    ExperimentType
)


class TestSubscriptionTiers:
    """Test subscription tier configuration and entitlements."""

    def test_tier_pricing_configuration(self):
        """Test pricing configuration for all tiers."""
        from src.models.monetization import MonetizationConfig
        
        config = MonetizationConfig()
        
        # Free tier
        free_pricing = config.get_pricing_config(SubscriptionTier.FREE)
        assert free_pricing.monthly_price_usd == Decimal("0")
        assert free_pricing.yearly_price_usd == Decimal("0")
        assert free_pricing.trial_days == 0
        
        # Plus tier
        plus_pricing = config.get_pricing_config(SubscriptionTier.PLUS)
        assert plus_pricing.monthly_price_usd == Decimal("12.99")
        assert plus_pricing.yearly_price_usd == Decimal("129.90")
        assert plus_pricing.trial_days == 7
        assert plus_pricing.yearly_discount_percent > 15  # Should have meaningful discount
        
        # Pro tier
        pro_pricing = config.get_pricing_config(SubscriptionTier.PRO)
        assert pro_pricing.monthly_price_usd == Decimal("24.99")
        assert pro_pricing.yearly_price_usd == Decimal("249.90")
        assert pro_pricing.trial_days == 7

    def test_feature_entitlements_by_tier(self):
        """Test feature access by subscription tier."""
        from src.models.monetization import MonetizationConfig
        
        config = MonetizationConfig()
        
        # Free tier features
        free_tier = config.get_tier_definition(SubscriptionTier.FREE)
        assert free_tier.has_feature(FeatureFlag.BASIC_MEAL_PLANS)
        assert free_tier.has_feature(FeatureFlag.SMS_NUDGES)
        assert not free_tier.has_feature(FeatureFlag.ADAPTIVE_PLANNING)
        assert not free_tier.has_feature(FeatureFlag.CREWS)
        
        # Plus tier features
        plus_tier = config.get_tier_definition(SubscriptionTier.PLUS)
        assert plus_tier.has_feature(FeatureFlag.BASIC_MEAL_PLANS)
        assert plus_tier.has_feature(FeatureFlag.SMS_NUDGES)
        assert plus_tier.has_feature(FeatureFlag.ADAPTIVE_PLANNING)
        assert plus_tier.has_feature(FeatureFlag.WIDGETS)
        assert not plus_tier.has_feature(FeatureFlag.CREWS)
        assert not plus_tier.has_feature(FeatureFlag.CALENDAR_INTEGRATION)
        
        # Pro tier features
        pro_tier = config.get_tier_definition(SubscriptionTier.PRO)
        assert pro_tier.has_feature(FeatureFlag.BASIC_MEAL_PLANS)
        assert pro_tier.has_feature(FeatureFlag.ADAPTIVE_PLANNING)
        assert pro_tier.has_feature(FeatureFlag.CREWS)
        assert pro_tier.has_feature(FeatureFlag.CALENDAR_INTEGRATION)
        assert pro_tier.has_feature(FeatureFlag.GROCERY_EXPORT)
        assert pro_tier.has_feature(FeatureFlag.FITNESS_INTEGRATION)

    def test_usage_limits_by_tier(self):
        """Test usage limits for different tiers."""
        from src.models.monetization import MonetizationConfig
        
        config = MonetizationConfig()
        
        # Free tier limits
        free_tier = config.get_tier_definition(SubscriptionTier.FREE)
        meal_plans_entitlement = free_tier.get_feature_entitlement(FeatureFlag.BASIC_MEAL_PLANS)
        sms_entitlement = free_tier.get_feature_entitlement(FeatureFlag.SMS_NUDGES)
        
        assert meal_plans_entitlement.limit == 1  # 1 active plan
        assert sms_entitlement.limit == 3  # 3 SMS per week
        
        # Plus tier limits
        plus_tier = config.get_tier_definition(SubscriptionTier.PLUS)
        plus_meal_plans = plus_tier.get_feature_entitlement(FeatureFlag.BASIC_MEAL_PLANS)
        plus_sms = plus_tier.get_feature_entitlement(FeatureFlag.SMS_NUDGES)
        
        assert plus_meal_plans.limit == 5  # 5 active plans
        assert plus_sms.limit == 7  # Daily SMS
        
        # Pro tier limits (unlimited)
        pro_tier = config.get_tier_definition(SubscriptionTier.PRO)
        pro_meal_plans = pro_tier.get_feature_entitlement(FeatureFlag.BASIC_MEAL_PLANS)
        pro_sms = pro_tier.get_feature_entitlement(FeatureFlag.SMS_NUDGES)
        
        assert pro_meal_plans.limit is None  # Unlimited
        assert pro_sms.limit is None  # Unlimited


class TestBillingIntegration:
    """Test Stripe billing integration."""

    @pytest.fixture
    def billing_service(self):
        """Create billing service instance."""
        return BillingService()

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    def test_subscription_model_validation(self, user_id):
        """Test subscription model validation."""
        subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.PLUS,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            price_cents=1299,
            current_period_start=datetime.now(),
            current_period_end=datetime.now() + timedelta(days=30)
        )
        
        assert subscription.is_active == True
        assert subscription.is_in_trial == False
        assert subscription.get_price_usd() == Decimal("12.99")
        assert subscription.days_until_renewal is not None

    def test_trial_subscription_logic(self, user_id):
        """Test trial subscription behavior."""
        trial_end = datetime.now() + timedelta(days=5)
        
        subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.PLUS,
            status=SubscriptionStatus.TRIALING,
            billing_interval=BillingInterval.MONTHLY,
            trial_end=trial_end,
            price_cents=1299
        )
        
        assert subscription.is_active == True
        assert subscription.is_in_trial == True

    @pytest.mark.asyncio
    @patch('stripe.Customer.create')
    @patch('stripe.Subscription.create')
    async def test_create_customer_and_subscription(self, mock_stripe_sub, mock_stripe_customer, 
                                                   billing_service, user_id):
        """Test customer and subscription creation."""
        # Mock Stripe responses
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"
        mock_stripe_customer.return_value = mock_customer
        
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test123"
        mock_subscription.status = "active"
        mock_subscription.customer = "cus_test123"
        mock_subscription.created = int(datetime.now().timestamp())
        mock_subscription.current_period_start = int(datetime.now().timestamp())
        mock_subscription.current_period_end = int((datetime.now() + timedelta(days=30)).timestamp())
        mock_subscription.metadata = {"tier": "plus", "interval": "monthly"}
        mock_subscription.items = {
            "data": [{
                "price": {
                    "id": "price_plus_monthly",
                    "unit_amount": 1299,
                    "currency": "usd"
                }
            }]
        }
        mock_stripe_sub.return_value = mock_subscription
        
        customer, subscription = await billing_service.create_customer_and_subscription(
            user_id=user_id,
            email="test@example.com",
            name="Test User",
            tier=SubscriptionTier.PLUS,
            interval=BillingInterval.MONTHLY
        )
        
        assert customer.id == "cus_test123"
        assert subscription.id == "sub_test123"
        assert user_id in billing_service.subscriptions

    def test_usage_tracking(self, billing_service, user_id):
        """Test usage tracking functionality."""
        # Create subscription
        subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            price_cents=0
        )
        billing_service.subscriptions[user_id] = subscription
        
        # Create usage tracker
        period_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=30)
        
        tracker = UsageTracker(
            user_id=user_id,
            subscription_id=subscription.id,
            period_start=period_start,
            period_end=period_end
        )
        billing_service.usage_trackers[user_id] = tracker
        
        # Test usage increment
        tracker.increment_usage(FeatureFlag.BASIC_MEAL_PLANS, 1)
        tracker.increment_usage(FeatureFlag.SMS_NUDGES, 2)
        
        assert tracker.get_usage(FeatureFlag.BASIC_MEAL_PLANS) == 1
        assert tracker.get_usage(FeatureFlag.SMS_NUDGES) == 2


class TestEntitlementSystem:
    """Test entitlement checking and enforcement."""

    @pytest.fixture
    def billing_service(self):
        """Create billing service with test data."""
        service = BillingService()
        return service

    @pytest.fixture
    def entitlement_service(self, billing_service):
        """Create entitlement service."""
        return EntitlementService(billing_service)

    @pytest.fixture
    def free_user_id(self, billing_service):
        """Create free tier user."""
        user_id = uuid4()
        subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            price_cents=0
        )
        billing_service.subscriptions[user_id] = subscription
        
        # Add usage tracker
        billing_service.usage_trackers[user_id] = UsageTracker(
            user_id=user_id,
            subscription_id=subscription.id,
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(days=30)
        )
        return user_id

    @pytest.fixture
    def plus_user_id(self, billing_service):
        """Create Plus tier user."""
        user_id = uuid4()
        subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.PLUS,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            price_cents=1299
        )
        billing_service.subscriptions[user_id] = subscription
        
        billing_service.usage_trackers[user_id] = UsageTracker(
            user_id=user_id,
            subscription_id=subscription.id,
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(days=30)
        )
        return user_id

    def test_feature_access_free_user(self, entitlement_service, free_user_id):
        """Test feature access for free tier user."""
        # Should have access to free features
        basic_plans_access = entitlement_service.check_feature_access(
            free_user_id, FeatureFlag.BASIC_MEAL_PLANS
        )
        assert basic_plans_access["has_access"] == True
        assert basic_plans_access["limit"] == 1
        
        sms_access = entitlement_service.check_feature_access(
            free_user_id, FeatureFlag.SMS_NUDGES
        )
        assert sms_access["has_access"] == True
        assert sms_access["limit"] == 3
        
        # Should not have access to premium features
        adaptive_access = entitlement_service.check_feature_access(
            free_user_id, FeatureFlag.ADAPTIVE_PLANNING
        )
        assert adaptive_access["has_access"] == False
        assert adaptive_access["upgrade_required"] == True
        
        crews_access = entitlement_service.check_feature_access(
            free_user_id, FeatureFlag.CREWS
        )
        assert crews_access["has_access"] == False
        assert crews_access["upgrade_required"] == True

    def test_feature_access_plus_user(self, entitlement_service, plus_user_id):
        """Test feature access for Plus tier user."""
        # Should have access to Plus features
        adaptive_access = entitlement_service.check_feature_access(
            plus_user_id, FeatureFlag.ADAPTIVE_PLANNING
        )
        assert adaptive_access["has_access"] == True
        
        widgets_access = entitlement_service.check_feature_access(
            plus_user_id, FeatureFlag.WIDGETS
        )
        assert widgets_access["has_access"] == True
        
        # Should not have access to Pro features
        crews_access = entitlement_service.check_feature_access(
            plus_user_id, FeatureFlag.CREWS
        )
        assert crews_access["has_access"] == False
        assert crews_access["upgrade_required"] == True

    def test_usage_limit_enforcement(self, entitlement_service, billing_service, free_user_id):
        """Test usage limit enforcement."""
        # Simulate reaching usage limit
        tracker = billing_service.get_usage_tracker(free_user_id)
        tracker.increment_usage(FeatureFlag.BASIC_MEAL_PLANS, 1)  # Reach limit of 1
        
        # Should still have access (at limit)
        access_check = entitlement_service.check_feature_access(
            free_user_id, FeatureFlag.BASIC_MEAL_PLANS
        )
        assert access_check["has_access"] == True
        assert access_check["usage"] == 1
        assert access_check["remaining"] == 0
        
        # Check usage limit for increment
        usage_check = entitlement_service.check_usage_limit(
            free_user_id, FeatureFlag.BASIC_MEAL_PLANS, 1
        )
        assert usage_check["has_access"] == False  # Would exceed limit
        assert usage_check["upgrade_required"] == True

    def test_entitlement_caching(self, entitlement_service, free_user_id):
        """Test entitlement result caching."""
        # First check should hit database/service
        result1 = entitlement_service.check_feature_access(
            free_user_id, FeatureFlag.BASIC_MEAL_PLANS
        )
        
        # Second check should hit cache
        result2 = entitlement_service.check_feature_access(
            free_user_id, FeatureFlag.BASIC_MEAL_PLANS
        )
        
        assert result1 == result2
        
        # Cache invalidation test
        entitlement_service.cache.invalidate(free_user_id, FeatureFlag.BASIC_MEAL_PLANS)
        
        # Should be able to check again after invalidation
        result3 = entitlement_service.check_feature_access(
            free_user_id, FeatureFlag.BASIC_MEAL_PLANS
        )
        assert result3["has_access"] == True

    def test_usage_summary(self, entitlement_service, free_user_id, billing_service):
        """Test comprehensive usage summary."""
        # Add some usage
        tracker = billing_service.get_usage_tracker(free_user_id)
        tracker.increment_usage(FeatureFlag.BASIC_MEAL_PLANS, 1)
        tracker.increment_usage(FeatureFlag.SMS_NUDGES, 2)
        
        summary = entitlement_service.get_usage_summary(free_user_id)
        
        assert summary["user_id"] == str(free_user_id)
        assert summary["tier"] == "free"
        assert summary["billing_period"] is not None
        assert "basic_meal_plans" in summary["features"]
        assert "sms_nudges" in summary["features"]
        
        # Check usage counts
        basic_plans_usage = summary["features"]["basic_meal_plans"]
        assert basic_plans_usage["usage"] == 1
        assert basic_plans_usage["limit"] == 1
        assert basic_plans_usage["remaining"] == 0


class TestPaywallSystem:
    """Test server-driven paywall system."""

    @pytest.fixture
    def paywall_service(self):
        """Create paywall service."""
        return PaywallService()

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    def test_paywall_config_generation(self, paywall_service, user_id):
        """Test paywall configuration generation."""
        config = paywall_service.get_paywall_config(
            user_id=user_id,
            current_tier=SubscriptionTier.FREE,
            trigger=PaywallTrigger.PLAN_GENERATION
        )
        
        assert config.trigger == PaywallTrigger.PLAN_GENERATION
        assert config.template == PaywallTemplate.USAGE_LIMIT
        assert len(config.offers) > 0
        assert len(config.features) > 0
        
        # Check offers include Plus and Pro tiers
        tier_offers = {offer.tier for offer in config.offers}
        assert SubscriptionTier.PLUS in tier_offers
        assert SubscriptionTier.PRO in tier_offers

    def test_experiment_variant_assignment(self, paywall_service, user_id):
        """Test consistent variant assignment for A/B tests."""
        # Get paywall config multiple times
        config1 = paywall_service.get_paywall_config(
            user_id=user_id,
            current_tier=SubscriptionTier.FREE,
            trigger=PaywallTrigger.PLAN_GENERATION
        )
        
        config2 = paywall_service.get_paywall_config(
            user_id=user_id,
            current_tier=SubscriptionTier.FREE,
            trigger=PaywallTrigger.PLAN_GENERATION
        )
        
        # Should get same variant consistently
        assert config1.variant.id == config2.variant.id

    def test_paywall_feature_highlights(self, paywall_service, user_id):
        """Test feature highlights in paywall."""
        config = paywall_service.get_paywall_config(
            user_id=user_id,
            current_tier=SubscriptionTier.FREE,
            trigger=PaywallTrigger.WIDGET_ACCESS
        )
        
        # Should highlight Plus features for free user
        feature_names = {feature.name for feature in config.features}
        assert "Adaptive Meal Planning" in feature_names
        assert "Home Screen Widget" in feature_names
        
        # Check feature tier requirements
        for feature in config.features:
            assert feature.tier_required in [SubscriptionTier.PLUS, SubscriptionTier.PRO]

    def test_pricing_offers_with_discounts(self, paywall_service, user_id):
        """Test pricing offers with yearly discounts."""
        config = paywall_service.get_paywall_config(
            user_id=user_id,
            current_tier=SubscriptionTier.FREE,
            trigger=PaywallTrigger.UPGRADE_PROMPT
        )
        
        # Find yearly offers
        yearly_offers = [offer for offer in config.offers if offer.interval == BillingInterval.YEARLY]
        assert len(yearly_offers) > 0
        
        for offer in yearly_offers:
            assert offer.has_discount == True
            assert offer.discount_percent is not None
            assert offer.discount_percent > 0

    def test_paywall_tracking(self, paywall_service, user_id):
        """Test paywall view and action tracking."""
        config = paywall_service.get_paywall_config(
            user_id=user_id,
            current_tier=SubscriptionTier.FREE,
            trigger=PaywallTrigger.PLAN_GENERATION
        )
        
        # Track view (should not raise exception)
        paywall_service.track_paywall_view(user_id, config)
        
        # Track action (should not raise exception)
        paywall_service.track_paywall_action(
            user_id, config, "upgrade", 
            SubscriptionTier.PLUS, BillingInterval.MONTHLY
        )


class TestExperimentFramework:
    """Test monetization experiments framework."""

    @pytest.fixture
    def experiment_service(self):
        """Create experiment service."""
        return ExperimentService()

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    def test_experiment_initialization(self, experiment_service):
        """Test default experiments are initialized."""
        assert len(experiment_service.experiments) > 0
        
        # Check specific experiments exist
        assert "price_test_q4_2024" in experiment_service.experiments
        assert "trial_length_2024" in experiment_service.experiments
        assert "nudge_frequency_2024" in experiment_service.experiments

    def test_user_assignment_to_experiment(self, experiment_service, user_id):
        """Test user assignment to experiments."""
        experiment_id = "price_test_q4_2024"
        
        # Set experiment to active
        experiment_service.experiments[experiment_id].status = "active"
        
        variant_id = experiment_service.assign_user_to_experiment(user_id, experiment_id)
        assert variant_id is not None
        
        # Should get same variant on repeated calls
        variant_id2 = experiment_service.assign_user_to_experiment(user_id, experiment_id)
        assert variant_id == variant_id2
        
        # Check assignment is stored
        stored_variant = experiment_service.get_user_variant(user_id, experiment_id)
        assert stored_variant == variant_id

    def test_experiment_config_retrieval(self, experiment_service, user_id):
        """Test getting experiment config for user."""
        # Set experiment to active
        experiment_service.experiments["price_test_q4_2024"].status = "active"
        
        config = experiment_service.get_experiment_config_for_user(
            user_id, ExperimentType.PRICE_TESTING
        )
        
        assert config is not None
        assert "experiment_id" in config
        assert "variant_id" in config
        assert "config" in config
        assert config["experiment_id"] == "price_test_q4_2024"

    def test_experiment_event_tracking(self, experiment_service, user_id):
        """Test experiment event tracking."""
        experiment_id = "trial_length_2024"
        
        # Set experiment to active and assign user
        experiment_service.experiments[experiment_id].status = "active"
        variant_id = experiment_service.assign_user_to_experiment(user_id, experiment_id)
        
        # Track events (should not raise exceptions)
        experiment_service.track_experiment_event(
            user_id, experiment_id, "paywall_viewed"
        )
        
        experiment_service.track_experiment_event(
            user_id, experiment_id, "trial_started", 
            {"trial_days": 14}
        )

    def test_guardrail_checking(self, experiment_service):
        """Test experiment guardrail checking."""
        experiment_id = "price_test_q4_2024"
        
        # Check guardrails (with no real data, should return empty)
        violations = experiment_service.check_guardrails(experiment_id)
        assert isinstance(violations, list)

    def test_experiment_pause_functionality(self, experiment_service):
        """Test experiment pausing."""
        experiment_id = "nudge_frequency_2024"
        
        # Pause experiment
        success = experiment_service.pause_experiment(experiment_id, "Test pause")
        assert success == True
        
        # Check status updated
        experiment = experiment_service.experiments[experiment_id]
        assert experiment.status.value == "paused"

    def test_experiment_results_generation(self, experiment_service):
        """Test experiment results generation."""
        experiment_id = "trial_length_2024"
        
        results = experiment_service.get_experiment_results(experiment_id)
        
        assert "experiment" in results
        assert "variants" in results
        assert "results" in results
        assert "guardrail_violations" in results
        assert "statistical_significance" in results
        assert "recommendation" in results
        
        # Check experiment details
        exp_info = results["experiment"]
        assert exp_info["id"] == experiment_id
        assert exp_info["type"] == "trial_length"


class TestIntegrationWorkflows:
    """Test complete monetization workflows."""

    @pytest.fixture
    def services(self):
        """Create all monetization services."""
        billing_service = BillingService()
        return {
            "billing": billing_service,
            "entitlement": EntitlementService(billing_service),
            "paywall": PaywallService(),
            "experiment": ExperimentService()
        }

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    def test_complete_upgrade_workflow(self, services, user_id):
        """Test complete user upgrade workflow."""
        billing = services["billing"]
        entitlement = services["entitlement"]
        paywall = services["paywall"]
        
        # 1. Start with free user
        free_subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            price_cents=0
        )
        billing.subscriptions[user_id] = free_subscription
        billing.usage_trackers[user_id] = UsageTracker(
            user_id=user_id,
            subscription_id=free_subscription.id,
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(days=30)
        )
        
        # 2. Check feature access (should be limited)
        access = entitlement.check_feature_access(user_id, FeatureFlag.ADAPTIVE_PLANNING)
        assert access["has_access"] == False
        assert access["upgrade_required"] == True
        
        # 3. Get paywall config
        paywall_config = paywall.get_paywall_config(
            user_id, SubscriptionTier.FREE, PaywallTrigger.PLAN_GENERATION
        )
        assert len(paywall_config.offers) > 0
        
        # 4. Simulate upgrade to Plus
        plus_subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.PLUS,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            price_cents=1299
        )
        billing.subscriptions[user_id] = plus_subscription
        
        # 5. Check feature access after upgrade
        entitlement.cache.invalidate(user_id)  # Clear cache
        new_access = entitlement.check_feature_access(user_id, FeatureFlag.ADAPTIVE_PLANNING)
        assert new_access["has_access"] == True
        assert new_access["tier"] == "plus"

    def test_experiment_driven_pricing(self, services, user_id):
        """Test experiment-driven pricing workflow."""
        experiment = services["experiment"]
        paywall = services["paywall"]
        
        # 1. Set up price test experiment
        experiment_id = "price_test_q4_2024"
        experiment.experiments[experiment_id].status = "active"
        
        # 2. Assign user to experiment
        variant_id = experiment.assign_user_to_experiment(user_id, experiment_id)
        assert variant_id is not None
        
        # 3. Get paywall config (should reflect experiment)
        paywall_config = paywall.get_paywall_config(
            user_id, SubscriptionTier.FREE, PaywallTrigger.PLAN_GENERATION
        )
        
        # 4. Check if pricing reflects experiment variant
        assert paywall_config.experiment_bucket == experiment_id
        
        # 5. Track experiment event
        experiment.track_experiment_event(
            user_id, experiment_id, "paywall_viewed"
        )

    def test_usage_limit_enforcement_workflow(self, services, user_id):
        """Test usage limit enforcement workflow."""
        billing = services["billing"]
        entitlement = services["entitlement"]
        
        # Create free user with usage tracker
        subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.MONTHLY,
            price_cents=0
        )
        billing.subscriptions[user_id] = subscription
        billing.usage_trackers[user_id] = UsageTracker(
            user_id=user_id,
            subscription_id=subscription.id,
            period_start=datetime.now(),
            period_end=datetime.now() + timedelta(days=30)
        )
        
        # Use up free tier limits
        tracker = billing.usage_trackers[user_id]
        tracker.increment_usage(FeatureFlag.BASIC_MEAL_PLANS, 1)  # Hit limit
        tracker.increment_usage(FeatureFlag.SMS_NUDGES, 3)  # Hit limit
        
        # Check that further usage is blocked
        meal_plan_check = entitlement.check_usage_limit(
            user_id, FeatureFlag.BASIC_MEAL_PLANS, 1
        )
        assert meal_plan_check["has_access"] == False
        
        sms_check = entitlement.check_usage_limit(
            user_id, FeatureFlag.SMS_NUDGES, 1
        )
        assert sms_check["has_access"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
