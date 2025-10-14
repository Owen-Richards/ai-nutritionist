"""
Distributed tracing framework for request correlation and performance monitoring.

Provides:
- Distributed tracing with span hierarchy
- Request correlation across services
- Performance tracking
- Integration with AWS X-Ray
"""

import time
import uuid
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json

from .logging import StructuredLogger, LogLevel


class SpanStatus(Enum):
    """Span status enumeration."""
    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


@dataclass
class SpanContext:
    """Span context for distributed tracing."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Span:
    """Represents a single span in a trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.OK
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: Optional[float] = None
    
    def finish(self, status: SpanStatus = SpanStatus.OK) -> None:
        """Finish the span."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def add_tag(self, key: str, value: str) -> None:
        """Add a tag to the span."""
        self.tags[key] = value
    
    def add_log(self, message: str, level: str = "INFO", **kwargs) -> None:
        """Add a log entry to the span."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def set_error(self, error: Exception) -> None:
        """Mark span as error and add error details."""
        self.status = SpanStatus.ERROR
        self.add_tag("error", "true")
        self.add_tag("error.type", type(error).__name__)
        self.add_tag("error.message", str(error))
        self.add_log(f"Error: {error}", level="ERROR", error_type=type(error).__name__)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data


class TraceExporter(ABC):
    """Abstract base class for trace exporters."""
    
    @abstractmethod
    def export(self, spans: List[Span]) -> None:
        """Export spans."""
        pass


class ConsoleTraceExporter(TraceExporter):
    """Console trace exporter for development."""
    
    def export(self, spans: List[Span]) -> None:
        """Export spans to console."""
        for span in spans:
            print(f"Trace: {json.dumps(span.to_dict(), indent=2)}")


class LoggingTraceExporter(TraceExporter):
    """Logging trace exporter that uses structured logging."""
    
    def __init__(self):
        self.logger = StructuredLogger()
    
    def export(self, spans: List[Span]) -> None:
        """Export spans via structured logging."""
        for span in spans:
            level = LogLevel.ERROR if span.status == SpanStatus.ERROR else LogLevel.INFO
            self.logger._log(
                level=level,
                message=f"Span completed: {span.operation_name}",
                extra={
                    "trace": span.to_dict(),
                    "span_id": span.span_id,
                    "trace_id": span.trace_id,
                    "duration_ms": span.duration_ms,
                    "status": span.status.value
                }
            )


class XRayTraceExporter(TraceExporter):
    """AWS X-Ray trace exporter."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of X-Ray client."""
        if self._client is None:
            import boto3
            self._client = boto3.client('xray', region_name=self.region)
        return self._client
    
    def export(self, spans: List[Span]) -> None:
        """Export spans to AWS X-Ray."""
        if not spans:
            return
        
        try:
            trace_documents = []
            for span in spans:
                document = self._span_to_xray_document(span)
                trace_documents.append(document)
            
            self.client.put_trace_segments(
                TraceSegmentDocuments=trace_documents
            )
        except Exception as e:
            logger = StructuredLogger()
            logger.error(f"Failed to export traces to X-Ray: {e}")
    
    def _span_to_xray_document(self, span: Span) -> str:
        """Convert span to X-Ray trace document."""
        segment = {
            "id": span.span_id,
            "trace_id": span.trace_id,
            "name": span.operation_name,
            "start_time": span.start_time.timestamp(),
            "annotations": span.tags,
            "metadata": {
                "logs": span.logs
            }
        }
        
        if span.end_time:
            segment["end_time"] = span.end_time.timestamp()
        
        if span.parent_span_id:
            segment["parent_id"] = span.parent_span_id
        
        if span.status == SpanStatus.ERROR:
            segment["error"] = True
            segment["fault"] = True
        
        return json.dumps(segment)


class TraceContext:
    """Thread-local trace context."""
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def current_span(self) -> Optional[Span]:
        """Get current span."""
        return getattr(self._local, 'current_span', None)
    
    @current_span.setter
    def current_span(self, span: Optional[Span]) -> None:
        """Set current span."""
        self._local.current_span = span
    
    @property
    def trace_id(self) -> Optional[str]:
        """Get current trace ID."""
        span = self.current_span
        return span.trace_id if span else None
    
    @property
    def span_id(self) -> Optional[str]:
        """Get current span ID."""
        span = self.current_span
        return span.span_id if span else None


class Tracer:
    """Main tracer class for creating and managing spans."""
    
    def __init__(self, service_name: str = "ai-nutritionist"):
        self.service_name = service_name
        self.context = TraceContext()
        self.exporters: List[TraceExporter] = []
        self._finished_spans: List[Span] = []
        self._lock = threading.Lock()
    
    def add_exporter(self, exporter: TraceExporter) -> None:
        """Add a trace exporter."""
        self.exporters.append(exporter)
    
    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Span:
        """Start a new span."""
        # Determine parent
        if parent_span is None:
            parent_span = self.context.current_span
        
        # Generate IDs
        if parent_span:
            trace_id = parent_span.trace_id
            parent_span_id = parent_span.span_id
        else:
            trace_id = self._generate_trace_id()
            parent_span_id = None
        
        span_id = self._generate_span_id()
        
        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            tags=tags or {}
        )
        
        # Add service tag
        span.add_tag("service.name", self.service_name)
        
        return span
    
    def finish_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> None:
        """Finish a span."""
        span.finish(status)
        
        with self._lock:
            self._finished_spans.append(span)
        
        # Export immediately for now (could be batched)
        self._export_spans([span])
    
    def _export_spans(self, spans: List[Span]) -> None:
        """Export spans using all configured exporters."""
        for exporter in self.exporters:
            try:
                exporter.export(spans)
            except Exception as e:
                logger = StructuredLogger()
                logger.error(f"Trace export failed: {e}")
    
    def _generate_trace_id(self) -> str:
        """Generate a new trace ID."""
        return str(uuid.uuid4())
    
    def _generate_span_id(self) -> str:
        """Generate a new span ID."""
        return str(uuid.uuid4())
    
    @contextmanager
    def trace(
        self,
        operation_name: str,
        tags: Optional[Dict[str, str]] = None,
        parent_span: Optional[Span] = None
    ):
        """Context manager for tracing an operation."""
        span = self.start_span(operation_name, parent_span, tags)
        previous_span = self.context.current_span
        self.context.current_span = span
        
        try:
            yield span
            self.finish_span(span, SpanStatus.OK)
        except Exception as e:
            span.set_error(e)
            self.finish_span(span, SpanStatus.ERROR)
            raise
        finally:
            self.context.current_span = previous_span
    
    def get_current_context(self) -> Optional[SpanContext]:
        """Get current span context."""
        span = self.context.current_span
        if not span:
            return None
        
        return SpanContext(
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id
        )
    
    def inject_context(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into HTTP headers."""
        context = self.get_current_context()
        if not context:
            return headers
        
        headers = headers.copy()
        headers["X-Trace-Id"] = context.trace_id
        headers["X-Span-Id"] = context.span_id
        if context.parent_span_id:
            headers["X-Parent-Span-Id"] = context.parent_span_id
        
        return headers
    
    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """Extract trace context from HTTP headers."""
        trace_id = headers.get("X-Trace-Id")
        span_id = headers.get("X-Span-Id")
        parent_span_id = headers.get("X-Parent-Span-Id")
        
        if not trace_id or not span_id:
            return None
        
        return SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
    
    def start_span_from_context(
        self,
        operation_name: str,
        context: SpanContext,
        tags: Optional[Dict[str, str]] = None
    ) -> Span:
        """Start a span from extracted context."""
        span = Span(
            trace_id=context.trace_id,
            span_id=self._generate_span_id(),
            parent_span_id=context.span_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            tags=tags or {}
        )
        
        span.add_tag("service.name", self.service_name)
        return span


# Global tracer instance
default_tracer = Tracer()


def get_tracer(service_name: str = "ai-nutritionist") -> Tracer:
    """Get tracer for a service."""
    if service_name == "ai-nutritionist":
        return default_tracer
    return Tracer(service_name)


def setup_tracing(
    service_name: str = "ai-nutritionist",
    use_xray: bool = False,
    use_logging: bool = True,
    xray_region: str = "us-east-1"
) -> Tracer:
    """Setup distributed tracing."""
    tracer = get_tracer(service_name)
    
    # Add exporters
    if use_logging:
        tracer.add_exporter(LoggingTraceExporter())
    
    if use_xray:
        tracer.add_exporter(XRayTraceExporter(xray_region))
    
    # Default to console for development
    if not use_logging and not use_xray:
        tracer.add_exporter(ConsoleTraceExporter())
    
    return tracer


def trace_operation(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for tracing operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace(operation_name, tags) as span:
                # Add function metadata
                span.add_tag("function.name", func.__name__)
                span.add_tag("function.module", func.__module__)
                
                return func(*args, **kwargs)
        
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace(operation_name, tags) as span:
                # Add function metadata
                span.add_tag("function.name", func.__name__)
                span.add_tag("function.module", func.__module__)
                
                return await func(*args, **kwargs)
        
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator
