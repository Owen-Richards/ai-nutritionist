"""Shared monitoring package.

Comprehensive performance monitoring and observability for the AI Nutritionist platform.
"""

from .logging import (
    StructuredLogger, LogLevel, EventType, LogContext, PerformanceMetrics,
    BusinessEvent, PIIMasker, LogFormatter, LogHandler, ConsoleLogHandler,
    CloudWatchLogHandler, performance_monitor, audit_log, get_logger, setup_logging
)
from .metrics import (
    MetricCollector, InMemoryMetricCollector, CloudWatchMetricCollector,
    Counter, Gauge, Histogram, MetricsRegistry, BusinessMetrics,
    get_registry, setup_metrics, business_metrics
)
from .tracing import (
    Tracer, Span, SpanContext, SpanStatus, TraceExporter, ConsoleTraceExporter,
    LoggingTraceExporter, XRayTraceExporter, TraceContext, get_tracer,
    setup_tracing, trace_operation
)
from .health import (
    HealthCheck, HealthStatus, HealthCheckResult, ServiceHealth,
    DatabaseHealthCheck, ExternalAPIHealthCheck, MemoryHealthCheck,
    DiskHealthCheck, HealthMonitor, get_health_monitor, setup_basic_health_checks
)
from .performance_monitor import PerformanceMonitor
from .business_metrics import BusinessMetricsTracker
from .infrastructure_monitor import InfrastructureMonitor
from .distributed_tracing import DistributedTracer
from .dashboards import DashboardManager
from .alerts import AlertManager

__all__ = [
    # Logging
    "StructuredLogger", "LogLevel", "EventType", "LogContext", "PerformanceMetrics",
    "BusinessEvent", "PIIMasker", "LogFormatter", "LogHandler", "ConsoleLogHandler",
    "CloudWatchLogHandler", "performance_monitor", "audit_log", "get_logger", "setup_logging",
    
    # Metrics
    "MetricCollector", "InMemoryMetricCollector", "CloudWatchMetricCollector",
    "Counter", "Gauge", "Histogram", "MetricsRegistry", "BusinessMetrics",
    "get_registry", "setup_metrics", "business_metrics",
    
    # Tracing
    "Tracer", "Span", "SpanContext", "SpanStatus", "TraceExporter", "ConsoleTraceExporter",
    "LoggingTraceExporter", "XRayTraceExporter", "TraceContext", "get_tracer",
    "setup_tracing", "trace_operation",
    
    # Health
    "HealthCheck", "HealthStatus", "HealthCheckResult", "ServiceHealth",
    "DatabaseHealthCheck", "ExternalAPIHealthCheck", "MemoryHealthCheck",
    "DiskHealthCheck", "HealthMonitor", "get_health_monitor", "setup_basic_health_checks",
    
    # Performance Monitoring
    "PerformanceMonitor", "BusinessMetricsTracker", "InfrastructureMonitor",
    "DistributedTracer", "DashboardManager", "AlertManager"
]
