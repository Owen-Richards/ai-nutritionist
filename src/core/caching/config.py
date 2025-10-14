"""
Cache configuration and tier definitions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import os


class CacheTier(Enum):
    """Cache tier definitions for different performance requirements."""
    
    MEMORY = "memory"           # Ultra-fast, limited size
    REDIS = "redis"             # Fast distributed cache
    CDN = "cdn"                 # Edge caching for static content
    DATABASE = "database"       # Persistent cache with TTL
    HYBRID = "hybrid"           # Multiple tiers combined


class CacheStrategy(Enum):
    """Cache strategies for different use cases."""
    
    CACHE_ASIDE = "cache_aside"         # App manages cache
    WRITE_THROUGH = "write_through"     # Write to cache and store
    WRITE_BEHIND = "write_behind"       # Write to cache, async to store
    REFRESH_AHEAD = "refresh_ahead"     # Proactive refresh before expiry


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    
    TTL = "ttl"                 # Time-based expiration
    EVENT_BASED = "event_based" # Invalidate on events
    VERSIONED = "versioned"     # Version-based invalidation
    TAG_BASED = "tag_based"     # Tag-based bulk invalidation


@dataclass
class CacheConfig:
    """Configuration for cache behavior."""
    
    # Basic settings
    default_ttl: int = 3600  # 1 hour
    max_size: int = 10000
    compression_enabled: bool = True
    
    # Redis settings
    redis_host: str = field(default_factory=lambda: os.getenv('REDIS_HOST', 'localhost'))
    redis_port: int = field(default_factory=lambda: int(os.getenv('REDIS_PORT', '6379')))
    redis_password: Optional[str] = field(default_factory=lambda: os.getenv('REDIS_PASSWORD'))
    redis_db: int = 0
    redis_cluster_mode: bool = False
    redis_connection_pool_size: int = 20
    
    # CDN settings
    cdn_enabled: bool = False
    cdn_base_url: str = ""
    cdn_cache_control: str = "public, max-age=3600"
    
    # Performance settings
    enable_background_refresh: bool = True
    refresh_threshold: float = 0.8  # Refresh when 80% of TTL passed
    batch_size: int = 100
    timeout_seconds: float = 1.0
    
    # Monitoring
    enable_metrics: bool = True
    metrics_interval: int = 60  # seconds
    
    # Memory cache settings
    memory_cache_size: int = 1000
    memory_cache_ttl: int = 300  # 5 minutes
    
    # Database cache settings
    db_cache_table: str = "ai_nutritionist_cache"
    db_cache_ttl: int = 86400  # 24 hours


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0
    
    memory_hits: int = 0
    redis_hits: int = 0
    db_hits: int = 0
    
    avg_get_time_ms: float = 0.0
    avg_set_time_ms: float = 0.0
    
    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def total_operations(self) -> int:
        """Get total cache operations."""
        return self.hits + self.misses + self.sets + self.deletes


# Predefined cache configurations for different data types
CACHE_PROFILES: Dict[str, Dict[str, Any]] = {
    "user_data": {
        "tier": CacheTier.HYBRID,
        "strategy": CacheStrategy.WRITE_THROUGH,
        "ttl": 1800,  # 30 minutes
        "tags": ["user", "profile"],
        "refresh_threshold": 0.7
    },
    
    "meal_plan": {
        "tier": CacheTier.REDIS,
        "strategy": CacheStrategy.CACHE_ASIDE,
        "ttl": 3600,  # 1 hour
        "tags": ["meal", "planning"],
        "refresh_threshold": 0.8
    },
    
    "api_response": {
        "tier": CacheTier.MEMORY,
        "strategy": CacheStrategy.CACHE_ASIDE,
        "ttl": 300,  # 5 minutes
        "tags": ["api", "external"],
        "refresh_threshold": 0.9
    },
    
    "session_data": {
        "tier": CacheTier.REDIS,
        "strategy": CacheStrategy.WRITE_THROUGH,
        "ttl": 7200,  # 2 hours
        "tags": ["session", "user"],
        "refresh_threshold": 0.6
    },
    
    "computed_results": {
        "tier": CacheTier.DATABASE,
        "strategy": CacheStrategy.WRITE_BEHIND,
        "ttl": 86400,  # 24 hours
        "tags": ["computed", "ml"],
        "refresh_threshold": 0.8
    },
    
    "static_content": {
        "tier": CacheTier.CDN,
        "strategy": CacheStrategy.CACHE_ASIDE,
        "ttl": 86400,  # 24 hours
        "tags": ["static", "cdn"],
        "refresh_threshold": 0.9
    }
}
