"""
Metrics collection framework for structured monitoring.

Provides:
- Counter, Gauge, and Histogram metrics
- CloudWatch metrics integration
- Performance tracking
- Business metrics
"""

import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

from .logging import StructuredLogger, LogLevel, EventType


class MetricType:
    """Metric type constants."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricValue:
    """A metric value with metadata."""
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


class MetricCollector(ABC):
    """Abstract base class for metric collectors."""
    
    @abstractmethod
    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush buffered metrics."""
        pass


class InMemoryMetricCollector(MetricCollector):
    """In-memory metric collector for testing and development."""
    
    def __init__(self):
        self.metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        with self._lock:
            metric_value = MetricValue(value=value, tags=tags or {})
            self.metrics[name].append(metric_value)
    
    def flush(self) -> None:
        """Flush metrics (no-op for in-memory)."""
        pass
    
    def get_metrics(self, name: str) -> List[MetricValue]:
        """Get recorded metrics for a name."""
        with self._lock:
            return self.metrics[name].copy()
    
    def clear(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self.metrics.clear()


class CloudWatchMetricCollector(MetricCollector):
    """CloudWatch metric collector."""
    
    def __init__(self, namespace: str, region: str = "us-east-1", buffer_size: int = 20):
        self.namespace = namespace
        self.region = region
        self.buffer_size = buffer_size
        self._client = None
        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.logger = StructuredLogger()
    
    @property
    def client(self):
        """Lazy initialization of CloudWatch client."""
        if self._client is None:
            self._client = boto3.client('cloudwatch', region_name=self.region)
        return self._client
    
    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        dimensions = []
        if tags:
            dimensions = [{"Name": k, "Value": v} for k, v in tags.items()]
        
        metric_data = {
            "MetricName": name,
            "Value": value,
            "Unit": "Count",
            "Timestamp": datetime.now(timezone.utc),
            "Dimensions": dimensions
        }
        
        with self._lock:
            self._buffer.append(metric_data)
            if len(self._buffer) >= self.buffer_size:
                self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """Flush the metric buffer to CloudWatch."""
        if not self._buffer:
            return
        
        try:
            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=self._buffer
            )
            self.logger.debug(f"Flushed {len(self._buffer)} metrics to CloudWatch")
            self._buffer.clear()
        except Exception as e:
            self.logger.error(f"Failed to flush metrics to CloudWatch: {e}")
    
    def flush(self) -> None:
        """Manually flush buffered metrics."""
        with self._lock:
            self._flush_buffer()


class Counter:
    """Counter metric that only increases."""
    
    def __init__(self, name: str, description: str = "", collector: Optional[MetricCollector] = None):
        self.name = name
        self.description = description
        self.collector = collector or InMemoryMetricCollector()
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self, amount: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment the counter."""
        if amount < 0:
            raise ValueError("Counter increment must be non-negative")
        
        with self._lock:
            self._value += amount
        
        self.collector.record(self.name, amount, tags)
    
    def get_value(self) -> float:
        """Get current counter value."""
        with self._lock:
            return self._value
    
    def reset(self) -> None:
        """Reset counter to zero."""
        with self._lock:
            self._value = 0


class Gauge:
    """Gauge metric that can increase or decrease."""
    
    def __init__(self, name: str, description: str = "", collector: Optional[MetricCollector] = None):
        self.name = name
        self.description = description
        self.collector = collector or InMemoryMetricCollector()
        self._value = 0
        self._lock = threading.Lock()
    
    def set(self, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set the gauge value."""
        with self._lock:
            self._value = value
        
        self.collector.record(self.name, value, tags)
    
    def increment(self, amount: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment the gauge."""
        with self._lock:
            self._value += amount
            new_value = self._value
        
        self.collector.record(self.name, new_value, tags)
    
    def decrement(self, amount: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Decrement the gauge."""
        self.increment(-amount, tags)
    
    def get_value(self) -> float:
        """Get current gauge value."""
        with self._lock:
            return self._value


class Histogram:
    """Histogram metric for tracking distributions."""
    
    def __init__(self, name: str, description: str = "", collector: Optional[MetricCollector] = None):
        self.name = name
        self.description = description
        self.collector = collector or InMemoryMetricCollector()
        self._observations: List[float] = []
        self._lock = threading.Lock()
    
    def observe(self, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Observe a value."""
        with self._lock:
            self._observations.append(value)
        
        # Record individual observation
        self.collector.record(f"{self.name}_observation", value, tags)
        
        # Record summary statistics periodically
        if len(self._observations) % 100 == 0:  # Every 100 observations
            self._record_summary(tags)
    
    def _record_summary(self, tags: Optional[Dict[str, str]] = None) -> None:
        """Record summary statistics."""
        with self._lock:
            if not self._observations:
                return
            
            observations = self._observations.copy()
        
        observations.sort()
        count = len(observations)
        
        # Record count
        self.collector.record(f"{self.name}_count", count, tags)
        
        # Record percentiles
        percentiles = [50, 90, 95, 99]
        for p in percentiles:
            index = int((p / 100) * count)
            if index >= count:
                index = count - 1
            value = observations[index]
            self.collector.record(f"{self.name}_p{p}", value, tags)
        
        # Record min/max
        self.collector.record(f"{self.name}_min", observations[0], tags)
        self.collector.record(f"{self.name}_max", observations[-1], tags)
        
        # Record average
        avg = sum(observations) / count
        self.collector.record(f"{self.name}_avg", avg, tags)
    
    def get_summary(self) -> Dict[str, float]:
        """Get summary statistics."""
        with self._lock:
            if not self._observations:
                return {}
            
            observations = self._observations.copy()
        
        observations.sort()
        count = len(observations)
        
        summary = {
            "count": count,
            "min": observations[0],
            "max": observations[-1],
            "avg": sum(observations) / count
        }
        
        # Add percentiles
        percentiles = [50, 90, 95, 99]
        for p in percentiles:
            index = int((p / 100) * count)
            if index >= count:
                index = count - 1
            summary[f"p{p}"] = observations[index]
        
        return summary


class MetricsRegistry:
    """Registry for managing metrics."""
    
    def __init__(self, collector: Optional[MetricCollector] = None):
        self.collector = collector or InMemoryMetricCollector()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()
    
    def counter(self, name: str, description: str = "") -> Counter:
        """Get or create a counter."""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description, self.collector)
            return self._counters[name]
    
    def gauge(self, name: str, description: str = "") -> Gauge:
        """Get or create a gauge."""
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description, self.collector)
            return self._gauges[name]
    
    def histogram(self, name: str, description: str = "") -> Histogram:
        """Get or create a histogram."""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, description, self.collector)
            return self._histograms[name]
    
    def flush_all(self) -> None:
        """Flush all metrics."""
        self.collector.flush()
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all registered metrics."""
        with self._lock:
            return {
                "counters": {name: counter.get_value() for name, counter in self._counters.items()},
                "gauges": {name: gauge.get_value() for name, gauge in self._gauges.items()},
                "histograms": {name: hist.get_summary() for name, hist in self._histograms.items()}
            }


# Global metrics registry
default_registry = MetricsRegistry()


def get_registry(collector: Optional[MetricCollector] = None) -> MetricsRegistry:
    """Get metrics registry."""
    if collector:
        return MetricsRegistry(collector)
    return default_registry


# Business metrics helpers
class BusinessMetrics:
    """Business-specific metrics tracking."""
    
    def __init__(self, registry: Optional[MetricsRegistry] = None):
        self.registry = registry or default_registry
        self.logger = StructuredLogger()
    
    def track_user_action(self, action: str, user_id: str, success: bool = True) -> None:
        """Track user action."""
        counter_name = f"user_action_{action}_total"
        tags = {"user_id": user_id, "status": "success" if success else "failure"}
        
        self.registry.counter(counter_name).increment(tags=tags)
        
        # Log business event
        self.logger.business_event(
            event_type=EventType.USER_ACTION,
            entity_type="user",
            entity_id=user_id,
            action=action,
            metadata={"success": success}
        )
    
    def track_api_request(self, endpoint: str, method: str, status_code: int, duration_ms: float) -> None:
        """Track API request metrics."""
        # Request counter
        self.registry.counter("api_requests_total").increment(
            tags={"endpoint": endpoint, "method": method, "status_code": str(status_code)}
        )
        
        # Response time histogram
        self.registry.histogram("api_response_time_ms").observe(
            duration_ms, tags={"endpoint": endpoint, "method": method}
        )
        
        # Error counter for 4xx/5xx
        if status_code >= 400:
            self.registry.counter("api_errors_total").increment(
                tags={"endpoint": endpoint, "method": method, "status_code": str(status_code)}
            )
    
    def track_database_operation(self, operation: str, table: str, duration_ms: float, success: bool = True) -> None:
        """Track database operation metrics."""
        # Operation counter
        self.registry.counter("db_operations_total").increment(
            tags={"operation": operation, "table": table, "status": "success" if success else "failure"}
        )
        
        # Operation duration
        self.registry.histogram("db_operation_duration_ms").observe(
            duration_ms, tags={"operation": operation, "table": table}
        )
        
        if not success:
            self.registry.counter("db_errors_total").increment(
                tags={"operation": operation, "table": table}
            )
    
    def track_external_api_call(self, service: str, endpoint: str, duration_ms: float, success: bool = True) -> None:
        """Track external API call metrics."""
        # External API counter
        self.registry.counter("external_api_calls_total").increment(
            tags={"service": service, "endpoint": endpoint, "status": "success" if success else "failure"}
        )
        
        # Response time
        self.registry.histogram("external_api_response_time_ms").observe(
            duration_ms, tags={"service": service, "endpoint": endpoint}
        )
        
        if not success:
            self.registry.counter("external_api_errors_total").increment(
                tags={"service": service, "endpoint": endpoint}
            )
    
    def track_business_kpi(self, kpi_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Track business KPI."""
        self.registry.gauge(f"business_kpi_{kpi_name}").set(value, tags)
        
        # Log business event
        self.logger.business_event(
            event_type=EventType.BUSINESS_EVENT,
            entity_type="kpi",
            action="update",
            metadata={"kpi_name": kpi_name, "value": value, "tags": tags or {}}
        )


# Global business metrics instance
business_metrics = BusinessMetrics()


def setup_metrics(
    namespace: str = "AI-Nutritionist",
    use_cloudwatch: bool = False,
    cloudwatch_region: str = "us-east-1"
) -> MetricsRegistry:
    """Setup metrics collection."""
    if use_cloudwatch:
        collector = CloudWatchMetricCollector(namespace, cloudwatch_region)
    else:
        collector = InMemoryMetricCollector()
    
    registry = MetricsRegistry(collector)
    
    # Replace global registry
    global default_registry, business_metrics
    default_registry = registry
    business_metrics = BusinessMetrics(registry)
    
    return registry
