"""
G1 - Observability Infrastructure
Structured logs, traces, RED metrics, and SLO monitoring for production reliability.
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import uuid
from collections import defaultdict, deque
import threading

# Try importing optional dependencies with fallbacks
try:
    from opentelemetry import trace
    from opentelemetry.trace import Tracer
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    trace = None
    Tracer = None

try:
    import prometheus_client
    from prometheus_client import Counter, Histogram, Gauge, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    prometheus_client = None


class LogLevel(str, Enum):
    """Standard log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MetricType(str, Enum):
    """RED metrics types."""
    RATE = "rate"
    ERROR = "error"
    DURATION = "duration"


@dataclass
class StructuredLogEntry:
    """Structured log entry with consistent format."""
    timestamp: str
    level: LogLevel
    message: str
    service: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    operation: Optional[str] = None
    duration_ms: Optional[float] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Convert to JSON string for structured logging."""
        return json.dumps(asdict(self), default=str, ensure_ascii=False)


@dataclass
class SLOMetric:
    """Service Level Objective metric."""
    name: str
    target_percentage: float  # e.g., 99.9
    measurement_window_hours: int  # e.g., 24
    current_percentage: float
    breaches_count: int
    last_breach: Optional[datetime] = None


@dataclass  
class REDMetrics:
    """Rate, Error, Duration metrics."""
    service: str
    endpoint: str
    rate_per_minute: float
    error_rate_percentage: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    timestamp: datetime


class ObservabilityService:
    """
    Central observability service providing structured logging, 
    distributed tracing, RED metrics, and SLO monitoring.
    """
    
    def __init__(
        self,
        service_name: str = "ai-nutritionist",
        log_level: LogLevel = LogLevel.INFO,
        enable_tracing: bool = True,
        enable_metrics: bool = True
    ):
        self.service_name = service_name
        self.log_level = log_level
        self.enable_tracing = enable_tracing and TRACING_AVAILABLE
        self.enable_metrics = enable_metrics and PROMETHEUS_AVAILABLE
        
        # Initialize logging
        self._setup_structured_logging()
        
        # Initialize tracing
        if self.enable_tracing:
            self._setup_distributed_tracing()
        
        # Initialize metrics
        if self.enable_metrics:
            self._setup_prometheus_metrics()
        
        # RED metrics storage (in-memory for demo, use Redis/InfluxDB in production)
        self._metrics_buffer = defaultdict(lambda: deque(maxlen=1000))
        self._slo_metrics = {}
        self._start_time = time.time()
        
        # Background metrics processor
        self._metrics_lock = threading.Lock()
        self._start_background_processor()
    
    def _setup_structured_logging(self):
        """Configure structured JSON logging."""
        # Configure Python logger for structured output
        self.logger = logging.getLogger(self.service_name)
        self.logger.setLevel(getattr(logging, self.log_level.value))
        
        # Remove default handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def _setup_distributed_tracing(self):
        """Setup OpenTelemetry distributed tracing."""
        if not TRACING_AVAILABLE:
            return
            
        # Configure tracer provider
        trace.set_tracer_provider(TracerProvider())
        
        # Setup Jaeger exporter (for demo - use OTLP in production)
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=14268,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        self.tracer = trace.get_tracer(self.service_name)
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics collection."""
        if not PROMETHEUS_AVAILABLE:
            return
            
        # RED Metrics
        self.request_total = Counter(
            'requests_total',
            'Total HTTP requests',
            ['service', 'endpoint', 'method', 'status']
        )
        
        self.request_duration = Histogram(
            'request_duration_seconds',
            'HTTP request duration',
            ['service', 'endpoint', 'method'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self.error_total = Counter(
            'errors_total',
            'Total application errors',
            ['service', 'error_type', 'severity']
        )
        
        # SLO Metrics
        self.slo_compliance = Gauge(
            'slo_compliance_percentage',
            'SLO compliance percentage',
            ['service', 'slo_name']
        )
        
        self.active_users = Gauge(
            'active_users_current',
            'Currently active users',
            ['service']
        )
    
    def _start_background_processor(self):
        """Start background thread for metrics processing."""
        def process_metrics():
            while True:
                try:
                    self._process_red_metrics()
                    self._check_slo_breaches()
                except Exception as e:
                    self.log_error("metrics_processor_error", str(e))
                time.sleep(60)  # Process every minute
        
        thread = threading.Thread(target=process_metrics, daemon=True)
        thread.start()
    
    def log_structured(
        self,
        level: LogLevel,
        message: str,
        operation: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error_type: Optional[str] = None,
        **metadata
    ):
        """Log structured entry with consistent format."""
        entry = StructuredLogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level,
            message=message,
            service=self.service_name,
            trace_id=self._get_current_trace_id(),
            span_id=self._get_current_span_id(),
            user_id=user_id,
            request_id=request_id,
            operation=operation,
            duration_ms=duration_ms,
            error_type=error_type,
            metadata=metadata if metadata else None
        )
        
        # Log to structured logger
        log_method = getattr(self.logger, level.lower())
        log_method(entry.to_json())
        
        # Update metrics if available
        if self.enable_metrics and error_type:
            self.error_total.labels(
                service=self.service_name,
                error_type=error_type,
                severity=level.lower()
            ).inc()
    
    def log_info(self, message: str, **kwargs):
        """Log info level message."""
        self.log_structured(LogLevel.INFO, message, **kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """Log warning level message."""
        self.log_structured(LogLevel.WARNING, message, **kwargs)
    
    def log_error(self, message: str, error: str = None, **kwargs):
        """Log error level message."""
        self.log_structured(
            LogLevel.ERROR, 
            message, 
            error_type=error or "application_error",
            **kwargs
        )
    
    def log_critical(self, message: str, **kwargs):
        """Log critical level message."""
        self.log_structured(LogLevel.CRITICAL, message, **kwargs)
    
    @asynccontextmanager
    async def trace_operation(
        self, 
        operation_name: str,
        user_id: Optional[str] = None,
        **attributes
    ):
        """Context manager for distributed tracing."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Start trace span if available
        span = None
        if self.enable_tracing and self.tracer:
            span = self.tracer.start_span(operation_name)
            if user_id:
                span.set_attribute("user.id", user_id)
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            self.log_info(
                f"Starting operation: {operation_name}",
                operation=operation_name,
                user_id=user_id,
                request_id=request_id,
                **attributes
            )
            
            yield request_id
            
            # Success metrics
            duration_ms = (time.time() - start_time) * 1000
            self._record_request_metric(operation_name, "success", duration_ms)
            
            self.log_info(
                f"Completed operation: {operation_name}",
                operation=operation_name,
                user_id=user_id,
                request_id=request_id,
                duration_ms=duration_ms,
                **attributes
            )
            
        except Exception as e:
            # Error metrics
            duration_ms = (time.time() - start_time) * 1000
            self._record_request_metric(operation_name, "error", duration_ms)
            
            self.log_error(
                f"Failed operation: {operation_name}",
                error=type(e).__name__,
                operation=operation_name,
                user_id=user_id,
                request_id=request_id,
                duration_ms=duration_ms,
                error_details=str(e),
                **attributes
            )
            
            if span:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
            
            raise
        finally:
            if span:
                span.end()
    
    def _record_request_metric(self, operation: str, status: str, duration_ms: float):
        """Record request metrics for RED calculation."""
        with self._metrics_lock:
            metric_key = f"{operation}:{status}"
            self._metrics_buffer[metric_key].append({
                'timestamp': time.time(),
                'duration_ms': duration_ms,
                'status': status
            })
            
            # Update Prometheus metrics if available
            if self.enable_metrics:
                self.request_total.labels(
                    service=self.service_name,
                    endpoint=operation,
                    method="POST",  # Default for operations
                    status="200" if status == "success" else "500"
                ).inc()
                
                self.request_duration.labels(
                    service=self.service_name,
                    endpoint=operation,
                    method="POST"
                ).observe(duration_ms / 1000)  # Convert to seconds
    
    def _process_red_metrics(self):
        """Process RED metrics from buffer."""
        current_time = time.time()
        window_seconds = 300  # 5 minute window
        
        with self._metrics_lock:
            for operation in set(key.split(':')[0] for key in self._metrics_buffer.keys()):
                # Collect metrics for this operation
                success_metrics = []
                error_metrics = []
                
                for status in ['success', 'error']:
                    key = f"{operation}:{status}"
                    metrics = [
                        m for m in self._metrics_buffer[key] 
                        if current_time - m['timestamp'] <= window_seconds
                    ]
                    
                    if status == 'success':
                        success_metrics = metrics
                    else:
                        error_metrics = metrics
                
                # Calculate RED metrics
                total_requests = len(success_metrics) + len(error_metrics)
                if total_requests > 0:
                    # Rate (requests per minute)
                    rate_per_minute = (total_requests / window_seconds) * 60
                    
                    # Error rate
                    error_rate = len(error_metrics) / total_requests * 100
                    
                    # Duration percentiles
                    all_durations = [m['duration_ms'] for m in success_metrics + error_metrics]
                    all_durations.sort()
                    
                    p50 = self._percentile(all_durations, 50) if all_durations else 0
                    p95 = self._percentile(all_durations, 95) if all_durations else 0
                    p99 = self._percentile(all_durations, 99) if all_durations else 0
                    
                    red_metric = REDMetrics(
                        service=self.service_name,
                        endpoint=operation,
                        rate_per_minute=rate_per_minute,
                        error_rate_percentage=error_rate,
                        p50_duration_ms=p50,
                        p95_duration_ms=p95,
                        p99_duration_ms=p99,
                        timestamp=datetime.utcnow()
                    )
                    
                    # Store for dashboard access
                    self._metrics_buffer[f"red:{operation}"] = red_metric
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile from sorted data."""
        if not data:
            return 0.0
        n = len(data)
        k = (n - 1) * percentile / 100
        f = int(k)
        c = k - f
        if f == n - 1:
            return data[f]
        return data[f] * (1 - c) + data[f + 1] * c
    
    def register_slo(
        self, 
        name: str, 
        target_percentage: float, 
        measurement_window_hours: int = 24
    ):
        """Register an SLO for monitoring."""
        self._slo_metrics[name] = SLOMetric(
            name=name,
            target_percentage=target_percentage,
            measurement_window_hours=measurement_window_hours,
            current_percentage=100.0,
            breaches_count=0
        )
        
        self.log_info(
            f"Registered SLO: {name}",
            operation="slo_registration",
            slo_name=name,
            target=target_percentage
        )
    
    def _check_slo_breaches(self):
        """Check for SLO breaches and alert."""
        for slo_name, slo in self._slo_metrics.items():
            # Calculate current SLO compliance (simplified)
            red_key = f"red:{slo_name}"
            if red_key in self._metrics_buffer:
                red_metric = self._metrics_buffer[red_key]
                if isinstance(red_metric, REDMetrics):
                    # SLO based on error rate (simplified)
                    current_success_rate = 100 - red_metric.error_rate_percentage
                    slo.current_percentage = current_success_rate
                    
                    # Check for breach
                    if current_success_rate < slo.target_percentage:
                        slo.breaches_count += 1
                        slo.last_breach = datetime.utcnow()
                        
                        self.log_critical(
                            f"SLO BREACH: {slo_name}",
                            operation="slo_breach",
                            slo_name=slo_name,
                            target=slo.target_percentage,
                            current=current_success_rate,
                            breach_count=slo.breaches_count
                        )
                        
                        # Update Prometheus gauge if available
                        if self.enable_metrics:
                            self.slo_compliance.labels(
                                service=self.service_name,
                                slo_name=slo_name
                            ).set(current_success_rate)
    
    def get_red_metrics(self, operation: Optional[str] = None) -> Dict[str, REDMetrics]:
        """Get current RED metrics."""
        results = {}
        with self._metrics_lock:
            for key, value in self._metrics_buffer.items():
                if key.startswith("red:") and isinstance(value, REDMetrics):
                    endpoint = key.replace("red:", "")
                    if operation is None or endpoint == operation:
                        results[endpoint] = value
        return results
    
    def get_slo_status(self) -> Dict[str, SLOMetric]:
        """Get current SLO status."""
        return dict(self._slo_metrics)
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get service health metrics."""
        uptime_seconds = time.time() - self._start_time
        
        return {
            "service": self.service_name,
            "uptime_seconds": uptime_seconds,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "red_metrics_count": len([k for k in self._metrics_buffer.keys() if k.startswith("red:")]),
            "slo_count": len(self._slo_metrics),
            "tracing_enabled": self.enable_tracing,
            "metrics_enabled": self.enable_metrics
        }
    
    def _get_current_trace_id(self) -> Optional[str]:
        """Get current trace ID if tracing is enabled."""
        if not self.enable_tracing or not trace:
            return None
        try:
            span_context = trace.get_current_span().get_span_context()
            return f"{span_context.trace_id:032x}" if span_context.is_valid else None
        except:
            return None
    
    def _get_current_span_id(self) -> Optional[str]:
        """Get current span ID if tracing is enabled."""
        if not self.enable_tracing or not trace:
            return None
        try:
            span_context = trace.get_current_span().get_span_context()
            return f"{span_context.span_id:016x}" if span_context.is_valid else None
        except:
            return None
    
    def export_prometheus_metrics(self) -> str:
        """Export Prometheus metrics (for /metrics endpoint)."""
        if not self.enable_metrics or not prometheus_client:
            return "# Metrics not available\n"
        return generate_latest().decode('utf-8')


# Global instance
observability = ObservabilityService()

# Convenience functions
def log_info(message: str, **kwargs):
    """Global log info function."""
    observability.log_info(message, **kwargs)

def log_error(message: str, **kwargs):
    """Global log error function."""
    observability.log_error(message, **kwargs)

def trace_operation(operation_name: str, **kwargs):
    """Global trace operation function."""
    return observability.trace_operation(operation_name, **kwargs)
