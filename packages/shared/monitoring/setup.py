"""
Integrated monitoring setup for AI Nutritionist services.

Provides unified configuration for logging, metrics, tracing, and health checks.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .logging import setup_logging, LogLevel, StructuredLogger
from .metrics import setup_metrics, MetricsRegistry, BusinessMetrics
from .tracing import setup_tracing, Tracer
from .health import (
    HealthMonitor, setup_basic_health_checks, DatabaseHealthCheck,
    ExternalAPIHealthCheck, MemoryHealthCheck, DiskHealthCheck
)


@dataclass
class MonitoringConfig:
    """Configuration for monitoring setup."""
    service_name: str = "ai-nutritionist"
    environment: str = "development"
    
    # Logging configuration
    log_level: LogLevel = LogLevel.INFO
    use_cloudwatch_logs: bool = False
    cloudwatch_log_group: Optional[str] = None
    cloudwatch_log_stream: Optional[str] = None
    
    # Metrics configuration
    use_cloudwatch_metrics: bool = False
    metrics_namespace: str = "AI-Nutritionist"
    
    # Tracing configuration
    use_xray: bool = False
    use_tracing_logs: bool = True
    
    # Health check configuration
    enable_health_checks: bool = True
    health_check_interval: int = 60
    
    # AWS configuration
    aws_region: str = "us-east-1"
    
    # Additional configuration
    extra_tags: Dict[str, str] = field(default_factory=dict)


class MonitoringManager:
    """Central manager for all monitoring components."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.logger: Optional[StructuredLogger] = None
        self.metrics: Optional[MetricsRegistry] = None
        self.tracer: Optional[Tracer] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.business_metrics: Optional[BusinessMetrics] = None
        
    def setup_all(self) -> None:
        """Setup all monitoring components."""
        self.setup_logging()
        self.setup_metrics()
        self.setup_tracing()
        self.setup_health_checks()
        
        # Log successful setup
        if self.logger:
            self.logger.info(
                f"Monitoring setup complete for {self.config.service_name}",
                extra={
                    "environment": self.config.environment,
                    "cloudwatch_logs": self.config.use_cloudwatch_logs,
                    "cloudwatch_metrics": self.config.use_cloudwatch_metrics,
                    "xray_tracing": self.config.use_xray,
                    "health_checks": self.config.enable_health_checks
                }
            )
    
    def setup_logging(self) -> StructuredLogger:
        """Setup structured logging."""
        self.logger = setup_logging(
            service_name=self.config.service_name,
            log_level=self.config.log_level,
            use_cloudwatch=self.config.use_cloudwatch_logs,
            cloudwatch_log_group=self.config.cloudwatch_log_group,
            cloudwatch_log_stream=self.config.cloudwatch_log_stream,
            cloudwatch_region=self.config.aws_region
        )
        
        # Set service context
        self.logger.context.service_name = self.config.service_name
        for key, value in self.config.extra_tags.items():
            setattr(self.logger.context, key, value)
        
        return self.logger
    
    def setup_metrics(self) -> MetricsRegistry:
        """Setup metrics collection."""
        self.metrics = setup_metrics(
            namespace=self.config.metrics_namespace,
            use_cloudwatch=self.config.use_cloudwatch_metrics,
            cloudwatch_region=self.config.aws_region
        )
        
        from .metrics import business_metrics as global_business_metrics
        self.business_metrics = global_business_metrics
        
        return self.metrics
    
    def setup_tracing(self) -> Tracer:
        """Setup distributed tracing."""
        self.tracer = setup_tracing(
            service_name=self.config.service_name,
            use_xray=self.config.use_xray,
            use_logging=self.config.use_tracing_logs,
            xray_region=self.config.aws_region
        )
        
        return self.tracer
    
    def setup_health_checks(self) -> Optional[HealthMonitor]:
        """Setup health monitoring."""
        if not self.config.enable_health_checks:
            return None
        
        from .health import get_health_monitor
        self.health_monitor = get_health_monitor(self.config.service_name)
        
        # Setup basic health checks
        setup_basic_health_checks(self.health_monitor)
        
        # Start periodic health checks
        self.health_monitor.start_periodic_checks(self.config.health_check_interval)
        
        return self.health_monitor
    
    def add_database_health_check(self, name: str, connection_factory, timeout: float = 5.0) -> None:
        """Add database health check."""
        if self.health_monitor:
            check = DatabaseHealthCheck(name, connection_factory, timeout)
            self.health_monitor.add_check(check)
    
    def add_external_api_health_check(
        self, 
        name: str, 
        url: str, 
        timeout: float = 5.0, 
        expected_status: int = 200
    ) -> None:
        """Add external API health check."""
        if self.health_monitor:
            check = ExternalAPIHealthCheck(name, url, timeout, expected_status)
            self.health_monitor.add_check(check)
    
    def get_logger(self) -> StructuredLogger:
        """Get logger instance."""
        if not self.logger:
            self.setup_logging()
        return self.logger
    
    def get_metrics(self) -> MetricsRegistry:
        """Get metrics registry."""
        if not self.metrics:
            self.setup_metrics()
        return self.metrics
    
    def get_tracer(self) -> Tracer:
        """Get tracer instance."""
        if not self.tracer:
            self.setup_tracing()
        return self.tracer
    
    def get_health_monitor(self) -> Optional[HealthMonitor]:
        """Get health monitor."""
        if not self.health_monitor and self.config.enable_health_checks:
            self.setup_health_checks()
        return self.health_monitor
    
    def get_business_metrics(self) -> Optional[BusinessMetrics]:
        """Get business metrics tracker."""
        if not self.business_metrics:
            self.setup_metrics()
        return self.business_metrics


def create_monitoring_config_from_env() -> MonitoringConfig:
    """Create monitoring configuration from environment variables."""
    return MonitoringConfig(
        service_name=os.getenv("SERVICE_NAME", "ai-nutritionist"),
        environment=os.getenv("ENVIRONMENT", "development"),
        
        # Logging
        log_level=LogLevel(os.getenv("LOG_LEVEL", "INFO")),
        use_cloudwatch_logs=os.getenv("USE_CLOUDWATCH_LOGS", "false").lower() == "true",
        cloudwatch_log_group=os.getenv("CLOUDWATCH_LOG_GROUP"),
        cloudwatch_log_stream=os.getenv("CLOUDWATCH_LOG_STREAM"),
        
        # Metrics
        use_cloudwatch_metrics=os.getenv("USE_CLOUDWATCH_METRICS", "false").lower() == "true",
        metrics_namespace=os.getenv("METRICS_NAMESPACE", "AI-Nutritionist"),
        
        # Tracing
        use_xray=os.getenv("USE_XRAY", "false").lower() == "true",
        use_tracing_logs=os.getenv("USE_TRACING_LOGS", "true").lower() == "true",
        
        # Health checks
        enable_health_checks=os.getenv("ENABLE_HEALTH_CHECKS", "true").lower() == "true",
        health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
        
        # AWS
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        
        # Extra tags
        extra_tags={
            "environment": os.getenv("ENVIRONMENT", "development"),
            "version": os.getenv("APP_VERSION", "unknown")
        }
    )


def setup_service_monitoring(
    service_name: str,
    config: Optional[MonitoringConfig] = None
) -> MonitoringManager:
    """Setup monitoring for a service."""
    if config is None:
        config = create_monitoring_config_from_env()
        config.service_name = service_name
    
    manager = MonitoringManager(config)
    manager.setup_all()
    
    return manager


# Global monitoring manager
_global_manager: Optional[MonitoringManager] = None


def get_global_monitoring() -> MonitoringManager:
    """Get global monitoring manager."""
    global _global_manager
    if _global_manager is None:
        config = create_monitoring_config_from_env()
        _global_manager = MonitoringManager(config)
        _global_manager.setup_all()
    return _global_manager


def get_logger() -> StructuredLogger:
    """Get global logger."""
    return get_global_monitoring().get_logger()


def get_metrics() -> MetricsRegistry:
    """Get global metrics registry."""
    return get_global_monitoring().get_metrics()


def get_tracer() -> Tracer:
    """Get global tracer."""
    return get_global_monitoring().get_tracer()


def get_health_monitor() -> Optional[HealthMonitor]:
    """Get global health monitor."""
    return get_global_monitoring().get_health_monitor()


def get_business_metrics() -> Optional[BusinessMetrics]:
    """Get global business metrics."""
    return get_global_monitoring().get_business_metrics()
