"""
Comprehensive Health Check System

This package provides a complete health checking system with:
- Service health checks (liveness, readiness, startup)
- Dependency health checks
- Circuit breaker pattern
- Health check endpoints
- Monitoring integration
- Fallback mechanisms

Usage:
    from packages.shared.health_check import (
        HealthChecker, HealthStatus, HealthCheckType,
        health_check_endpoint, circuit_breaker_health
    )
"""

from .core import (
    HealthChecker,
    HealthStatus,
    HealthCheckType,
    HealthCheckResult,
    DependencyCheck,
    ServiceHealth
)

from .endpoints import (
    HealthCheckRouter,
    health_check_endpoint,
    create_health_routes
)

from .circuit_breaker import (
    CircuitBreakerHealthCheck,
    CircuitBreakerState,
    CircuitBreakerConfig
)

from .monitoring import (
    HealthMonitor,
    CloudWatchHealthReporter,
    PrometheusHealthReporter,
    HealthMetrics
)

from .probes import (
    LivenessProbe,
    ReadinessProbe,
    StartupProbe,
    ProbeConfig
)

from .dependencies import (
    DatabaseHealthCheck,
    RedisHealthCheck,
    HTTPServiceHealthCheck,
    AWSServiceHealthCheck,
    ExternalAPIHealthCheck
)

__all__ = [
    # Core health checking
    'HealthChecker',
    'HealthStatus',
    'HealthCheckType',
    'HealthCheckResult',
    'DependencyCheck',
    'ServiceHealth',
    
    # Health check endpoints
    'HealthCheckRouter',
    'health_check_endpoint',
    'create_health_routes',
    
    # Circuit breaker
    'CircuitBreakerHealthCheck',
    'CircuitBreakerState',
    'CircuitBreakerConfig',
    
    # Monitoring integration
    'HealthMonitor',
    'CloudWatchHealthReporter',
    'PrometheusHealthReporter',
    'HealthMetrics',
    
    # Health probes
    'LivenessProbe',
    'ReadinessProbe',
    'StartupProbe',
    'ProbeConfig',
    
    # Dependency checks
    'DatabaseHealthCheck',
    'RedisHealthCheck',
    'HTTPServiceHealthCheck',
    'AWSServiceHealthCheck',
    'ExternalAPIHealthCheck'
]
