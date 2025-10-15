"""Example: Admin interface for feature flag management."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

from packages.shared.feature_flags import (
    FeatureFlagService,
    FlagAdminService,
    FlagLifecycleManager,
    FlagCleanupService,
    FeatureFlagDefinition,
    FlagVariant,
    FlagStatus,
    FlagCleanupRule,
    TargetingRule,
    FlagAuditEvent,
)


async def admin_interface_demo():
    """Demonstrate administrative features for feature flags."""
    
    print("🔧 Feature Flag Admin Interface Demo")
    print("=" * 45)
    
    # Initialize services
    flag_service = FeatureFlagService()
    admin_service = FlagAdminService(flag_service)
    lifecycle_manager = FlagLifecycleManager(admin_service)
    cleanup_service = FlagCleanupService(admin_service, lifecycle_manager)
    
    # Add admin users
    admin_service.add_admin_user("admin@ainutritionist.com")
    admin_service.add_admin_user("product@ainutritionist.com")
    
    print("✅ Admin services initialized")
    print(f"   Admin users: {list(admin_service._admin_users)}")
    
    # Create some feature flags
    demo_flags = [
        FeatureFlagDefinition(
            key="experimental_feature",
            name="Experimental Feature",
            description="A new experimental feature for testing",
            status=FlagStatus.INACTIVE,
            variants=[
                FlagVariant(key="off", value=False),
                FlagVariant(key="on", value=True),
            ],
            default_variant="off",
            fallback_variant="off",
            created_by="admin@ainutritionist.com",
            tags=["experimental", "beta"],
        ),
        FeatureFlagDefinition(
            key="legacy_feature",
            name="Legacy Feature",
            description="Old feature that should be removed",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="off", value=False),
                FlagVariant(key="on", value=True),
            ],
            default_variant="on",
            fallback_variant="on",
            created_by="admin@ainutritionist.com",
            created_at=datetime.utcnow() - timedelta(days=120),  # Old flag
            tags=["legacy", "deprecated"],
        ),
        FeatureFlagDefinition(
            key="production_feature",
            name="Production Feature",
            description="A stable production feature",
            status=FlagStatus.ACTIVE,
            variants=[
                FlagVariant(key="off", value=False),
                FlagVariant(key="on", value=True),
            ],
            default_variant="on",
            fallback_variant="on",
            created_by="product@ainutritionist.com",
            tags=["production", "stable"],
        ),
    ]
    
    # Create flags through admin service
    print("\n📋 Creating flags through admin interface:")
    print("-" * 40)
    
    for flag in demo_flags:
        created_flag = await admin_service.create_flag(
            flag,
            "admin@ainutritionist.com",
            f"Created {flag.name} for demo"
        )
        print(f"✅ Created: {created_flag.key} ({created_flag.status})")
    
    # Demonstrate flag management operations
    print("\n🔄 Flag Management Operations:")
    print("-" * 35)
    
    # Toggle a flag
    new_status = await admin_service.toggle_flag(
        "experimental_feature",
        "admin@ainutritionist.com",
        "Enabling for testing"
    )
    print(f"📱 Toggled experimental_feature to: {new_status}")
    
    # Update flag with targeting rules
    targeting_rule = TargetingRule(
        name="Premium Users Only",
        conditions=[
            {
                "attribute": "subscription_tier",
                "operator": "equals",
                "value": "premium"
            }
        ],
        variant="on",
        percentage=100.0,
        priority=10,
    )
    
    await admin_service.update_flag(
        "experimental_feature",
        {
            "targeting_rules": [targeting_rule],
            "description": "Experimental feature with premium user targeting"
        },
        "product@ainutritionist.com",
        "Added targeting rules for premium users"
    )
    print("🎯 Added targeting rules to experimental_feature")
    
    # Demonstrate emergency kill switch
    await admin_service.enable_kill_switch(
        "experimental_feature",
        "admin@ainutritionist.com",
        "Bug reported in production - emergency disable"
    )
    print("🚨 Emergency kill switch enabled for experimental_feature")
    
    # Disable kill switch after "fix"
    await asyncio.sleep(1)  # Simulate time
    await admin_service.disable_kill_switch(
        "experimental_feature",
        "admin@ainutritionist.com",
        "Bug fixed, re-enabling feature"
    )
    print("✅ Kill switch disabled for experimental_feature")
    
    # Bulk update multiple flags
    bulk_updates = {
        "legacy_feature": {"status": FlagStatus.ARCHIVED},
        "production_feature": {"tags": ["production", "stable", "core"]},
    }
    
    results = await admin_service.bulk_update_flags(
        bulk_updates,
        "admin@ainutritionist.com",
        "Monthly flag maintenance"
    )
    print(f"📦 Bulk update results: {results}")
    
    # Get audit history
    print("\n📜 Audit History:")
    print("-" * 20)
    
    for flag_key in ["experimental_feature", "legacy_feature"]:
        history = await admin_service.get_flag_audit_history(flag_key, limit=3)
        print(f"\n{flag_key}:")
        for event in history:
            print(f"  {event.timestamp.strftime('%H:%M:%S')} - {event.event_type} by {event.user_id}")
            if event.reason:
                print(f"    Reason: {event.reason}")


async def lifecycle_management_demo():
    """Demonstrate feature flag lifecycle management."""
    
    print("\n♻️  Feature Flag Lifecycle Management")
    print("=" * 45)
    
    flag_service = FeatureFlagService()
    admin_service = FlagAdminService(flag_service)
    lifecycle_manager = FlagLifecycleManager(admin_service)
    
    admin_service.add_admin_user("system@ainutritionist.com")
    
    # Create flags with different ages for lifecycle testing
    test_flags = [
        FeatureFlagDefinition(
            key="new_feature",
            name="New Feature",
            description="Recently created feature",
            status=FlagStatus.ACTIVE,
            variants=[FlagVariant(key="off", value=False), FlagVariant(key="on", value=True)],
            default_variant="off",
            fallback_variant="off",
            created_by="system@ainutritionist.com",
            created_at=datetime.utcnow() - timedelta(days=5),
            tags=["new"],
        ),
        FeatureFlagDefinition(
            key="old_inactive_feature",
            name="Old Inactive Feature",
            description="Old feature that's been inactive",
            status=FlagStatus.INACTIVE,
            variants=[FlagVariant(key="off", value=False), FlagVariant(key="on", value=True)],
            default_variant="off",
            fallback_variant="off",
            created_by="system@ainutritionist.com",
            created_at=datetime.utcnow() - timedelta(days=45),
            tags=["old", "unused"],
        ),
        FeatureFlagDefinition(
            key="experimental_old",
            name="Old Experimental Feature",
            description="Experimental feature that's been around too long",
            status=FlagStatus.ACTIVE,
            variants=[FlagVariant(key="off", value=False), FlagVariant(key="on", value=True)],
            default_variant="off",
            fallback_variant="off",
            created_by="system@ainutritionist.com",
            created_at=datetime.utcnow() - timedelta(days=60),
            tags=["experimental"],
        ),
    ]
    
    for flag in test_flags:
        await admin_service.create_flag(flag, "system@ainutritionist.com", "Lifecycle test flag")
    
    print("✅ Created test flags for lifecycle management")
    
    # Add lifecycle rules
    lifecycle_manager.add_lifecycle_rule(
        name="Archive Old Inactive Flags",
        description="Archive flags that have been inactive for 30+ days",
        conditions={
            "age_days": 30,
            "status": "inactive",
        },
        actions={
            "archive": True,
        }
    )
    
    lifecycle_manager.add_lifecycle_rule(
        name="Deactivate Old Experimental",
        description="Deactivate experimental flags older than 45 days",
        conditions={
            "age_days": 45,
            "tags": ["experimental"],
        },
        actions={
            "deactivate": True,
        }
    )
    
    print("📋 Added lifecycle rules:")
    for rule in lifecycle_manager._lifecycle_rules:
        print(f"  - {rule['name']}: {rule['description']}")
    
    # Apply lifecycle rules
    print("\n🔄 Applying lifecycle rules...")
    results = await lifecycle_manager.check_lifecycle_rules("system@ainutritionist.com")
    
    print("Results:")
    for action in results["applied"]:
        print(f"  ✅ {action}")
    for error in results["failed"]:
        print(f"  ❌ {error}")


async def cleanup_automation_demo():
    """Demonstrate automated flag cleanup."""
    
    print("\n🧹 Automated Flag Cleanup Demo")
    print("=" * 35)
    
    flag_service = FeatureFlagService()
    admin_service = FlagAdminService(flag_service)
    lifecycle_manager = FlagLifecycleManager(admin_service)
    cleanup_service = FlagCleanupService(admin_service, lifecycle_manager)
    
    admin_service.add_admin_user("cleanup@ainutritionist.com")
    
    # Create cleanup rules
    cleanup_rules = [
        FlagCleanupRule(
            name="Archive Very Old Flags",
            description="Archive flags older than 90 days that are inactive",
            flag_age_days=90,
            flag_status=FlagStatus.INACTIVE,
            action="archive",
            notify_users=["admin@ainutritionist.com"],
            created_by="cleanup@ainutritionist.com",
        ),
        FlagCleanupRule(
            name="Notify About Deprecated Flags",
            description="Notify about deprecated flags",
            tags=["deprecated"],
            action="notify",
            notify_users=["product@ainutritionist.com"],
            created_by="cleanup@ainutritionist.com",
        ),
        FlagCleanupRule(
            name="Archive Legacy Features",
            description="Archive old legacy features",
            flag_age_days=120,
            tags=["legacy"],
            action="archive",
            notify_users=["admin@ainutritionist.com"],
            created_by="cleanup@ainutritionist.com",
        ),
    ]
    
    for rule in cleanup_rules:
        cleanup_service.add_cleanup_rule(rule)
    
    print("📋 Added cleanup rules:")
    for rule in cleanup_service._cleanup_rules:
        print(f"  - {rule.name}: {rule.description}")
    
    # Create test flags that would match cleanup rules
    old_flags = [
        FeatureFlagDefinition(
            key="very_old_inactive",
            name="Very Old Inactive Feature",
            description="Should be archived by cleanup",
            status=FlagStatus.INACTIVE,
            variants=[FlagVariant(key="off", value=False)],
            default_variant="off",
            fallback_variant="off",
            created_by="cleanup@ainutritionist.com",
            created_at=datetime.utcnow() - timedelta(days=100),
            tags=["old"],
        ),
        FeatureFlagDefinition(
            key="deprecated_feature",
            name="Deprecated Feature",
            description="Should trigger notification",
            status=FlagStatus.ACTIVE,
            variants=[FlagVariant(key="off", value=False)],
            default_variant="off",
            fallback_variant="off",
            created_by="cleanup@ainutritionist.com",
            created_at=datetime.utcnow() - timedelta(days=30),
            tags=["deprecated"],
        ),
    ]
    
    for flag in old_flags:
        await admin_service.create_flag(flag, "cleanup@ainutritionist.com", "Test flag for cleanup")
    
    print("✅ Created test flags for cleanup")
    
    # Run cleanup process
    print("\n🔄 Running cleanup process...")
    cleanup_results = await cleanup_service.run_cleanup("cleanup@ainutritionist.com")
    
    print("Cleanup Results:")
    print(f"  Started: {cleanup_results['started_at']}")
    print(f"  Rules processed: {cleanup_results['rules_processed']}")
    print(f"  Flags affected: {len(cleanup_results['flags_affected'])}")
    for flag in cleanup_results['flags_affected']:
        print(f"    - {flag}")
    print(f"  Notifications sent: {len(cleanup_results['notifications_sent'])}")
    for notification in cleanup_results['notifications_sent']:
        print(f"    - {notification}")
    print(f"  Errors: {len(cleanup_results['errors'])}")
    for error in cleanup_results['errors']:
        print(f"    - {error}")


async def monitoring_integration_demo():
    """Demonstrate monitoring integration with admin features."""
    
    print("\n📊 Monitoring Integration Demo")
    print("=" * 35)
    
    from packages.shared.feature_flags import FlagMonitoringService, FlagEventLogger
    
    flag_service = FeatureFlagService()
    admin_service = FlagAdminService(flag_service)
    monitoring_service = FlagMonitoringService(flag_service)
    
    admin_service.add_admin_user("monitor@ainutritionist.com")
    
    # Create a test flag
    test_flag = FeatureFlagDefinition(
        key="monitored_feature",
        name="Monitored Feature",
        description="Feature with monitoring enabled",
        status=FlagStatus.ACTIVE,
        variants=[
            FlagVariant(key="off", value=False, percentage=70),
            FlagVariant(key="on", value=True, percentage=30),
        ],
        default_variant="off",
        fallback_variant="off",
        created_by="monitor@ainutritionist.com",
        tags=["monitored"],
    )
    
    await admin_service.create_flag(test_flag, "monitor@ainutritionist.com", "Test flag for monitoring")
    print("✅ Created monitored feature flag")
    
    # Simulate some flag evaluations with monitoring
    from packages.shared.feature_flags.models import FlagContext, FlagEvaluationResult
    
    print("\n📈 Simulating flag evaluations...")
    
    for i in range(50):
        context = FlagContext(
            user_id=f"user_{i:03d}",
            subscription_tier="premium" if i % 3 == 0 else "free",
        )
        
        # Simulate evaluation
        result = await flag_service.evaluate_flag("monitored_feature", context)
        
        # Record metrics
        await monitoring_service.record_evaluation(
            result, context, latency_ms=15.0 + (i % 10), cache_hit=(i % 3 == 0)
        )
    
    print("✅ Simulated 50 flag evaluations")
    
    # Get monitoring reports
    flag_metrics = await monitoring_service.get_flag_metrics("monitored_feature")
    if flag_metrics:
        print(f"\n📊 Flag Metrics for 'monitored_feature':")
        print(f"  Evaluations: {flag_metrics.evaluation_count}")
        print(f"  Unique users: {flag_metrics.unique_user_count}")
        print(f"  Avg latency: {flag_metrics.avg_latency_ms:.2f}ms")
        print(f"  Cache hit rate: {flag_metrics.cache_hit_rate:.2%}")
        print(f"  Variant distribution: {flag_metrics.variant_counts}")
    
    # Get performance report
    perf_report = await monitoring_service.get_performance_report()
    print(f"\n⚡ Performance Report:")
    print(f"  Total evaluations: {perf_report['summary']['total_evaluations']}")
    print(f"  Total flags: {perf_report['summary']['total_flags']}")
    print(f"  Avg latency: {perf_report['summary']['avg_latency_ms']:.2f}ms")
    print(f"  Recommendations: {len(perf_report['recommendations'])}")
    for rec in perf_report['recommendations']:
        print(f"    - {rec}")
    
    # Stop monitoring
    monitoring_service.stop_monitoring()
    print("🔄 Monitoring stopped")


async def main():
    """Run all admin demo examples."""
    
    print("🎛️  Feature Flag Administration Demo")
    print("=" * 45)
    
    try:
        await admin_interface_demo()
        await lifecycle_management_demo()
        await cleanup_automation_demo()
        await monitoring_integration_demo()
        
        print("\n🎉 All admin demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running admin demos: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
