"""Feature flag models and data structures."""

from __future__ import annotations

import enum
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class FlagStatus(str, enum.Enum):
    """Feature flag status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    ROLLBACK = "rollback"


class RolloutStrategy(str, enum.Enum):
    """Rollout strategy types."""
    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    SEGMENT = "segment"
    GRADUAL = "gradual"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"


class FlagVariant(BaseModel):
    """Feature flag variant definition."""
    key: str
    name: str
    value: Any
    description: Optional[str] = None
    percentage: float = Field(default=0.0, ge=0, le=100)
    is_control: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TargetingRule(BaseModel):
    """Targeting rule for feature flags."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    conditions: List[Dict[str, Any]]
    variant: str
    percentage: float = Field(default=100.0, ge=0, le=100)
    description: Optional[str] = None
    priority: int = 0  # Higher priority rules are evaluated first


class UserSegment(BaseModel):
    """User segment definition for targeting."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    conditions: List[Dict[str, Any]]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('conditions')
    def validate_conditions(cls, v):
        """Validate segment conditions."""
        for condition in v:
            if 'attribute' not in condition or 'operator' not in condition:
                raise ValueError("Each condition must have 'attribute' and 'operator'")
        return v


class FlagRolloutRule(BaseModel):
    """Rollout rule configuration."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    strategy: RolloutStrategy
    percentage: Optional[float] = Field(default=None, ge=0, le=100)
    user_ids: Optional[List[str]] = None
    segments: Optional[List[str]] = None
    targeting_rules: List[TargetingRule] = Field(default_factory=list)
    schedule: Optional[Dict[str, Any]] = None
    
    @validator('percentage')
    def validate_percentage(cls, v, values):
        """Validate percentage for percentage-based strategies."""
        strategy = values.get('strategy')
        if strategy == RolloutStrategy.PERCENTAGE and v is None:
            raise ValueError("Percentage is required for percentage rollout strategy")
        return v


class ABTestConfiguration(BaseModel):
    """A/B test configuration."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    variants: List[FlagVariant]
    traffic_allocation: float = Field(default=100.0, ge=0, le=100)
    primary_metric: str
    secondary_metrics: List[str] = Field(default_factory=list)
    minimum_sample_size: int = 1000
    significance_threshold: float = 0.05
    max_duration_days: int = 30
    
    @validator('variants')
    def validate_variants(cls, v):
        """Validate A/B test variants."""
        if len(v) < 2:
            raise ValueError("A/B test must have at least 2 variants")
        
        total_percentage = sum(variant.percentage for variant in v)
        if not (99.0 <= total_percentage <= 101.0):  # Allow small rounding errors
            raise ValueError(f"Variant percentages must sum to 100%, got {total_percentage}%")
        
        return v


class FlagTarget(BaseModel):
    """Feature flag target configuration."""
    user_id: Optional[str] = None
    segment_ids: List[str] = Field(default_factory=list)
    percentage: float = Field(default=0.0, ge=0, le=100)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class FlagContext(BaseModel):
    """Context for feature flag evaluation."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    country: Optional[str] = None
    subscription_tier: Optional[str] = None
    user_segments: List[str] = Field(default_factory=list)
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FeatureFlagDefinition(BaseModel):
    """Complete feature flag definition."""
    key: str
    name: str
    description: str
    status: FlagStatus = FlagStatus.INACTIVE
    
    # Variants and targeting
    variants: List[FlagVariant]
    default_variant: str
    fallback_variant: str
    
    # Rollout configuration
    rollout_rules: List[FlagRolloutRule] = Field(default_factory=list)
    targeting_rules: List[TargetingRule] = Field(default_factory=list)
    
    # A/B testing
    ab_test: Optional[ABTestConfiguration] = None
    
    # Emergency controls
    kill_switch: bool = False
    emergency_fallback: Optional[str] = None
    
    # Lifecycle
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    environment: str = "development"
    project_id: Optional[str] = None
    
    @validator('variants')
    def validate_variants(cls, v, values):
        """Validate flag variants."""
        if not v:
            raise ValueError("Flag must have at least one variant")
        
        default_variant = values.get('default_variant')
        fallback_variant = values.get('fallback_variant')
        
        variant_keys = [variant.key for variant in v]
        
        if default_variant and default_variant not in variant_keys:
            raise ValueError(f"Default variant '{default_variant}' not found in variants")
        
        if fallback_variant and fallback_variant not in variant_keys:
            raise ValueError(f"Fallback variant '{fallback_variant}' not found in variants")
        
        return v


class FlagEvaluationResult(BaseModel):
    """Result of feature flag evaluation."""
    flag_key: str
    variant_key: str
    value: Any
    reason: str
    is_default: bool = False
    rule_id: Optional[str] = None
    experiment_id: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class FlagAuditEvent(BaseModel):
    """Audit event for feature flag changes."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    flag_key: str
    event_type: str  # created, updated, deleted, toggled, etc.
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Change details
    previous_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    
    # Context
    environment: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    reason: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FlagCleanupRule(BaseModel):
    """Rule for automatic flag cleanup."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    
    # Conditions
    flag_age_days: Optional[int] = None
    flag_status: Optional[FlagStatus] = None
    last_evaluation_days: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    
    # Actions
    action: str  # archive, delete, notify
    notify_users: List[str] = Field(default_factory=list)
    
    # Schedule
    enabled: bool = True
    cron_schedule: str = "0 2 * * 0"  # Weekly on Sunday at 2 AM
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str


class FlagUsageMetrics(BaseModel):
    """Feature flag usage metrics."""
    flag_key: str
    evaluation_count: int = 0
    unique_users: int = 0
    variant_distributions: Dict[str, int] = Field(default_factory=dict)
    last_evaluated: Optional[datetime] = None
    
    # Time period
    period_start: datetime
    period_end: datetime
    
    # Performance metrics
    avg_evaluation_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0


# Integration models for LaunchDarkly
class LaunchDarklyConfig(BaseModel):
    """LaunchDarkly client configuration."""
    sdk_key: str
    base_uri: Optional[str] = None
    events_uri: Optional[str] = None
    stream_uri: Optional[str] = None
    
    # Performance settings
    cache_ttl_seconds: int = 300
    start_wait_seconds: int = 5
    send_events: bool = True
    events_capacity: int = 10000
    events_flush_interval_seconds: int = 5
    
    # Reliability settings
    offline: bool = False
    use_ldd: bool = False
    feature_store: Optional[str] = None
    
    # Environment
    environment: str = "development"
    
    def model_post_init(self, __context: Any) -> None:
        """Validate configuration after initialization."""
        if not self.sdk_key:
            raise ValueError("SDK key is required")
