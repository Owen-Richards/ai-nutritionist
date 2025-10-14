"""Example: Basic feature flag usage with the AI Nutritionist application."""

import asyncio
from datetime import datetime
from typing import Dict, Any

from packages.shared.feature_flags import (
    FeatureFlagService,
    LaunchDarklyService,
    FeatureFlagClient,
    FlagContext,
    FeatureFlagDefinition,
    FlagVariant,
    FlagStatus,
    LaunchDarklyConfig,
    CacheConfig,
)


async def basic_flag_usage_example():
    """Demonstrate basic feature flag operations."""
    
    print("🚀 Feature Flag Basic Usage Example")
    print("=" * 50)
    
    # Create a basic feature flag service
    cache_config = CacheConfig(
        ttl_seconds=300,
        enable_local_cache=True,
        enable_distributed_cache=False,
    )
    
    service = FeatureFlagService(cache_config=cache_config)
    client = FeatureFlagClient(service)
    
    # Define a feature flag for new meal planning algorithm
    meal_planning_flag = FeatureFlagDefinition(
        key="new_meal_planning_algorithm",
        name="New Meal Planning Algorithm",
        description="Enable the new AI-powered meal planning algorithm",
        status=FlagStatus.ACTIVE,
        variants=[
            FlagVariant(
                key="control",
                name="Control",
                value=False,
                description="Use existing meal planning algorithm",
                percentage=50.0,
                is_control=True,
            ),
            FlagVariant(
                key="treatment",
                name="Treatment",
                value=True,
                description="Use new AI-powered algorithm",
                percentage=50.0,
            ),
        ],
        default_variant="control",
        fallback_variant="control",
        created_by="admin@ainutritionist.com",
        environment="development",
        tags=["meal-planning", "ai", "algorithm"],
    )
    
    # Register the flag
    await service.register_flag(meal_planning_flag)
    print(f"✅ Registered flag: {meal_planning_flag.key}")
    
    # Create user contexts for testing
    contexts = [
        FlagContext(
            user_id="user_123",
            subscription_tier="premium",
            country="US",
            user_segments=["power_user"],
            custom_attributes={"signup_date": "2024-01-15"},
        ),
        FlagContext(
            user_id="user_456",
            subscription_tier="free",
            country="CA",
            user_segments=["new_user"],
            custom_attributes={"signup_date": "2024-10-01"},
        ),
        FlagContext(
            user_id="user_789",
            subscription_tier="enterprise",
            country="UK",
            user_segments=["enterprise"],
            custom_attributes={"company_size": "large"},
        ),
    ]
    
    # Evaluate flag for different users
    print("\n📊 Flag Evaluations:")
    print("-" * 30)
    
    for context in contexts:
        # Check if flag is enabled
        is_enabled = await client.is_enabled(
            "new_meal_planning_algorithm",
            context
        )
        
        # Get detailed evaluation
        result = await client.evaluate(
            "new_meal_planning_algorithm",
            context
        )
        
        print(f"User: {context.user_id}")
        print(f"  Tier: {context.subscription_tier}")
        print(f"  Enabled: {is_enabled}")
        print(f"  Variant: {result.variant_key}")
        print(f"  Value: {result.value}")
        print(f"  Reason: {result.reason}")
        print()
    
    # Demonstrate batch evaluation
    print("🔄 Batch Evaluation:")
    print("-" * 20)
    
    flag_keys = ["new_meal_planning_algorithm"]
    context = contexts[0]
    
    batch_results = await client.evaluate_all(flag_keys, context)
    for flag_key, result in batch_results.items():
        print(f"Flag: {flag_key}")
        print(f"  Result: {result.value} ({result.variant_key})")
    
    print("\n✨ Basic usage example completed!")


async def advanced_targeting_example():
    """Demonstrate advanced targeting and rollout strategies."""
    
    print("\n🎯 Advanced Targeting Example")
    print("=" * 40)
    
    service = FeatureFlagService()
    client = FeatureFlagClient(service)
    
    # Define a feature flag with advanced targeting for fitness integration
    from packages.shared.feature_flags.models import TargetingRule, RolloutStrategy, FlagRolloutRule
    
    fitness_integration_flag = FeatureFlagDefinition(
        key="fitness_integration_v2",
        name="Fitness Integration V2",
        description="Enable new fitness data integration features",
        status=FlagStatus.ACTIVE,
        variants=[
            FlagVariant(key="off", value=False, percentage=0),
            FlagVariant(key="basic", value="basic", percentage=40),
            FlagVariant(key="advanced", value="advanced", percentage=60),
        ],
        default_variant="off",
        fallback_variant="off",
        targeting_rules=[
            TargetingRule(
                name="Premium Users Early Access",
                conditions=[
                    {
                        "attribute": "subscription_tier",
                        "operator": "in",
                        "value": ["premium", "enterprise"]
                    }
                ],
                variant="advanced",
                percentage=100.0,
                priority=10,
            ),
            TargetingRule(
                name="Power Users Basic Access",
                conditions=[
                    {
                        "attribute": "user_segments",
                        "operator": "contains",
                        "value": "power_user"
                    }
                ],
                variant="basic",
                percentage=80.0,
                priority=5,
            ),
        ],
        rollout_rules=[
            FlagRolloutRule(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=25.0,  # 25% rollout for remaining users
            )
        ],
        created_by="product@ainutritionist.com",
        environment="production",
        tags=["fitness", "integration", "v2"],
    )
    
    await service.register_flag(fitness_integration_flag)
    print(f"✅ Registered advanced flag: {fitness_integration_flag.key}")
    
    # Test different user types
    test_users = [
        {
            "name": "Premium User",
            "context": FlagContext(
                user_id="premium_user_001",
                subscription_tier="premium",
                user_segments=["power_user"],
            ),
            "expected": "advanced"
        },
        {
            "name": "Free Power User",
            "context": FlagContext(
                user_id="free_user_002",
                subscription_tier="free",
                user_segments=["power_user"],
            ),
            "expected": "basic (80% chance)"
        },
        {
            "name": "Regular Free User",
            "context": FlagContext(
                user_id="free_user_003",
                subscription_tier="free",
                user_segments=["regular"],
            ),
            "expected": "25% rollout chance"
        },
    ]
    
    print("\n🧪 Targeting Test Results:")
    print("-" * 25)
    
    for user in test_users:
        result = await client.evaluate(fitness_integration_flag.key, user["context"])
        print(f"User: {user['name']}")
        print(f"  Expected: {user['expected']}")
        print(f"  Actual: {result.variant_key} ({result.value})")
        print(f"  Reason: {result.reason}")
        print()


async def launchdarkly_integration_example():
    """Demonstrate LaunchDarkly integration (requires API key)."""
    
    print("\n🚀 LaunchDarkly Integration Example")
    print("=" * 40)
    
    # Note: This requires a valid LaunchDarkly SDK key
    # For demo purposes, we'll show the setup
    
    try:
        # Configure LaunchDarkly
        ld_config = LaunchDarklyConfig(
            sdk_key="sdk-your-key-here",  # Replace with actual key
            environment="development",
            cache_ttl_seconds=300,
            send_events=True,
        )
        
        # Create LaunchDarkly service
        # ld_service = LaunchDarklyService(ld_config)
        # ld_client = LaunchDarklyClient(ld_config)
        
        print("⚠️  LaunchDarkly integration configured")
        print("   (Requires valid SDK key to run)")
        
        # Example usage that would work with valid credentials:
        example_context = FlagContext(
            user_id="demo_user",
            subscription_tier="premium",
            country="US",
            custom_attributes={
                "beta_user": True,
                "feature_requests": 5,
            }
        )
        
        print(f"\nExample context: {example_context.user_id}")
        print("Would evaluate flags against LaunchDarkly...")
        
        # Example operations:
        # is_enabled = await ld_client.is_enabled("my-flag", example_context)
        # variant = await ld_client.get_variant("ab-test-flag", example_context)
        
    except ImportError:
        print("⚠️  LaunchDarkly SDK not installed")
        print("   Install with: pip install launchdarkly-server-sdk")


async def performance_optimization_example():
    """Demonstrate performance optimization techniques."""
    
    print("\n⚡ Performance Optimization Example")
    print("=" * 40)
    
    from packages.shared.feature_flags import PerformanceOptimizedClient, MemoryCache
    
    # Create optimized service with caching
    cache_config = CacheConfig(
        ttl_seconds=60,  # Short TTL for faster updates
        enable_local_cache=True,
        max_size=1000,
    )
    
    service = FeatureFlagService(cache_config=cache_config)
    
    # Create performance-optimized client
    perf_client = PerformanceOptimizedClient(
        service=service,
        preload_flags=["critical_feature", "ui_variant", "api_version"],
        cache_duration=30,  # 30-second local cache
    )
    
    print("✅ Performance-optimized client created")
    
    # Register some flags for testing
    test_flags = [
        FeatureFlagDefinition(
            key="critical_feature",
            name="Critical Feature",
            description="A critical feature for the app",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="off", value=False),
                FlagVariant(key="on", value=True),
            ],
            default_variant="on",
            fallback_variant="off",
            created_by="system",
        ),
        FeatureFlagDefinition(
            key="ui_variant",
            name="UI Variant",
            description="UI layout variant",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="classic", value="classic"),
                FlagVariant(key="modern", value="modern"),
            ],
            default_variant="classic",
            fallback_variant="classic",
            created_by="system",
        ),
    ]
    
    for flag in test_flags:
        await service.register_flag(flag)
    
    # Demonstrate fast evaluation
    import time
    
    user_id = "performance_test_user"
    
    # Time batch evaluation
    start_time = time.time()
    
    results = await perf_client.batch_is_enabled(
        ["critical_feature", "ui_variant"],
        user_id,
        use_cache=True,
    )
    
    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000
    
    print(f"\n⏱️  Batch evaluation results:")
    for flag_key, is_enabled in results.items():
        print(f"  {flag_key}: {is_enabled}")
    
    print(f"  Latency: {latency_ms:.2f}ms")
    
    # Show cache stats
    cache_stats = perf_client.get_cache_stats()
    print(f"\n📊 Cache stats: {cache_stats}")


async def a_b_testing_example():
    """Demonstrate A/B testing with feature flags."""
    
    print("\n🧪 A/B Testing Example")
    print("=" * 30)
    
    from packages.shared.feature_flags.models import ABTestConfiguration
    
    service = FeatureFlagService()
    client = FeatureFlagClient(service)
    
    # Create A/B test for onboarding flow
    ab_test_config = ABTestConfiguration(
        name="Onboarding Flow V2",
        description="Test new onboarding flow vs current",
        variants=[
            FlagVariant(
                key="control",
                name="Current Onboarding",
                value="current",
                percentage=50.0,
                is_control=True,
            ),
            FlagVariant(
                key="treatment",
                name="New Onboarding",
                value="new_flow",
                percentage=50.0,
            ),
        ],
        traffic_allocation=100.0,
        primary_metric="onboarding_completion_rate",
        secondary_metrics=["time_to_complete", "user_satisfaction"],
        minimum_sample_size=1000,
    )
    
    onboarding_flag = FeatureFlagDefinition(
        key="onboarding_flow_ab_test",
        name="Onboarding Flow A/B Test",
        description="A/B test for new onboarding flow",
        status=FlagStatus.ACTIVE,
        variants=ab_test_config.variants,
        default_variant="control",
        fallback_variant="control",
        ab_test=ab_test_config,
        created_by="product@ainutritionist.com",
        tags=["ab-test", "onboarding", "ux"],
    )
    
    await service.register_flag(onboarding_flag)
    print(f"✅ A/B test flag registered: {onboarding_flag.key}")
    
    # Simulate users going through the test
    print("\n👥 Simulating A/B test users:")
    print("-" * 25)
    
    variant_counts = {"control": 0, "treatment": 0}
    
    for i in range(10):
        context = FlagContext(
            user_id=f"test_user_{i:03d}",
            subscription_tier="free" if i % 3 == 0 else "premium",
            user_segments=["new_user"],
        )
        
        variant = await client.get_variant(onboarding_flag.key, context)
        variant_counts[variant] += 1
        
        print(f"User {i+1:2d}: {variant}")
    
    print(f"\n📈 Variant distribution:")
    for variant, count in variant_counts.items():
        percentage = (count / 10) * 100
        print(f"  {variant}: {count}/10 ({percentage}%)")


async def main():
    """Run all feature flag examples."""
    
    print("🎯 AI Nutritionist Feature Flag Examples")
    print("=" * 50)
    
    try:
        await basic_flag_usage_example()
        await advanced_targeting_example()
        await launchdarkly_integration_example()
        await performance_optimization_example()
        await a_b_testing_example()
        
        print("\n🎉 All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
