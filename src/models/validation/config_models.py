"""Comprehensive Pydantic models for configuration and infrastructure services."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, SecretStr

from .user_models import BaseValidationModel, APIBaseModel


class EnvironmentType(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SecretType(str, Enum):
    """Secret types for secret management."""
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    ENCRYPTION_KEY = "encryption_key"
    CERTIFICATE = "certificate"
    OAUTH_SECRET = "oauth_secret"
    WEBHOOK_SECRET = "webhook_secret"


class MonitoringStatus(str, Enum):
    """Monitoring status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class FeatureFlag(BaseValidationModel):
    """Feature flag configuration."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique feature flag identifier")
    name: Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')] = Field(
        ...,
        description="Feature flag name"
    )
    description: Annotated[str, Field(min_length=1, max_length=500)] = Field(
        ...,
        description="Feature flag description"
    )
    enabled: bool = Field(
        default=False,
        description="Whether the feature is enabled"
    )
    environment: EnvironmentType = Field(
        ...,
        description="Environment this flag applies to"
    )
    rollout_percentage: Annotated[int, Field(ge=0, le=100)] = Field(
        default=0,
        description="Percentage of users to roll out to"
    )
    user_whitelist: List[UUID] = Field(
        default_factory=list,
        description="Users who always have this feature enabled"
    )
    user_blacklist: List[UUID] = Field(
        default_factory=list,
        description="Users who never have this feature enabled"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="When the feature should become available"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="When the feature should be disabled"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the feature flag"
    )
    
    @model_validator(mode='after')
    def validate_feature_flag(self) -> 'FeatureFlag':
        """Validate feature flag configuration."""
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValueError("End date must be after start date")
        
        # Check for conflicts between whitelist and blacklist
        if set(self.user_whitelist) & set(self.user_blacklist):
            raise ValueError("Users cannot be in both whitelist and blacklist")
        
        return self
    
    def is_enabled_for_user(self, user_id: UUID) -> bool:
        """Check if feature is enabled for a specific user."""
        # Check blacklist first
        if user_id in self.user_blacklist:
            return False
        
        # Check whitelist
        if user_id in self.user_whitelist:
            return True
        
        # Check global enable status
        if not self.enabled:
            return False
        
        # Check date range
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        
        # Check rollout percentage
        if self.rollout_percentage == 100:
            return True
        if self.rollout_percentage == 0:
            return False
        
        # Use user ID hash for consistent rollout
        import hashlib
        user_hash = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
        return (user_hash % 100) < self.rollout_percentage


class DatabaseConfig(BaseValidationModel):
    """Database configuration."""
    
    host: Annotated[str, Field(min_length=1, max_length=255)] = Field(
        ...,
        description="Database host"
    )
    port: Annotated[int, Field(gt=0, le=65535)] = Field(
        ...,
        description="Database port"
    )
    database: Annotated[str, Field(min_length=1, max_length=100)] = Field(
        ...,
        description="Database name"
    )
    username: Annotated[str, Field(min_length=1, max_length=100)] = Field(
        ...,
        description="Database username"
    )
    password: SecretStr = Field(
        ...,
        description="Database password"
    )
    ssl_enabled: bool = Field(
        default=True,
        description="Whether SSL is enabled"
    )
    connection_timeout: Annotated[int, Field(gt=0, le=300)] = Field(
        default=30,
        description="Connection timeout in seconds"
    )
    max_connections: Annotated[int, Field(gt=0, le=1000)] = Field(
        default=100,
        description="Maximum number of connections"
    )
    pool_size: Annotated[int, Field(gt=0, le=100)] = Field(
        default=10,
        description="Connection pool size"
    )
    
    @property
    def connection_string(self) -> str:
        """Generate database connection string."""
        password = self.password.get_secret_value()
        ssl_param = "?sslmode=require" if self.ssl_enabled else ""
        return f"postgresql://{self.username}:{password}@{self.host}:{self.port}/{self.database}{ssl_param}"


class RedisConfig(BaseValidationModel):
    """Redis configuration."""
    
    host: Annotated[str, Field(min_length=1, max_length=255)] = Field(
        ...,
        description="Redis host"
    )
    port: Annotated[int, Field(gt=0, le=65535)] = Field(
        default=6379,
        description="Redis port"
    )
    password: Optional[SecretStr] = Field(
        None,
        description="Redis password"
    )
    database: Annotated[int, Field(ge=0, le=15)] = Field(
        default=0,
        description="Redis database number"
    )
    ssl_enabled: bool = Field(
        default=False,
        description="Whether SSL is enabled"
    )
    connection_timeout: Annotated[int, Field(gt=0, le=60)] = Field(
        default=5,
        description="Connection timeout in seconds"
    )
    max_connections: Annotated[int, Field(gt=0, le=1000)] = Field(
        default=50,
        description="Maximum number of connections"
    )


class APIConfig(BaseValidationModel):
    """API service configuration."""
    
    base_url: Annotated[str, Field(min_length=1, max_length=500)] = Field(
        ...,
        description="Base URL for the API"
    )
    api_key: Optional[SecretStr] = Field(
        None,
        description="API key for authentication"
    )
    timeout: Annotated[int, Field(gt=0, le=300)] = Field(
        default=30,
        description="Request timeout in seconds"
    )
    retry_attempts: Annotated[int, Field(ge=0, le=10)] = Field(
        default=3,
        description="Number of retry attempts"
    )
    retry_delay: Annotated[float, Field(gt=0, le=60)] = Field(
        default=1.0,
        description="Delay between retries in seconds"
    )
    rate_limit_per_minute: Optional[Annotated[int, Field(gt=0, le=10000)]] = Field(
        None,
        description="Rate limit per minute"
    )
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip('/')


class LoggingConfig(BaseValidationModel):
    """Logging configuration."""
    
    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Default logging level"
    )
    format: Annotated[str, Field(min_length=1, max_length=500)] = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    handlers: List[str] = Field(
        default_factory=lambda: ["console"],
        description="Log handlers to use"
    )
    file_path: Optional[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        None,
        description="Log file path (if file handler is used)"
    )
    max_file_size_mb: Annotated[int, Field(gt=0, le=1000)] = Field(
        default=100,
        description="Maximum log file size in MB"
    )
    backup_count: Annotated[int, Field(ge=0, le=100)] = Field(
        default=5,
        description="Number of backup log files to keep"
    )
    structured_logging: bool = Field(
        default=True,
        description="Whether to use structured (JSON) logging"
    )


class SecurityConfig(BaseValidationModel):
    """Security configuration."""
    
    encryption_key: SecretStr = Field(
        ...,
        description="Primary encryption key"
    )
    jwt_secret: SecretStr = Field(
        ...,
        description="JWT signing secret"
    )
    jwt_expiry_hours: Annotated[int, Field(gt=0, le=8760)] = Field(  # Max 1 year
        default=24,
        description="JWT token expiry in hours"
    )
    password_min_length: Annotated[int, Field(ge=8, le=128)] = Field(
        default=8,
        description="Minimum password length"
    )
    session_timeout_minutes: Annotated[int, Field(gt=0, le=10080)] = Field(  # Max 1 week
        default=60,
        description="Session timeout in minutes"
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Whether rate limiting is enabled"
    )
    rate_limit_requests_per_minute: Annotated[int, Field(gt=0, le=10000)] = Field(
        default=100,
        description="Rate limit requests per minute"
    )
    cors_origins: List[str] = Field(
        default_factory=list,
        description="Allowed CORS origins"
    )
    
    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        """Validate CORS origins."""
        for origin in v:
            if origin != "*" and not origin.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid CORS origin: {origin}")
        return v


class MonitoringConfig(BaseValidationModel):
    """Monitoring and observability configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Whether monitoring is enabled"
    )
    metrics_endpoint: Optional[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        None,
        description="Metrics collection endpoint"
    )
    health_check_interval: Annotated[int, Field(gt=0, le=3600)] = Field(
        default=30,
        description="Health check interval in seconds"
    )
    alert_webhook_url: Optional[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        None,
        description="Webhook URL for alerts"
    )
    sentry_dsn: Optional[SecretStr] = Field(
        None,
        description="Sentry DSN for error tracking"
    )
    datadog_api_key: Optional[SecretStr] = Field(
        None,
        description="Datadog API key for metrics"
    )


class ApplicationConfig(BaseValidationModel):
    """Complete application configuration."""
    
    environment: EnvironmentType = Field(
        ...,
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Whether debug mode is enabled"
    )
    database: DatabaseConfig = Field(
        ...,
        description="Database configuration"
    )
    redis: RedisConfig = Field(
        ...,
        description="Redis configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    security: SecurityConfig = Field(
        ...,
        description="Security configuration"
    )
    monitoring: MonitoringConfig = Field(
        default_factory=MonitoringConfig,
        description="Monitoring configuration"
    )
    external_apis: Dict[str, APIConfig] = Field(
        default_factory=dict,
        description="External API configurations"
    )
    feature_flags: List[FeatureFlag] = Field(
        default_factory=list,
        description="Feature flag configurations"
    )
    
    @model_validator(mode='after')
    def validate_environment_config(self) -> 'ApplicationConfig':
        """Validate configuration based on environment."""
        if self.environment == EnvironmentType.PRODUCTION:
            if self.debug:
                raise ValueError("Debug mode cannot be enabled in production")
            if not self.database.ssl_enabled:
                raise ValueError("SSL must be enabled for production database")
            if self.logging.level == LogLevel.DEBUG:
                raise ValueError("Debug logging should not be used in production")
        
        return self


class HealthCheck(BaseValidationModel):
    """Health check result."""
    
    service_name: Annotated[str, Field(min_length=1, max_length=100)] = Field(
        ...,
        description="Name of the service being checked"
    )
    status: MonitoringStatus = Field(
        ...,
        description="Health status"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Check timestamp"
    )
    response_time_ms: Annotated[float, Field(ge=0)] = Field(
        ...,
        description="Response time in milliseconds"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional health check details"
    )
    error_message: Optional[Annotated[str, Field(max_length=1000)]] = Field(
        None,
        description="Error message if status is not healthy"
    )
    
    @model_validator(mode='after')
    def validate_health_check(self) -> 'HealthCheck':
        """Validate health check consistency."""
        if self.status in [MonitoringStatus.WARNING, MonitoringStatus.CRITICAL]:
            if not self.error_message:
                raise ValueError("Error message required for warning/critical status")
        
        return self


class MetricData(BaseValidationModel):
    """Metric data point."""
    
    name: Annotated[str, Field(min_length=1, max_length=100)] = Field(
        ...,
        description="Metric name"
    )
    value: float = Field(
        ...,
        description="Metric value"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metric timestamp"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Metric tags"
    )
    unit: Optional[Annotated[str, Field(min_length=1, max_length=20)]] = Field(
        None,
        description="Metric unit"
    )


# API Request/Response Models

class ConfigUpdateRequest(APIBaseModel):
    """Request model for configuration updates."""
    
    feature_flags: Optional[List[FeatureFlag]] = Field(
        None,
        description="Feature flags to update"
    )
    logging_level: Optional[LogLevel] = Field(
        None,
        description="Logging level to set"
    )
    maintenance_mode: Optional[bool] = Field(
        None,
        description="Whether to enable maintenance mode"
    )


class HealthCheckResponse(APIBaseModel):
    """Response model for health checks."""
    
    overall_status: MonitoringStatus = Field(
        ...,
        description="Overall system health status"
    )
    services: List[HealthCheck] = Field(
        ...,
        description="Individual service health checks"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Overall check timestamp"
    )
    uptime_seconds: Annotated[float, Field(ge=0)] = Field(
        ...,
        description="System uptime in seconds"
    )


class MetricsResponse(APIBaseModel):
    """Response model for metrics data."""
    
    metrics: List[MetricData] = Field(
        ...,
        description="List of metric data points"
    )
    period_start: datetime = Field(
        ...,
        description="Start of metrics period"
    )
    period_end: datetime = Field(
        ...,
        description="End of metrics period"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary statistics"
    )


class ConfigResponse(APIBaseModel):
    """Response model for configuration data."""
    
    environment: EnvironmentType = Field(
        ...,
        description="Current environment"
    )
    feature_flags: List[FeatureFlag] = Field(
        ...,
        description="Active feature flags"
    )
    public_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Public configuration values"
    )
    last_updated: datetime = Field(
        ...,
        description="Last configuration update timestamp"
    )
