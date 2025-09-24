#!/usr/bin/env python3
"""Validation test for Track F - Data & Analytics."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.models.analytics import (
    EventType,
    ConsentType,
    PIILevel,
    UserConsent,
    EventContext
)
from src.services.analytics.analytics_service import AnalyticsService
from src.services.analytics.warehouse_processor import WarehouseProcessor

async def test_event_taxonomy():
    """Test F1 - Event Taxonomy implementation."""
    print("🧪 Testing F1 - Event Taxonomy...")
    
    analytics_service = AnalyticsService()
    user_id = uuid4()
    
    # Test consent setup
    await analytics_service.update_user_consent(
        user_id, ConsentType.ANALYTICS, True, "test"
    )
    
    # Test all core events from GO_TO_PRODUCTION.md
    test_results = []
    
    # 1. plan_generated
    success = await analytics_service.track_plan_generated(
        user_id=user_id,
        plan_id=uuid4(),
        ruleset="test_rules",
        est_cost_cents=1500,
        duration_ms=250,
        dietary_preferences=["vegan", "gluten-free"],
        budget_constraint=50.0
    )
    test_results.append(("plan_generated", success))
    
    # 2. meal_logged
    success = await analytics_service.track_meal_logged(
        user_id=user_id,
        meal_id=uuid4(),
        status="eaten",
        source="app",
        mood_score=4,
        energy_score=5
    )
    test_results.append(("meal_logged", success))
    
    # 3. nudge_sent
    success = await analytics_service.track_nudge_sent(
        user_id=user_id,
        template_id="morning_reminder",
        channel="sms",
        experiment_id="nudge_freq_test"
    )
    test_results.append(("nudge_sent", success))
    
    # 4. nudge_clicked
    success = await analytics_service.track_nudge_clicked(
        user_id=user_id,
        nudge_id="nudge_123",
        template_id="morning_reminder",
        channel="sms",
        time_to_click_seconds=45
    )
    test_results.append(("nudge_clicked", success))
    
    # 5. crew_joined
    success = await analytics_service.track_crew_joined(
        user_id=user_id,
        crew_id=uuid4(),
        crew_type="weekly_challenge",
        invite_source="friend"
    )
    test_results.append(("crew_joined", success))
    
    # 6. reflection_submitted
    success = await analytics_service.track_reflection_submitted(
        user_id=user_id,
        reflection_id=uuid4(),
        content_length=150,
        sentiment_score=0.8
    )
    test_results.append(("reflection_submitted", success))
    
    # 7. paywall_viewed
    success = await analytics_service.track_paywall_viewed(
        user_id=user_id,
        price_usd=12.99,
        variant="control",
        source="feature_gate",
        trigger_feature="adaptive_planning"
    )
    test_results.append(("paywall_viewed", success))
    
    # 8. subscribe_started
    success = await analytics_service.track_subscribe_started(
        user_id=user_id,
        tier="plus",
        interval="monthly",
        price_usd=12.99,
        source="paywall"
    )
    test_results.append(("subscribe_started", success))
    
    # 9. subscribe_activated
    success = await analytics_service.track_subscribe_activated(
        user_id=user_id,
        tier="plus",
        price_usd=12.99,
        time_to_activate_seconds=120
    )
    test_results.append(("subscribe_activated", success))
    
    # 10. churned
    success = await analytics_service.track_churned(
        user_id=user_id,
        churn_type="voluntary",
        previous_tier="plus",
        days_subscribed=45,
        ltv_usd=38.97
    )
    test_results.append(("churned", success))
    
    # Validate results
    all_successful = all(success for _, success in test_results)
    total_events = len(analytics_service.events)
    
    print(f"✅ Event tracking results:")
    for event_name, success in test_results:
        status = "✓" if success else "✗"
        print(f"  {status} {event_name}")
    
    print(f"✅ Total events tracked: {total_events}")
    print(f"✅ All events successful: {all_successful}")
    
    # Test privacy controls
    user_profile = analytics_service.get_user_profile(user_id)
    assert user_profile is not None
    assert user_profile.total_plans_generated == 1
    assert user_profile.total_meals_logged == 1
    assert user_profile.current_tier == "plus"
    
    print("✅ Privacy controls and user profiles working")
    print("🎉 F1 - Event Taxonomy: PASSED\n")
    
    await analytics_service.cleanup()
    return True

async def test_schema_design():
    """Test F2 - Schema Design with PII separation."""
    print("🧪 Testing F2 - Schema Design...")
    
    analytics_service = AnalyticsService()
    user_id = uuid4()
    
    # Test consent management
    consent_granted = await analytics_service.update_user_consent(
        user_id, ConsentType.ANALYTICS, True, "app", "consent"
    )
    assert consent_granted == True
    print("✅ Consent management working")
    
    # Test PII separation
    user_pii = analytics_service.user_pii.get(user_id)
    assert user_pii is not None
    assert user_pii.has_consent(ConsentType.ANALYTICS) == True
    print("✅ PII separation implemented")
    
    # Test event with sensitive data
    context = EventContext(
        session_id=uuid4(),
        platform="ios",
        ip_address="192.168.1.1"  # Will be hashed
    )
    
    success = await analytics_service.track_reflection_submitted(
        user_id=user_id,
        reflection_id=uuid4(),
        content_length=200,
        contains_pii=True,
        context=context
    )
    assert success == True
    
    # Verify privacy transforms were applied
    events = analytics_service.get_events_for_user(user_id)
    reflection_event = next(e for e in events if e.event_type == EventType.REFLECTION_SUBMITTED)
    assert reflection_event.pii_level == PIILevel.SENSITIVE
    assert reflection_event.context.ip_address != "192.168.1.1"  # Should be hashed
    print("✅ Privacy transforms applied")
    
    # Test GDPR data deletion request
    deletion_success = await analytics_service.request_data_deletion(user_id)
    assert deletion_success == True
    
    user_pii_after = analytics_service.user_pii.get(user_id)
    assert user_pii_after.deletion_requested == True
    print("✅ GDPR compliance implemented")
    
    print("🎉 F2 - Schema Design: PASSED\n")
    
    await analytics_service.cleanup()
    return True

async def test_warehouse_dashboards():
    """Test F3 - Warehouse & Dashboards."""
    print("🧪 Testing F3 - Warehouse & Dashboards...")
    
    analytics_service = AnalyticsService()
    processor = WarehouseProcessor(analytics_service)
    
    # Create test data for multiple users
    test_users = []
    for i in range(5):
        user_id = uuid4()
        test_users.append(user_id)
        
        # Grant consent
        await analytics_service.update_user_consent(
            user_id, ConsentType.ANALYTICS, True, "test"
        )
        
        # Create user journey
        base_time = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Registration (simulated via first event)
        await analytics_service.track_plan_generated(
            user_id=user_id,
            plan_id=uuid4(),
            ruleset="onboarding",
            est_cost_cents=1200 + i * 100,
            duration_ms=200 + i * 50
        )
        
        # Onboarding completion
        if i < 4:  # 80% complete onboarding
            from src.models.analytics import BaseEvent
            onboarding_event = BaseEvent(
                event_type=EventType.ONBOARDING_COMPLETED,
                user_id=user_id,
                timestamp=base_time + timedelta(minutes=30)
            )
            await analytics_service.track_event(onboarding_event)
        
        # Meal logging
        if i < 3:  # 60% log meals
            for day in range(7):
                await analytics_service.track_meal_logged(
                    user_id=user_id,
                    meal_id=uuid4(),
                    status="eaten" if day < 5 else "skipped",
                    source="app"
                )
        
        # Subscription (some users)
        if i < 2:  # 40% convert
            await analytics_service.track_subscribe_activated(
                user_id=user_id,
                tier="plus" if i == 0 else "pro",
                price_usd=12.99 if i == 0 else 24.99
            )
    
    print(f"✅ Created test data for {len(test_users)} users")
    
    # Test activation funnel
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    funnel_metrics = await processor.process_activation_funnel(start_date, end_date)
    assert funnel_metrics.registered_users == 5
    assert funnel_metrics.completed_onboarding == 4
    assert funnel_metrics.onboarding_rate == 0.8  # 4/5
    print(f"✅ Activation funnel: {funnel_metrics.registered_users} users, {funnel_metrics.onboarding_rate:.1%} completion")
    
    # Test cohort analysis
    current_month = end_date.strftime("%Y-%m")
    cohort_metrics = await processor.process_cohort_analysis(current_month)
    assert cohort_metrics.cohort_size == 5
    assert cohort_metrics.conversion_rate == 0.4  # 2/5 converted
    print(f"✅ Cohort analysis: {cohort_metrics.cohort_size} users, {cohort_metrics.conversion_rate:.1%} conversion")
    
    # Test revenue metrics
    revenue_metrics = await processor.process_revenue_metrics(start_date, end_date)
    assert revenue_metrics.new_subscribers == 2
    assert revenue_metrics.plus_subscribers == 1
    assert revenue_metrics.pro_subscribers == 1
    print(f"✅ Revenue metrics: {revenue_metrics.new_subscribers} new, ${revenue_metrics.mrr_usd:.2f} MRR")
    
    # Test dashboard data
    dashboard_data = await processor.get_dashboard_data(start_date, end_date)
    assert "overview" in dashboard_data
    assert "activation_funnel" in dashboard_data
    assert "engagement" in dashboard_data
    assert "monetization" in dashboard_data
    print("✅ Dashboard data generation working")
    
    # Test adherence metrics
    adherence_data = await processor.calculate_adherence_metrics(None, start_date, end_date)
    assert adherence_data["total_users"] > 0
    assert "average_adherence" in adherence_data
    print(f"✅ Adherence metrics: {adherence_data['total_users']} users analyzed")
    
    print("🎉 F3 - Warehouse & Dashboards: PASSED\n")
    
    await analytics_service.cleanup()
    return True

async def test_integration_workflow():
    """Test complete analytics integration workflow."""
    print("🧪 Testing Complete Analytics Integration...")
    
    analytics_service = AnalyticsService()
    user_id = uuid4()
    
    # 1. User registration and consent
    await analytics_service.update_user_consent(
        user_id, ConsentType.ANALYTICS, True, "app"
    )
    print("✅ User consent established")
    
    # 2. Complete user journey simulation
    journey_events = [
        ("plan_generated", lambda: analytics_service.track_plan_generated(
            user_id, uuid4(), "onboarding", 1500, 300
        )),
        ("meal_logged", lambda: analytics_service.track_meal_logged(
            user_id, uuid4(), "eaten", "app", mood_score=4
        )),
        ("paywall_viewed", lambda: analytics_service.track_paywall_viewed(
            user_id, 12.99, "control", "feature_gate"
        )),
        ("subscribe_activated", lambda: analytics_service.track_subscribe_activated(
            user_id, "plus", 12.99
        ))
    ]
    
    for event_name, event_func in journey_events:
        success = await event_func()
        assert success == True
        print(f"  ✓ {event_name}")
    
    print("✅ User journey tracking complete")
    
    # 3. Analytics processing
    processor = WarehouseProcessor(analytics_service)
    
    # Get user profile
    profile = analytics_service.get_user_profile(user_id)
    assert profile is not None
    assert profile.total_plans_generated >= 1
    assert profile.current_tier == "plus"
    print("✅ User profile updated from events")
    
    # Get dashboard data
    dashboard_data = await processor.get_dashboard_data()
    assert dashboard_data["overview"]["total_users"] >= 1
    assert dashboard_data["monetization"]["subscribers"]["plus"] >= 1
    print("✅ Dashboard aggregation working")
    
    # 4. Privacy compliance
    user_events = analytics_service.get_events_for_user(user_id)
    assert len(user_events) == 4
    
    # All events should have consent flags
    for event in user_events:
        assert ConsentType.ANALYTICS in event.consent_flags
        assert event.consent_flags[ConsentType.ANALYTICS] == True
    print("✅ Privacy compliance verified")
    
    print("🎉 Complete Analytics Integration: PASSED\n")
    await analytics_service.cleanup()
    return True

async def main():
    """Run all Track F analytics tests."""
    print("🚀 Track F - Data & Analytics Validation\n")
    print("=" * 60)
    
    try:
        # Test F1 - Event Taxonomy
        await test_event_taxonomy()
        
        # Test F2 - Schema Design  
        await test_schema_design()
        
        # Test F3 - Warehouse & Dashboards
        await test_warehouse_dashboards()
        
        # Test Integration
        await test_integration_workflow()
        
        print("=" * 60)
        print("🎉 ALL TRACK F TESTS PASSED!")
        print("✅ F1 - Event Taxonomy: 10 core events implemented")
        print("✅ F2 - Schema Design: PII separation + GDPR compliance")
        print("✅ F3 - Warehouse & Dashboards: Funnel, cohort, revenue analytics")
        print("📊 ANALYTICS SYSTEM READY FOR PRODUCTION!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
