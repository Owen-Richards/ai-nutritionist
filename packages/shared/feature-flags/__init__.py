"""Feature flag system for controlled rollouts and A/B testing."""

from .models import (
    FeatureFlagDefinition,
    FlagVariant,
    FlagRolloutRule,
    FlagTarget,
    FlagStatus,
    FlagContext,
    FlagAuditEvent,
    RolloutStrategy,
    TargetingRule,
    UserSegment,
    ABTestConfiguration,
)

from .service import (
    FeatureFlagService,
    LaunchDarklyService,
    CacheConfig,
)

from .cache import (
    FeatureFlagCache,
    MemoryCache,
    RedisCache,
)

from .client import (
    FeatureFlagClient,
    LaunchDarklyClient,
)

from .admin import (
    FlagAdminService,
    FlagLifecycleManager,
    FlagCleanupService,
)

from .middleware import (
    FeatureFlagMiddleware,
    flag_required,
    feature_gate,
)

from .monitoring import (
    FlagMonitoringService,
    FlagMetrics,
    FlagEventLogger,
)

__all__ = [
    # Models
    "FeatureFlagDefinition",
    "FlagVariant",
    "FlagRolloutRule",
    "FlagTarget",
    "FlagStatus",
    "FlagContext",
    "FlagAuditEvent",
    "RolloutStrategy",
    "TargetingRule",
    "UserSegment",
    "ABTestConfiguration",
    
    # Services
    "FeatureFlagService",
    "LaunchDarklyService",
    "CacheConfig",
    
    # Cache
    "FeatureFlagCache",
    "MemoryCache",
    "RedisCache",
    
    # Client
    "FeatureFlagClient",
    "LaunchDarklyClient",
    
    # Admin
    "FlagAdminService",
    "FlagLifecycleManager",
    "FlagCleanupService",
    
    # Middleware
    "FeatureFlagMiddleware",
    "flag_required",
    "feature_gate",
    
    # Monitoring
    "FlagMonitoringService",
    "FlagMetrics",
    "FlagEventLogger",
]
