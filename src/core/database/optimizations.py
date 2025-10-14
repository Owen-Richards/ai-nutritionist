"""
Database query optimizations and performance tools.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Callable, TypeVar, Generic, Sequence, Mapping, Iterable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
import hashlib
import json

from .abstractions import Repository, Specification, QueryBuilder
from .monitoring import QueryMonitor, QueryEvent
from .cache import QueryCache

logger = logging.getLogger(__name__)

ID = TypeVar("ID")
T = TypeVar("T")
Related = TypeVar("Related")


@dataclass
class IndexRecommendation:
    """Recommendation for database index creation."""
    
    table_name: str
    columns: List[str]
    index_type: str  # "primary", "gsi", "lsi", "composite"
    reason: str
    estimated_improvement: float  # Percentage improvement estimate
    usage_frequency: int
    query_patterns: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BatchOperation:
    """Represents a batch operation for optimization."""
    
    operation_type: str
    items: List[Any]
    table_name: str
    batch_size: int = 25
    retry_count: int = 0
    max_retries: int = 3


class BatchLoader:
    """
    Batch fetch helper used to eradicate N+1 query patterns.
    
    Features:
    - Automatic batching of similar queries
    - Deduplication of requests
    - Result caching
    - Performance monitoring
    """

    def __init__(
        self,
        fetch_fn: Callable[[Sequence[ID]], Mapping[ID, T]],
        *,
        batch_size: int = 50,
        cache_results: bool = True,
    ) -> None:
        self._fetch_fn = fetch_fn
        self._batch_size = max(1, batch_size)
        self._cache_results = cache_results
        self._cache: Dict[ID, T] = {}
        
        # Performance tracking
        self._batches_executed = 0
        self._items_loaded = 0
        self._cache_hits = 0

    def load(self, key: ID) -> Optional[T]:
        """Load single item with caching."""
        if self._cache_results and key in self._cache:
            self._cache_hits += 1
            return self._cache[key]
        results = self.load_many([key])
        return results.get(key)

    def load_many(self, keys: Sequence[ID]) -> Mapping[ID, T]:
        """Load multiple items in optimized batches."""
        # Check cache first
        uncached_keys = []
        results = {}
        
        if self._cache_results:
            for key in keys:
                if key in self._cache:
                    results[key] = self._cache[key]
                    self._cache_hits += 1
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = list(keys)
        
        # Fetch uncached items in batches
        for i in range(0, len(uncached_keys), self._batch_size):
            batch_keys = uncached_keys[i:i + self._batch_size]
            try:
                batch_results = self._fetch_fn(batch_keys)
                results.update(batch_results)
                
                # Update cache
                if self._cache_results:
                    self._cache.update(batch_results)
                
                self._batches_executed += 1
                self._items_loaded += len(batch_results)
                
            except Exception as e:
                logger.error(f"Batch load failed: {e}")
                raise
        
        return results

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get batch loader performance statistics."""
        return {
            "batches_executed": self._batches_executed,
            "items_loaded": self._items_loaded,
            "cache_hits": self._cache_hits,
            "cache_size": len(self._cache),
            "avg_items_per_batch": (
                self._items_loaded / self._batches_executed 
                if self._batches_executed > 0 else 0
            )
        }


class EagerLoader:
    """Helper for eager loading related entities to avoid N+1 patterns."""
    
    def __init__(self):
        self._loaders: Dict[str, BatchLoader] = {}
    
    def register_loader(self, name: str, loader: BatchLoader):
        """Register a batch loader for a specific relationship."""
        self._loaders[name] = loader
    
    def load_related(self, loader_name: str, parent_ids: List[ID]) -> Mapping[ID, List[Related]]:
        """Load related entities for multiple parent entities."""
        if loader_name not in self._loaders:
            raise ValueError(f"No loader registered for {loader_name}")
        
        loader = self._loaders[loader_name]
        return loader.load_many(parent_ids)


class QueryOptimizer:
    """
    Analyzes and optimizes database queries.
    
    Features:
    - Query pattern analysis
    - Index recommendations
    - Query rewriting suggestions
    - Performance optimization hints
    """
    
    def __init__(self):
        self._query_patterns: Dict[str, Dict[str, Any]] = {}
        self._index_recommendations: List[IndexRecommendation] = []
        self._optimization_cache: Dict[str, Dict[str, Any]] = {}
        
    def analyze_query_pattern(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query pattern and provide optimization suggestions."""
        pattern_key = f"{metrics.table_name}:{metrics.operation}"
        
        # Track pattern
        if pattern_key not in self._query_patterns:
            self._query_patterns[pattern_key] = {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0,
                "parameters": set(),
                "first_seen": metrics.timestamp,
                "last_seen": metrics.timestamp
            }
        
        pattern = self._query_patterns[pattern_key]
        pattern["count"] += 1
        pattern["total_time"] += metrics.execution_time_ms
        pattern["avg_time"] = pattern["total_time"] / pattern["count"]
        pattern["max_time"] = max(pattern["max_time"], metrics.execution_time_ms)
        pattern["last_seen"] = metrics.timestamp
        
        # Add parameter keys (not values for privacy)
        pattern["parameters"].update(metrics.parameters.keys())
        
        # Analyze for optimization opportunities
        optimizations = []
        
        # Check for slow queries
        if metrics.execution_time_ms > 1000:
            optimizations.append({
                "type": "slow_query",
                "description": "Query execution time exceeds 1 second",
                "suggestions": [
                    "Consider adding indexes on frequently queried fields",
                    "Review query filters and projections",
                    "Consider query result caching"
                ]
            })
        
        # Check for frequent queries
        if pattern["count"] > 100:
            optimizations.append({
                "type": "frequent_query",
                "description": f"Query executed {pattern['count']} times",
                "suggestions": [
                    "Consider caching results",
                    "Review if query can be batched",
                    "Consider denormalizing data if appropriate"
                ]
            })
        
        return {
            "pattern": pattern,
            "optimizations": optimizations,
            "recommendations": self._generate_recommendations(metrics, pattern)
        }
    
    def _generate_recommendations(
        self, 
        metrics: Dict[str, Any], 
        pattern: Dict[str, Any]
    ) -> List[str]:
        """Generate specific optimization recommendations."""
        recommendations = []
        
        # Performance-based recommendations
        if pattern["avg_time"] > 500:
            recommendations.append(
                f"Average query time ({pattern['avg_time']:.2f}ms) is high. "
                "Consider optimizing query or adding indexes."
            )
        
        # Frequency-based recommendations
        if pattern["count"] > 50:
            recommendations.append(
                f"Query is executed frequently ({pattern['count']} times). "
                "Consider caching results or optimizing the query."
            )
        
        # DynamoDB-specific recommendations
        if metrics.table_name.startswith("ai-nutritionist"):
            if "scan" in metrics.operation.lower():
                recommendations.append(
                    "Scan operations are expensive. Consider using Query with proper key conditions."
                )
            
            if len(metrics.parameters) > 3:
                recommendations.append(
                    "Complex filter conditions may indicate need for a GSI (Global Secondary Index)."
                )
        
        return recommendations


class IndexManager:
    """
    Manages database index recommendations and optimization.
    
    Features:
    - Index usage analysis
    - Performance impact measurement
    - Automatic index recommendations
    - Index effectiveness monitoring
    """
    
    def __init__(self):
        self._index_usage: Dict[str, Dict[str, Any]] = {}
        self._index_performance: Dict[str, List[float]] = defaultdict(list)
        
    def track_index_usage(self, table_name: str, index_name: str, query_time: float):
        """Track index usage and performance."""
        key = f"{table_name}:{index_name}"
        
        if key not in self._index_usage:
            self._index_usage[key] = {
                "usage_count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "last_used": datetime.utcnow()
            }
        
        usage = self._index_usage[key]
        usage["usage_count"] += 1
        usage["total_time"] += query_time
        usage["avg_time"] = usage["total_time"] / usage["usage_count"]
        usage["last_used"] = datetime.utcnow()
        
        # Track performance history
        self._index_performance[key].append(query_time)
        if len(self._index_performance[key]) > 100:
            self._index_performance[key].pop(0)
    
    def get_index_effectiveness(self, table_name: str, index_name: str) -> Dict[str, Any]:
        """Get effectiveness metrics for an index."""
        key = f"{table_name}:{index_name}"
        
        if key not in self._index_usage:
            return {"effectiveness": "unknown", "reason": "No usage data"}
        
        usage = self._index_usage[key]
        performance_history = self._index_performance[key]
        
        # Calculate effectiveness score
        effectiveness_score = 0.0
        
        # Factor 1: Usage frequency (max 40 points)
        if usage["usage_count"] > 100:
            effectiveness_score += 40
        elif usage["usage_count"] > 50:
            effectiveness_score += 30
        elif usage["usage_count"] > 10:
            effectiveness_score += 20
        else:
            effectiveness_score += 10
        
        # Factor 2: Performance consistency (max 30 points)
        if len(performance_history) > 5:
            avg_time = sum(performance_history) / len(performance_history)
            std_dev = (sum((t - avg_time) ** 2 for t in performance_history) / len(performance_history)) ** 0.5
            
            # Lower standard deviation is better
            consistency_score = max(0, 30 - (std_dev / avg_time * 100))
            effectiveness_score += consistency_score
        
        # Factor 3: Recent usage (max 30 points)
        days_since_use = (datetime.utcnow() - usage["last_used"]).days
        if days_since_use == 0:
            effectiveness_score += 30
        elif days_since_use <= 7:
            effectiveness_score += 20
        elif days_since_use <= 30:
            effectiveness_score += 10
        
        # Determine effectiveness level
        if effectiveness_score >= 80:
            effectiveness = "high"
        elif effectiveness_score >= 60:
            effectiveness = "medium"
        elif effectiveness_score >= 40:
            effectiveness = "low"
        else:
            effectiveness = "poor"
        
        return {
            "effectiveness": effectiveness,
            "score": effectiveness_score,
            "usage_count": usage["usage_count"],
            "avg_query_time": usage["avg_time"],
            "last_used": usage["last_used"]
        }


class SlowQueryDetector:
    """
    Detects and analyzes slow database queries.
    
    Features:
    - Real-time slow query detection
    - Query pattern analysis
    - Performance regression detection
    - Alerting for performance issues
    """
    
    def __init__(self, slow_threshold_ms: float = 1000.0):
        self.slow_threshold_ms = slow_threshold_ms
        self._slow_queries: deque = deque(maxlen=100)
        self._query_baselines: Dict[str, float] = {}
        self._alert_callbacks: List[Callable] = []
        
    def add_alert_callback(self, callback: Callable):
        """Add callback for slow query alerts."""
        self._alert_callbacks.append(callback)
    
    def analyze_query(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query for performance issues."""
        analysis = {
            "is_slow": False,
            "is_regression": False,
            "severity": "normal",
            "recommendations": []
        }
        
        # Check if query is slow
        if metrics.execution_time_ms > self.slow_threshold_ms:
            analysis["is_slow"] = True
            analysis["severity"] = "slow"
            
            # Very slow queries
            if metrics.execution_time_ms > self.slow_threshold_ms * 5:
                analysis["severity"] = "very_slow"
            
            # Add to slow query log
            self._slow_queries.append({
                "timestamp": metrics.timestamp,
                "query_id": metrics.query_id,
                "operation": metrics.operation,
                "table_name": metrics.table_name,
                "execution_time_ms": metrics.execution_time_ms,
                "parameters": metrics.parameters
            })
            
            # Generate recommendations
            analysis["recommendations"].extend([
                "Review query efficiency and consider optimization",
                "Check if appropriate indexes exist",
                "Consider caching if query is frequently executed"
            ])
        
        # Check for performance regression
        query_signature = f"{metrics.operation}:{metrics.table_name}"
        baseline = self._query_baselines.get(query_signature)
        
        if baseline:
            regression_threshold = baseline * 2.0  # 100% increase
            if metrics.execution_time_ms > regression_threshold:
                analysis["is_regression"] = True
                analysis["severity"] = "regression"
        
        # Update baseline (exponential moving average)
        if baseline:
            self._query_baselines[query_signature] = (
                baseline * 0.9 + metrics.execution_time_ms * 0.1
            )
        else:
            self._query_baselines[query_signature] = metrics.execution_time_ms
        
        # Trigger alerts if necessary
        if analysis["is_slow"] or analysis["is_regression"]:
            for callback in self._alert_callbacks:
                try:
                    callback(metrics, analysis)
                except Exception as e:
                    logger.error(f"Error in slow query alert callback: {e}")
        
        return analysis
        unique_keys = list(dict.fromkeys(keys))
        missing = [key for key in unique_keys if key not in self._cache]
        for chunk_start in range(0, len(missing), self._batch_size):
            chunk = missing[chunk_start : chunk_start + self._batch_size]
            if not chunk:
                continue
            fetched = self._fetch_fn(chunk)
            if self._cache_results:
                self._cache.update(fetched)
        return {key: self._cache[key] for key in unique_keys if key in self._cache}

    def prime(self, mapping: Mapping[ID, T]) -> None:
        if self._cache_results:
            self._cache.update(mapping)

    def clear(self) -> None:
        self._cache.clear()


class EagerLoader:
    """Coordinates eager loading of one-to-many or one-to-one relations."""

    def __init__(
        self,
        foreign_key_fn: Callable[[T], ID],
        fetch_related: Callable[[Sequence[ID]], Mapping[ID, Sequence[Related]]],
        *,
        assign: Callable[[T, Sequence[Related]], None],
        batch_size: int = 100,
    ) -> None:
        self._foreign_key_fn = foreign_key_fn
        self._assign = assign
        self._loader = BatchLoader(fetch_related, batch_size=batch_size, cache_results=False)

    def load(self, parents: Sequence[T]) -> None:
        keys = [self._foreign_key_fn(parent) for parent in parents]
        related = self._loader.load_many(keys)
        for parent, key in zip(parents, keys):
            self._assign(parent, related.get(key, ()))


@dataclass(slots=True)
class OptimizerFinding:
    level: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class QueryOptimizer:
    """Inspects queries for common anti-patterns and surfaces remedies."""

    def __init__(
        self,
        *,
        cache: Optional[QueryCache] = None,
        monitor: Optional[QueryMonitor] = None,
        max_select_all_rows: int = 500,
    ) -> None:
        self._cache = cache
        self._monitor = monitor
        self._max_select_all_rows = max_select_all_rows

    def optimize(self, builder: QueryBuilder[Any], *, expected_rows: Optional[int] = None) -> List[OptimizerFinding]:
        findings: List[OptimizerFinding] = []
        plan = builder.render()

        if not builder.prefetch_relations and self._has_join(plan):
            findings.append(OptimizerFinding(level="warning", message="Potential N+1 query detected", details={"plan": plan}))

        projected_rows = expected_rows if expected_rows is not None else self._max_select_all_rows
        if self._selects_all(plan) and projected_rows > self._max_select_all_rows:
            findings.append(OptimizerFinding(level="critical", message="Wide select without limit", details={"plan": plan}))

        if expected_rows and expected_rows > self._max_select_all_rows and builder.prefetch_relations:
            findings.append(OptimizerFinding(level="info", message="Consider pagination for large result sets", details={"expected_rows": expected_rows}))

        if self._cache and self._should_cache(plan):
            findings.append(OptimizerFinding(level="info", message="Candidate for query caching", details={"cache_strategy": self._cache.stats()}))

        if findings and self._monitor:
            self._monitor.record(plan, duration=0.0, rowcount=expected_rows, origin="optimizer_dry_run")

        if any(f.level == "critical" for f in findings):
            raise QueryPerformanceError("Critical query issues detected")
        return findings

    def _has_join(self, plan: Dict[str, Any]) -> bool:
        return any(step["operation"] == "join" for step in plan["plan"])

    def _selects_all(self, plan: Dict[str, Any]) -> bool:
        columns = plan.get("select")
        return not columns or "*" in columns

    def _should_cache(self, plan: Dict[str, Any]) -> bool:
        has_filters = any(step["operation"] == "where" for step in plan["plan"])
        has_limit = any(step["operation"] == "limit" for step in plan["plan"])
        return has_filters and has_limit


class IndexManager:
    """Tracks index usage and surfaces recommended additions."""

    def __init__(self) -> None:
        self._access_patterns: Dict[str, List[Tuple[str, ...]]] = {}
        self._existing: Dict[str, List[Tuple[str, ...]]] = {}

    def register_existing(self, table: str, columns: Sequence[str]) -> None:
        self._existing.setdefault(table, []).append(tuple(columns))

    def record_access(self, table: str, *, filters: Iterable[str], order_by: Iterable[str] = ()) -> None:
        pattern = tuple(sorted(set(filters)) | set(order_by))
        if not pattern:
            return
        self._access_patterns.setdefault(table, []).append(pattern)

    def recommendations(self) -> Dict[str, List[Tuple[str, ...]]]:
        suggestions: Dict[str, List[Tuple[str, ...]]] = {}
        for table, patterns in self._access_patterns.items():
            seen = set(self._existing.get(table, []))
            freq: Dict[Tuple[str, ...], int] = {}
            for pattern in patterns:
                freq[pattern] = freq.get(pattern, 0) + 1
            ranked = sorted(freq.items(), key=lambda item: item[1], reverse=True)
            for pattern, occurrence in ranked:
                if pattern in seen:
                    continue
                suggestions.setdefault(table, []).append(pattern)
                seen.add(pattern)
        return suggestions


class SlowQueryDetector:
    """Listens for slow events and forwards actionable context."""

    def __init__(self, monitor: QueryMonitor, *, threshold: float = 0.3) -> None:
        self._threshold = threshold
        self._monitor = monitor
        monitor.register_slow_query_handler(self._handle)

    def _handle(self, event: QueryEvent) -> None:
        if event.duration < self._threshold:
            return
        logger.error(
            "database.slow_query.detected",
            extra={
                "duration": event.duration,
                "payload": event.payload,
                "origin": event.origin,
                "rows": event.rowcount,
            },
        )

