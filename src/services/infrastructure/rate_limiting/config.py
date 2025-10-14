"""
Rate Limiting Configuration
==========================

Configuration classes for rate limiting with tier-based support.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Union, Any
import os


class RateLimitStrategy(Enum):
    """Available rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


class UserTier(Enum):
    """User tiers with different rate limits."""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"


@dataclass
class TierLimits:
    """Rate limits for a specific tier."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_capacity: int = 0
    concurrent_requests: int = 10
    
    # AI-specific limits
    ai_requests_per_hour: int = 0
    meal_plans_per_day: int = 0
    
    # Feature access
    premium_features: bool = False
    priority_support: bool = False


@dataclass
class EndpointConfig:
    """Configuration for a specific endpoint."""
    path: str
    strategy: RateLimitStrategy
    limits: Dict[UserTier, TierLimits]
    custom_headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class TierConfig:
    """Configuration for user tiers."""
    
    # Default tier configurations
    FREE = TierLimits(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=5000,
        burst_capacity=10,
        concurrent_requests=5,
        ai_requests_per_hour=50,
        meal_plans_per_day=3,
        premium_features=False,
        priority_support=False
    )
    
    PREMIUM = TierLimits(
        requests_per_minute=300,
        requests_per_hour=10000,
        requests_per_day=50000,
        burst_capacity=50,
        concurrent_requests=20,
        ai_requests_per_hour=500,
        meal_plans_per_day=20,
        premium_features=True,
        priority_support=True
    )
    
    ENTERPRISE = TierLimits(
        requests_per_minute=1000,
        requests_per_hour=50000,
        requests_per_day=500000,
        burst_capacity=200,
        concurrent_requests=100,
        ai_requests_per_hour=2000,
        meal_plans_per_day=100,
        premium_features=True,
        priority_support=True
    )
    
    ADMIN = TierLimits(
        requests_per_minute=10000,
        requests_per_hour=500000,
        requests_per_day=5000000,
        burst_capacity=1000,
        concurrent_requests=500,
        ai_requests_per_hour=10000,
        meal_plans_per_day=1000,
        premium_features=True,
        priority_support=True
    )


@dataclass
class RateLimitConfig:
    """Main rate limiting configuration."""
    
    # Redis configuration
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    redis_key_prefix: str = "rl:"
    redis_pool_size: int = 20
    redis_timeout: int = 5
    
    # Global settings
    enabled: bool = True
    default_strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    
    # Headers
    include_headers: bool = True
    header_prefix: str = "X-RateLimit"
    
    # Fallback behavior
    allow_on_error: bool = True
    fallback_to_memory: bool = True
    
    # Cleanup and maintenance
    cleanup_interval: int = 300  # 5 minutes
    stats_retention: int = 86400  # 24 hours
    
    # Global rate limits (emergency brake)
    global_limit_per_second: int = 1000
    global_limit_per_minute: int = 50000
    
    # Default tier configuration
    tier_config: TierConfig = field(default_factory=TierConfig)
    
    # Endpoint-specific configurations
    endpoint_configs: Dict[str, EndpointConfig] = field(default_factory=dict)
    
    # Dynamic configuration
    dynamic_limits_enabled: bool = True
    auto_scaling_enabled: bool = True
    
    def get_tier_limits(self, tier: UserTier) -> TierLimits:
        """Get rate limits for a specific tier."""
        tier_map = {
            UserTier.FREE: self.tier_config.FREE,
            UserTier.PREMIUM: self.tier_config.PREMIUM,
            UserTier.ENTERPRISE: self.tier_config.ENTERPRISE,
            UserTier.ADMIN: self.tier_config.ADMIN,
        }
        return tier_map.get(tier, self.tier_config.FREE)
    
    def get_endpoint_config(self, path: str) -> Optional[EndpointConfig]:
        """Get configuration for a specific endpoint."""
        return self.endpoint_configs.get(path)
    
    def add_endpoint_config(self, config: EndpointConfig) -> None:
        """Add endpoint-specific configuration."""
        self.endpoint_configs[config.path] = config
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RateLimitConfig':
        """Create configuration from dictionary."""
        config = cls()
        
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "redis_url": self.redis_url,
            "redis_key_prefix": self.redis_key_prefix,
            "redis_pool_size": self.redis_pool_size,
            "redis_timeout": self.redis_timeout,
            "enabled": self.enabled,
            "default_strategy": self.default_strategy.value,
            "include_headers": self.include_headers,
            "header_prefix": self.header_prefix,
            "allow_on_error": self.allow_on_error,
            "fallback_to_memory": self.fallback_to_memory,
            "cleanup_interval": self.cleanup_interval,
            "stats_retention": self.stats_retention,
            "global_limit_per_second": self.global_limit_per_second,
            "global_limit_per_minute": self.global_limit_per_minute,
            "dynamic_limits_enabled": self.dynamic_limits_enabled,
            "auto_scaling_enabled": self.auto_scaling_enabled,
        }


# Default configuration instance
default_config = RateLimitConfig()

# Common endpoint configurations
DEFAULT_ENDPOINT_CONFIGS = {
    "/api/auth/login": EndpointConfig(
        path="/api/auth/login",
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        limits={
            UserTier.FREE: TierLimits(
                requests_per_minute=5,
                requests_per_hour=20,
                requests_per_day=100,
                burst_capacity=2
            ),
            UserTier.PREMIUM: TierLimits(
                requests_per_minute=10,
                requests_per_hour=50,
                requests_per_day=500,
                burst_capacity=5
            ),
        }
    ),
    
    "/api/nutrition/analyze": EndpointConfig(
        path="/api/nutrition/analyze",
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        limits={
            UserTier.FREE: TierLimits(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=500,
                burst_capacity=20,
                ai_requests_per_hour=50
            ),
            UserTier.PREMIUM: TierLimits(
                requests_per_minute=50,
                requests_per_hour=1000,
                requests_per_day=10000,
                burst_capacity=100,
                ai_requests_per_hour=500
            ),
        }
    ),
    
    "/api/meal-plans/generate": EndpointConfig(
        path="/api/meal-plans/generate",
        strategy=RateLimitStrategy.LEAKY_BUCKET,
        limits={
            UserTier.FREE: TierLimits(
                requests_per_minute=2,
                requests_per_hour=10,
                requests_per_day=3,
                burst_capacity=1,
                meal_plans_per_day=3
            ),
            UserTier.PREMIUM: TierLimits(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=20,
                burst_capacity=5,
                meal_plans_per_day=20
            ),
        }
    ),
}

# Apply default endpoint configurations
for config in DEFAULT_ENDPOINT_CONFIGS.values():
    default_config.add_endpoint_config(config)
