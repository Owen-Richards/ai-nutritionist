"""Monitoring helpers for observability around database queries."""

from __future__ import annotations

import logging
import statistics
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

__all__ = ["PerformanceMetrics", "QueryEvent", "QueryMonitor"]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PerformanceMetrics:
    total_queries: int = 0
    slow_queries: int = 0
    total_duration: float = 0.0
    max_duration: float = 0.0
    p95_duration: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        avg = self.total_duration / self.total_queries if self.total_queries else 0.0
        return {
            "total_queries": self.total_queries,
            "slow_queries": self.slow_queries,
            "max_duration": self.max_duration,
            "avg_duration": avg,
            "p95_duration": self.p95_duration,
        }


@dataclass(slots=True)
class QueryEvent:
    payload: Dict[str, Any]
    duration: float
    rowcount: Optional[int]
    origin: str
    timestamp: float


class QueryMonitor:
    """Records query diagnostics and emits slow query notifications."""

    def __init__(self, *, slow_threshold: float = 0.3, retention: int = 1000) -> None:
        self._slow_threshold = slow_threshold
        self._retention = retention
        self._events: List[QueryEvent] = []
        self._lock = threading.Lock()
        self._slow_handlers: List[Callable[[QueryEvent], None]] = []

    def register_slow_query_handler(self, handler: Callable[[QueryEvent], None]) -> None:
        self._slow_handlers.append(handler)

    def record(self, payload: Dict[str, Any], *, duration: float, rowcount: Optional[int], origin: str) -> None:
        event = QueryEvent(payload=payload, duration=duration, rowcount=rowcount, origin=origin, timestamp=time.time())
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._retention:
                del self._events[:-self._retention]
        if duration >= self._slow_threshold:
            self._emit_slow(event)

    def metrics(self) -> PerformanceMetrics:
        with self._lock:
            events = list(self._events)
        metrics = PerformanceMetrics()
        metrics.total_queries = len(events)
        if not events:
            return metrics
        durations = [event.duration for event in events]
        metrics.total_duration = sum(durations)
        metrics.max_duration = max(durations)
        metrics.slow_queries = sum(1 for event in events if event.duration >= self._slow_threshold)
        try:
            metrics.p95_duration = statistics.quantiles(durations, n=100)[94]
        except (statistics.StatisticsError, IndexError):
            metrics.p95_duration = metrics.max_duration
        return metrics

    def recent(self, *, limit: int = 20) -> Sequence[QueryEvent]:
        with self._lock:
            return tuple(self._events[-limit:])

    def _emit_slow(self, event: QueryEvent) -> None:
        logger.warning(
            "database.slow_query",
            extra={
                "duration": event.duration,
                "payload": event.payload,
                "origin": event.origin,
                "rows": event.rowcount,
            },
        )
        for handler in self._slow_handlers:
            try:
                handler(event)
            except Exception:  # pragma: no cover - defensive
                logger.exception("Slow query handler failed")

    async def track_operation(self, operation_name: str, metadata: Dict[str, Any] = None):
        """Context manager for tracking database operations."""
        return QueryOperationTracker(self, operation_name, metadata or {})

    async def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.metrics()

    async def get_query_patterns(self) -> List[Dict[str, Any]]:
        """Get query patterns for analysis."""
        with self._lock:
            events = list(self._events)
        
        patterns = {}
        for event in events:
            # Simple pattern detection based on operation type
            operation_type = event.payload.get('operation', 'unknown')
            table_name = event.payload.get('table_name', 'unknown')
            pattern_key = f"{operation_type}:{table_name}"
            
            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    'pattern': pattern_key,
                    'count': 0,
                    'total_duration': 0.0,
                    'avg_duration': 0.0,
                    'potential_n_plus_one': False
                }
            
            patterns[pattern_key]['count'] += 1
            patterns[pattern_key]['total_duration'] += event.duration
            patterns[pattern_key]['avg_duration'] = patterns[pattern_key]['total_duration'] / patterns[pattern_key]['count']
            
            # Simple N+1 detection: many queries of same pattern in short time
            if patterns[pattern_key]['count'] > 10:
                patterns[pattern_key]['potential_n_plus_one'] = True
        
        return list(patterns.values())


class QueryOperationTracker:
    """Context manager for tracking database operations."""
    
    def __init__(self, monitor: QueryMonitor, operation_name: str, metadata: Dict[str, Any]):
        self.monitor = monitor
        self.operation_name = operation_name
        self.metadata = metadata
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            payload = {
                'operation': self.operation_name,
                **self.metadata
            }
            self.monitor.record(payload, duration=duration, rowcount=None, origin="tracked_operation")

