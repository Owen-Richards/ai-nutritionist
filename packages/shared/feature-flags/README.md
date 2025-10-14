# Feature Flag System for AI Nutritionist

A comprehensive feature flag system with LaunchDarkly integration for controlled rollouts, A/B testing, and gradual feature deployments.

## Features

### 🚀 Core Capabilities

- **Runtime Flag Evaluation**: Fast, cached flag evaluation with fallback values
- **Advanced Targeting**: User segments, percentage rollouts, and custom rules
- **A/B Testing**: Built-in experimentation framework with statistical analysis
- **Emergency Controls**: Kill switches and emergency fallback mechanisms
- **Performance Optimized**: Multi-level caching with Redis support

### 🎯 Targeting & Rollouts

- **User Segmentation**: Define custom user segments for targeted rollouts
- **Percentage Rollouts**: Gradual rollouts with consistent user bucketing
- **Rule-Based Targeting**: Complex targeting rules with multiple conditions
- **Scheduled Rollouts**: Time-based feature activation
- **Canary Deployments**: Safe feature releases with automatic rollback

### 📊 Management & Monitoring

- **Admin Interface**: Complete administrative control over flags
- **Audit Logging**: Full audit trail of all flag changes
- **Performance Metrics**: Detailed usage and performance analytics
- **Lifecycle Management**: Automated flag cleanup and archival
- **Health Monitoring**: Real-time system health and alerting

### 🔌 Integration

- **LaunchDarkly**: Full LaunchDarkly SDK integration
- **Web Frameworks**: FastAPI and Flask middleware
- **Caching**: Redis and in-memory caching support
- **Monitoring**: CloudWatch and custom metrics integration

## Quick Start

### Basic Usage

```python
from packages.shared.feature_flags import (
    FeatureFlagService,
    FeatureFlagClient,
    FlagContext,
    CacheConfig,
)

# Initialize service
cache_config = CacheConfig(
    ttl_seconds=300,
    enable_local_cache=True,
)

service = FeatureFlagService(cache_config=cache_config)
client = FeatureFlagClient(service)

# Create user context
context = FlagContext(
    user_id="user_123",
    subscription_tier="premium",
    country="US",
    user_segments=["power_user"],
)

# Evaluate flags
is_enabled = await client.is_enabled("new_feature", context)
variant = await client.get_variant("ui_experiment", context)
value = await client.get_value("config_setting", context, default="default_value")
```

### LaunchDarkly Integration

```python
from packages.shared.feature_flags import LaunchDarklyClient, LaunchDarklyConfig

# Configure LaunchDarkly
config = LaunchDarklyConfig(
    sdk_key="your-sdk-key",
    environment="production",
    send_events=True,
)

# Create client
client = LaunchDarklyClient(config)

# Use same API as basic client
is_enabled = await client.is_enabled("feature_key", context)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from packages.shared.feature_flags import (
    FastAPIFeatureFlagMiddleware,
    FeatureFlagDependency,
    flag_required,
)

app = FastAPI()

# Add middleware
middleware = FastAPIFeatureFlagMiddleware(flag_client)
app.middleware("http")(middleware)

# Use dependency injection
flag_dependency = FeatureFlagDependency(flag_client)

@app.get("/api/feature")
@flag_required("premium_feature")
async def premium_endpoint(
    flags: dict = Depends(flag_dependency),
):
    return {"message": "Premium feature enabled"}
```

## Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Flag Client   │    │  Flag Service    │    │   Cache Layer   │
│                 │───▶│                  │───▶│                 │
│ - Simple API    │    │ - Evaluation     │    │ - Memory Cache  │
│ - Context Mgmt  │    │ - Targeting      │    │ - Redis Cache   │
│ - Event Tracking│    │ - Fallbacks      │    │ - Multi-level   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌──────────────────┐            │
         │              │  LaunchDarkly    │            │
         └──────────────│   Integration    │────────────┘
                        │                  │
                        │ - SDK Wrapper    │
                        │ - Event Tracking │
                        │ - Real-time Sync │
                        └──────────────────┘
```

### Flag Evaluation Flow

```
User Request
     │
     ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Context   │───▶│    Cache     │───▶│ Evaluation  │
│ Extraction  │    │   Lookup     │    │   Engine    │
└─────────────┘    └──────────────┘    └─────────────┘
     │                     │                   │
     │              Cache Hit/Miss             │
     │                     │                   │
     ▼                     ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Targeting │    │   Fallback   │    │   Result    │
│    Rules    │    │   Provider   │    │   & Cache   │
└─────────────┘    └──────────────┘    └─────────────┘
```

## Configuration

### Environment Variables

```bash
# LaunchDarkly Configuration
LAUNCHDARKLY_SDK_KEY=sdk-your-key-here
LAUNCHDARKLY_ENVIRONMENT=production

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/1

# Feature Flag Settings
FF_CACHE_TTL_SECONDS=300
FF_ENABLE_METRICS=true
FF_LOG_LEVEL=INFO
```

### Feature Flag Definitions

```python
# Configuration file example
FEATURE_FLAGS = {
    "enhanced_meal_planning": {
        "name": "Enhanced Meal Planning",
        "description": "AI-powered meal planning algorithm",
        "variants": [
            {"key": "off", "value": False, "percentage": 30},
            {"key": "basic", "value": "basic", "percentage": 40},
            {"key": "advanced", "value": "advanced", "percentage": 30},
        ],
        "default_variant": "basic",
        "targeting_rules": [
            {
                "name": "Premium Users",
                "conditions": [
                    {"attribute": "subscription_tier", "operator": "equals", "value": "premium"}
                ],
                "variant": "advanced",
                "percentage": 100.0,
            }
        ],
        "tags": ["meal-planning", "ai", "premium"],
    }
}
```

## Use Cases

### 1. New Feature Rollouts

```python
# Gradual rollout of new meal planning algorithm
@app.post("/api/meal-plan")
async def generate_meal_plan(request, flags=Depends(flag_dependency)):
    algorithm = await flags["flag_client"].get_variant(
        "meal_planning_algorithm",
        flags["flag_context"],
        default="v1"
    )

    if algorithm == "v2":
        return await generate_ai_meal_plan(request)
    else:
        return await generate_standard_meal_plan(request)
```

### 2. A/B Testing

```python
# A/B test different onboarding flows
@feature_gate(
    "onboarding_flow",
    variants={
        "control": original_onboarding,
        "variant_a": simplified_onboarding,
        "variant_b": gamified_onboarding,
    }
)
async def onboarding_endpoint(request):
    # Automatically routed based on feature flag
    pass
```

### 3. Emergency Controls

```python
# Emergency kill switch for problematic features
admin_service = FlagAdminService(flag_service)

# Enable kill switch
await admin_service.enable_kill_switch(
    "problematic_feature",
    admin_user_id="admin@company.com",
    reason="Bug causing data corruption - emergency disable"
)
```

### 4. Performance Testing

```python
# Test different caching strategies
cache_strategy = await client.get_variant(
    "cache_strategy",
    context,
    default="standard"
)

if cache_strategy == "aggressive":
    cache_ttl = 3600  # 1 hour
elif cache_strategy == "moderate":
    cache_ttl = 300   # 5 minutes
else:
    cache_ttl = 60    # 1 minute
```

## Best Practices

### 1. Flag Naming

- Use descriptive, kebab-case names: `enhanced-meal-planning`
- Include component prefix: `api-v2-endpoints`
- Avoid negations: use `feature-enabled` not `feature-disabled`

### 2. Fallback Values

- Always provide safe fallback values
- Default to the most stable behavior
- Test fallback scenarios regularly

### 3. Context Enrichment

```python
context = FlagContext(
    user_id=user.id,
    subscription_tier=user.subscription.tier,
    country=user.profile.country,
    user_segments=determine_user_segments(user),
    custom_attributes={
        "signup_date": user.created_at.isoformat(),
        "feature_usage_score": calculate_usage_score(user),
    }
)
```

### 4. Performance Optimization

```python
# Use performance-optimized client for high-frequency calls
perf_client = PerformanceOptimizedClient(
    service=flag_service,
    preload_flags=["critical_feature", "ui_variant"],
    cache_duration=30,
)

# Batch evaluations when possible
results = await perf_client.batch_is_enabled(
    ["feature_a", "feature_b", "feature_c"],
    user_id,
    use_cache=True,
)
```

### 5. Monitoring & Alerting

```python
# Set up monitoring
monitoring_service = FlagMonitoringService(flag_service)

# Get performance insights
report = await monitoring_service.get_performance_report()
if report["performance_issues"]["slow_flags"]:
    # Alert on slow flags
    send_alert("Slow feature flags detected")
```

## Administrative Features

### Flag Lifecycle Management

```python
# Automated flag cleanup
cleanup_service = FlagCleanupService(admin_service, lifecycle_manager)

cleanup_service.add_cleanup_rule(FlagCleanupRule(
    name="Archive Old Experimental Flags",
    flag_age_days=90,
    tags=["experimental"],
    action="archive",
    notify_users=["product@company.com"],
))

# Run cleanup
results = await cleanup_service.run_cleanup("system@company.com")
```

### Audit & Compliance

```python
# Get audit history
history = await admin_service.get_flag_audit_history("critical_feature")
for event in history:
    print(f"{event.timestamp}: {event.event_type} by {event.user_id}")
    print(f"  Reason: {event.reason}")
```

## Testing

### Unit Tests

```python
import pytest
from packages.shared.feature_flags import FeatureFlagService, FlagContext

@pytest.mark.asyncio
async def test_flag_evaluation():
    service = FeatureFlagService()

    # Register test flag
    flag = FeatureFlagDefinition(
        key="test_flag",
        variants=[
            FlagVariant(key="off", value=False),
            FlagVariant(key="on", value=True),
        ],
        default_variant="off",
        fallback_variant="off",
    )
    await service.register_flag(flag)

    # Test evaluation
    context = FlagContext(user_id="test_user")
    result = await service.evaluate_flag("test_flag", context)

    assert result.flag_key == "test_flag"
    assert result.variant_key in ["off", "on"]
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_fastapi_integration():
    from fastapi.testclient import TestClient

    # Test with feature flag middleware
    with TestClient(app) as client:
        response = client.get(
            "/api/feature",
            headers={"X-User-ID": "test_user"}
        )
        assert response.status_code == 200
```

## Examples

See the `examples/feature-flags/` directory for complete examples:

- `basic_usage.py` - Basic feature flag operations
- `fastapi_integration.py` - FastAPI integration example
- `admin_interface.py` - Administrative features demo
- `meal_planning_integration.py` - Integration with meal planning service
- `launchdarkly_config.py` - LaunchDarkly configuration

## Performance

### Benchmarks

- **Local cache**: ~0.1ms average evaluation time
- **Redis cache**: ~2-5ms average evaluation time
- **LaunchDarkly**: ~10-20ms average evaluation time
- **Batch operations**: 10x faster for multiple flags

### Optimization Tips

1. **Use local caching** for frequently accessed flags
2. **Batch evaluations** when checking multiple flags
3. **Preload critical flags** in performance-optimized client
4. **Monitor cache hit rates** and adjust TTL accordingly
5. **Use appropriate fallbacks** to avoid blocking operations

## Security

### Best Practices

1. **Validate context data** before evaluation
2. **Audit all flag changes** with proper authentication
3. **Use environment-specific keys** for LaunchDarkly
4. **Rotate SDK keys** regularly
5. **Monitor for unusual usage patterns**

### Access Control

```python
# Admin service with role-based access
admin_service = FlagAdminService(flag_service)
admin_service.add_admin_user("admin@company.com")

# Check permissions before operations
if admin_service.is_admin(user_id):
    await admin_service.toggle_flag(flag_key, user_id, reason)
else:
    raise PermissionError("Insufficient privileges")
```

## Troubleshooting

### Common Issues

1. **Slow flag evaluation**

   - Check cache configuration
   - Monitor cache hit rates
   - Consider local caching

2. **Inconsistent flag values**

   - Verify cache TTL settings
   - Check user context consistency
   - Review targeting rules

3. **LaunchDarkly connection issues**

   - Verify SDK key and environment
   - Check network connectivity
   - Enable offline mode as fallback

4. **Memory usage in cache**
   - Adjust cache size limits
   - Monitor memory usage
   - Implement cache cleanup

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger("packages.shared.feature_flags").setLevel(logging.DEBUG)

# Use monitoring service for insights
monitoring_service = FlagMonitoringService(flag_service)
metrics = await monitoring_service.get_performance_report()
print(f"Performance issues: {metrics['performance_issues']}")
```

## Contributing

1. Follow the existing code style (Black formatting)
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Consider backward compatibility
5. Test with both local and LaunchDarkly backends

## License

This feature flag system is part of the AI Nutritionist application and follows the same licensing terms.
