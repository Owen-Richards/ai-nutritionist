"""
Shared Package - Common functionality across all services

This package contains shared utilities, types, and infrastructure
components used throughout the AI Nutritionist application.

Modules:
- error_handling: Comprehensive error management system (placeholder)
- monitoring: System monitoring and observability  
- types: Common type definitions and data structures
"""

# Export monitoring system
from .monitoring import (
    # Logging
    StructuredLogger, LogLevel, EventType, LogContext, PerformanceMetrics,
    BusinessEvent, PIIMasker, LogFormatter, LogHandler, ConsoleLogHandler,
    CloudWatchLogHandler, performance_monitor, audit_log, get_logger, setup_logging,
    
    # Metrics
    MetricCollector, InMemoryMetricCollector, CloudWatchMetricCollector,
    Counter, Gauge, Histogram, MetricsRegistry, BusinessMetrics,
    get_registry, setup_metrics, business_metrics,
    
    # Tracing
    Tracer, Span, SpanContext, SpanStatus, TraceExporter, ConsoleTraceExporter,
    LoggingTraceExporter, XRayTraceExporter, TraceContext, get_tracer,
    setup_tracing, trace_operation,
    
    # Health
    HealthCheck, HealthStatus, HealthCheckResult, ServiceHealth,
    DatabaseHealthCheck, ExternalAPIHealthCheck, MemoryHealthCheck,
    DiskHealthCheck, HealthMonitor, get_health_monitor, setup_basic_health_checks,
)

__all__ = [
    # Logging
    'StructuredLogger', 'LogLevel', 'EventType', 'LogContext', 'PerformanceMetrics',
    'BusinessEvent', 'PIIMasker', 'LogFormatter', 'LogHandler', 'ConsoleLogHandler',
    'CloudWatchLogHandler', 'performance_monitor', 'audit_log', 'get_logger', 'setup_logging',
    
    # Metrics
    'MetricCollector', 'InMemoryMetricCollector', 'CloudWatchMetricCollector',
    'Counter', 'Gauge', 'Histogram', 'MetricsRegistry', 'BusinessMetrics',
    'get_registry', 'setup_metrics', 'business_metrics',
    
    # Tracing
    'Tracer', 'Span', 'SpanContext', 'SpanStatus', 'TraceExporter', 'ConsoleTraceExporter',
    'LoggingTraceExporter', 'XRayTraceExporter', 'TraceContext', 'get_tracer',
    'setup_tracing', 'trace_operation',
    
    # Health
    'HealthCheck', 'HealthStatus', 'HealthCheckResult', 'ServiceHealth',
    'DatabaseHealthCheck', 'ExternalAPIHealthCheck', 'MemoryHealthCheck',
    'DiskHealthCheck', 'HealthMonitor', 'get_health_monitor', 'setup_basic_health_checks',
]