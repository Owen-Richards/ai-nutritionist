"""
Database performance monitoring dashboard and alerting system.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

from .monitoring import get_query_monitor, PerformanceMetrics, QueryMetrics
from .connection_pool import get_connection_pool, ConnectionMetrics
from .cache import get_query_cache, CacheMetrics
from .optimizations import SlowQueryDetector, IndexManager, QueryOptimizer

logger = logging.getLogger(__name__)


@dataclass
class DatabaseAlert:
    """Database performance alert."""
    
    alert_id: str
    alert_type: str
    severity: str  # "info", "warning", "error", "critical"
    message: str
    details: Dict[str, Any]
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        """Check if alert is still active."""
        return self.resolved_at is None
    
    @property
    def duration(self) -> timedelta:
        """Get alert duration."""
        end_time = self.resolved_at or datetime.utcnow()
        return end_time - self.triggered_at


@dataclass
class PerformanceSummary:
    """Summary of database performance metrics."""
    
    timestamp: datetime
    
    # Query performance
    total_queries: int
    avg_query_time_ms: float
    slow_query_count: int
    error_rate: float
    
    # Connection pool
    active_connections: int
    connection_pool_utilization: float
    connection_wait_time_ms: float
    
    # Cache performance
    cache_hit_ratio: float
    cache_size: int
    cache_evictions: int
    
    # Resource usage
    tables_accessed: int
    indexes_used: int
    scan_operations: int
    
    # Alerts
    active_alerts: int
    critical_alerts: int


class AlertManager:
    """Manages database performance alerts."""
    
    def __init__(self):
        self._active_alerts: Dict[str, DatabaseAlert] = {}
        self._alert_history: deque = deque(maxlen=1000)
        self._alert_callbacks: List[Callable[[DatabaseAlert], None]] = []
        self._alert_rules: List[Callable[[Dict[str, Any]], Optional[DatabaseAlert]]] = []
        
        # Setup default alert rules
        self._setup_default_rules()
    
    def add_alert_callback(self, callback: Callable[[DatabaseAlert], None]):
        """Add callback for alert notifications."""
        self._alert_callbacks.append(callback)
    
    def add_alert_rule(self, rule: Callable[[Dict[str, Any]], Optional[DatabaseAlert]]):
        """Add custom alert rule."""
        self._alert_rules.append(rule)
    
    async def check_alerts(self, metrics: Dict[str, Any]) -> List[DatabaseAlert]:
        """Check all alert rules against current metrics."""
        new_alerts = []
        
        for rule in self._alert_rules:
            try:
                alert = rule(metrics)
                if alert:
                    new_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error in alert rule: {e}")
        
        # Process new alerts
        for alert in new_alerts:
            await self._trigger_alert(alert)
        
        return new_alerts
    
    async def _trigger_alert(self, alert: DatabaseAlert):
        """Trigger a new alert."""
        # Check if similar alert is already active
        existing_alert = self._find_similar_alert(alert)
        
        if existing_alert:
            # Update existing alert details
            existing_alert.details.update(alert.details)
            existing_alert.message = alert.message
        else:
            # Add new alert
            self._active_alerts[alert.alert_id] = alert
            self._alert_history.append(alert)
            
            # Notify callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
            logger.warning(f"Database alert triggered: {alert.alert_type} - {alert.message}")
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.resolved_at = datetime.utcnow()
            del self._active_alerts[alert_id]
            
            logger.info(f"Database alert resolved: {alert.alert_type} (duration: {alert.duration})")
            return True
        
        return False
    
    def get_active_alerts(self) -> List[DatabaseAlert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[DatabaseAlert]:
        """Get alert history for specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self._alert_history
            if alert.triggered_at >= cutoff_time
        ]
    
    def _find_similar_alert(self, new_alert: DatabaseAlert) -> Optional[DatabaseAlert]:
        """Find similar active alert."""
        for alert in self._active_alerts.values():
            if (alert.alert_type == new_alert.alert_type and 
                alert.severity == new_alert.severity):
                return alert
        return None
    
    def _setup_default_rules(self):
        """Setup default alert rules."""
        
        def slow_query_rule(metrics: Dict[str, Any]) -> Optional[DatabaseAlert]:
            """Alert for excessive slow queries."""
            query_metrics = metrics.get("query_performance", {})
            slow_queries = query_metrics.get("slow_queries", 0)
            total_queries = query_metrics.get("total_queries", 0)
            
            if total_queries > 100:
                slow_ratio = slow_queries / total_queries
                if slow_ratio > 0.1:  # More than 10% slow queries
                    return DatabaseAlert(
                        alert_id=f"slow_queries_{int(datetime.utcnow().timestamp())}",
                        alert_type="slow_queries",
                        severity="warning",
                        message=f"High slow query ratio: {slow_ratio:.2%} ({slow_queries}/{total_queries})",
                        details={
                            "slow_queries": slow_queries,
                            "total_queries": total_queries,
                            "ratio": slow_ratio
                        },
                        triggered_at=datetime.utcnow()
                    )
            return None
        
        def connection_pool_rule(metrics: Dict[str, Any]) -> Optional[DatabaseAlert]:
            """Alert for connection pool issues."""
            pool_metrics = metrics.get("connection_pool", {})
            utilization = pool_metrics.get("utilization", 0)
            wait_time = pool_metrics.get("wait_time_ms", 0)
            
            if utilization > 0.9:  # More than 90% utilization
                return DatabaseAlert(
                    alert_id=f"pool_utilization_{int(datetime.utcnow().timestamp())}",
                    alert_type="connection_pool_high_utilization",
                    severity="warning",
                    message=f"High connection pool utilization: {utilization:.1%}",
                    details={
                        "utilization": utilization,
                        "wait_time_ms": wait_time
                    },
                    triggered_at=datetime.utcnow()
                )
            
            if wait_time > 5000:  # More than 5 seconds wait time
                return DatabaseAlert(
                    alert_id=f"pool_wait_{int(datetime.utcnow().timestamp())}",
                    alert_type="connection_pool_high_wait",
                    severity="error",
                    message=f"High connection wait time: {wait_time:.1f}ms",
                    details={
                        "wait_time_ms": wait_time,
                        "utilization": utilization
                    },
                    triggered_at=datetime.utcnow()
                )
            
            return None
        
        def cache_performance_rule(metrics: Dict[str, Any]) -> Optional[DatabaseAlert]:
            """Alert for poor cache performance."""
            cache_metrics = metrics.get("cache", {})
            hit_ratio = cache_metrics.get("hit_ratio", 0)
            
            if hit_ratio < 0.5:  # Less than 50% hit ratio
                return DatabaseAlert(
                    alert_id=f"cache_performance_{int(datetime.utcnow().timestamp())}",
                    alert_type="low_cache_hit_ratio",
                    severity="warning",
                    message=f"Low cache hit ratio: {hit_ratio:.1%}",
                    details={
                        "hit_ratio": hit_ratio,
                        "total_operations": cache_metrics.get("total_operations", 0)
                    },
                    triggered_at=datetime.utcnow()
                )
            
            return None
        
        def error_rate_rule(metrics: Dict[str, Any]) -> Optional[DatabaseAlert]:
            """Alert for high error rates."""
            query_metrics = metrics.get("query_performance", {})
            failed_queries = query_metrics.get("failed_queries", 0)
            total_queries = query_metrics.get("total_queries", 0)
            
            if total_queries > 50:
                error_rate = failed_queries / total_queries
                if error_rate > 0.05:  # More than 5% error rate
                    return DatabaseAlert(
                        alert_id=f"error_rate_{int(datetime.utcnow().timestamp())}",
                        alert_type="high_error_rate",
                        severity="error",
                        message=f"High database error rate: {error_rate:.2%} ({failed_queries}/{total_queries})",
                        details={
                            "failed_queries": failed_queries,
                            "total_queries": total_queries,
                            "error_rate": error_rate
                        },
                        triggered_at=datetime.utcnow()
                    )
            
            return None
        
        # Register default rules
        self.add_alert_rule(slow_query_rule)
        self.add_alert_rule(connection_pool_rule)
        self.add_alert_rule(cache_performance_rule)
        self.add_alert_rule(error_rate_rule)


class DatabaseDashboard:
    """
    Comprehensive database performance monitoring dashboard.
    
    Features:
    - Real-time performance metrics
    - Alert management
    - Performance trend analysis
    - Optimization recommendations
    - Resource utilization monitoring
    """
    
    def __init__(self):
        self.query_monitor = get_query_monitor()
        self.alert_manager = AlertManager()
        self.slow_query_detector = SlowQueryDetector()
        self.index_manager = IndexManager()
        self.query_optimizer = QueryOptimizer()
        
        # Performance history
        self._performance_history: deque = deque(maxlen=1440)  # 24 hours of minute-by-minute data
        
        # Background monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start background performance monitoring."""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        
        logger.info("Database performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop background performance monitoring."""
        self._is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Database performance monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int):
        """Background monitoring loop."""
        while self._is_monitoring:
            try:
                # Collect metrics
                metrics = await self.collect_metrics()
                
                # Store performance summary
                summary = self._create_performance_summary(metrics)
                self._performance_history.append(summary)
                
                # Check for alerts
                await self.alert_manager.check_alerts(metrics)
                
                # Log performance summary
                logger.debug(f"Database performance: {summary.avg_query_time_ms:.1f}ms avg, "
                           f"{summary.cache_hit_ratio:.1%} cache hit ratio, "
                           f"{summary.active_alerts} active alerts")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive database metrics."""
        metrics = {}
        
        try:
            # Query performance metrics
            query_metrics = await self.query_monitor.get_metrics()
            metrics["query_performance"] = {
                "total_queries": query_metrics.total_queries,
                "slow_queries": query_metrics.slow_queries,
                "very_slow_queries": query_metrics.very_slow_queries,
                "failed_queries": query_metrics.failed_queries,
                "avg_query_time_ms": query_metrics.avg_query_time_ms,
                "p95_query_time_ms": query_metrics.p95_query_time_ms,
                "p99_query_time_ms": query_metrics.p99_query_time_ms,
                "potential_n_plus_one": query_metrics.potential_n_plus_one
            }
            
            # Connection pool metrics
            pool = await get_connection_pool()
            pool_metrics = await pool.get_metrics()
            metrics["connection_pool"] = {
                "total_connections": pool_metrics.total_connections,
                "active_connections": pool_metrics.active_connections,
                "idle_connections": pool_metrics.idle_connections,
                "failed_connections": pool_metrics.failed_connections,
                "utilization": pool_metrics.active_connections / pool_metrics.total_connections if pool_metrics.total_connections > 0 else 0,
                "wait_time_ms": pool_metrics.connection_wait_time * 1000,
                "avg_query_time_ms": pool_metrics.avg_query_time
            }
            
            # Cache metrics
            cache = get_query_cache()
            cache_metrics = await cache.get_metrics()
            metrics["cache"] = {
                "hits": cache_metrics.hits,
                "misses": cache_metrics.misses,
                "hit_ratio": cache_metrics.hit_ratio,
                "evictions": cache_metrics.evictions,
                "errors": cache_metrics.errors,
                "total_operations": cache_metrics.total_operations,
                "avg_hit_time_ms": cache_metrics.avg_hit_time_ms,
                "avg_miss_time_ms": cache_metrics.avg_miss_time_ms
            }
            
            # Query patterns
            query_patterns = await self.query_monitor.get_query_patterns()
            metrics["query_patterns"] = query_patterns
            
            # Slow queries
            slow_queries = await self.query_monitor.get_slow_queries(limit=20)
            metrics["slow_queries"] = [
                {
                    "query_id": q.query_id,
                    "operation": q.operation,
                    "table_name": q.table_name,
                    "execution_time_ms": q.execution_time_ms,
                    "timestamp": q.timestamp.isoformat()
                }
                for q in slow_queries
            ]
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            metrics["error"] = str(e)
        
        return metrics
    
    def _create_performance_summary(self, metrics: Dict[str, Any]) -> PerformanceSummary:
        """Create performance summary from metrics."""
        query_perf = metrics.get("query_performance", {})
        pool_perf = metrics.get("connection_pool", {})
        cache_perf = metrics.get("cache", {})
        
        active_alerts = len(self.alert_manager.get_active_alerts())
        critical_alerts = len([
            alert for alert in self.alert_manager.get_active_alerts()
            if alert.severity == "critical"
        ])
        
        return PerformanceSummary(
            timestamp=datetime.utcnow(),
            total_queries=query_perf.get("total_queries", 0),
            avg_query_time_ms=query_perf.get("avg_query_time_ms", 0),
            slow_query_count=query_perf.get("slow_queries", 0),
            error_rate=query_perf.get("failed_queries", 0) / max(query_perf.get("total_queries", 1), 1),
            active_connections=pool_perf.get("active_connections", 0),
            connection_pool_utilization=pool_perf.get("utilization", 0),
            connection_wait_time_ms=pool_perf.get("wait_time_ms", 0),
            cache_hit_ratio=cache_perf.get("hit_ratio", 0),
            cache_size=0,  # Would need to implement cache size tracking
            cache_evictions=cache_perf.get("evictions", 0),
            tables_accessed=len(set(pattern.get("table_name", "") for pattern in metrics.get("query_patterns", {}).values())),
            indexes_used=0,  # Would need to implement index usage tracking
            scan_operations=sum(1 for pattern in metrics.get("query_patterns", {}).values() if "scan" in pattern.get("operation", "").lower()),
            active_alerts=active_alerts,
            critical_alerts=critical_alerts
        )
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        current_metrics = await self.collect_metrics()
        
        # Get performance trends
        recent_summaries = list(self._performance_history)[-60:]  # Last hour
        
        trends = {}
        if len(recent_summaries) > 1:
            first = recent_summaries[0]
            last = recent_summaries[-1]
            
            trends = {
                "query_time_trend": (last.avg_query_time_ms - first.avg_query_time_ms) / max(first.avg_query_time_ms, 1),
                "cache_hit_trend": last.cache_hit_ratio - first.cache_hit_ratio,
                "error_rate_trend": last.error_rate - first.error_rate,
                "connection_utilization_trend": last.connection_pool_utilization - first.connection_pool_utilization
            }
        
        # Get optimization recommendations
        recommendations = await self._generate_recommendations(current_metrics)
        
        return {
            "current_metrics": current_metrics,
            "performance_history": [
                {
                    "timestamp": summary.timestamp.isoformat(),
                    "avg_query_time_ms": summary.avg_query_time_ms,
                    "cache_hit_ratio": summary.cache_hit_ratio,
                    "active_connections": summary.active_connections,
                    "error_rate": summary.error_rate
                }
                for summary in recent_summaries
            ],
            "trends": trends,
            "active_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "duration_seconds": alert.duration.total_seconds()
                }
                for alert in self.alert_manager.get_active_alerts()
            ],
            "recommendations": recommendations,
            "summary": {
                "total_queries_last_hour": sum(s.total_queries for s in recent_summaries),
                "avg_response_time": sum(s.avg_query_time_ms for s in recent_summaries) / max(len(recent_summaries), 1),
                "uptime_percentage": 100.0 - (sum(s.error_rate for s in recent_summaries) / max(len(recent_summaries), 1) * 100),
                "cache_efficiency": sum(s.cache_hit_ratio for s in recent_summaries) / max(len(recent_summaries), 1)
            }
        }
    
    async def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on metrics."""
        recommendations = []
        
        query_perf = metrics.get("query_performance", {})
        cache_perf = metrics.get("cache", {})
        pool_perf = metrics.get("connection_pool", {})
        
        # Query performance recommendations
        if query_perf.get("avg_query_time_ms", 0) > 500:
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "title": "High Average Query Time",
                "description": f"Average query time is {query_perf.get('avg_query_time_ms', 0):.1f}ms",
                "actions": [
                    "Review slow queries and add appropriate indexes",
                    "Consider query optimization and result caching",
                    "Analyze query patterns for N+1 issues"
                ]
            })
        
        # Cache recommendations
        if cache_perf.get("hit_ratio", 0) < 0.7:
            recommendations.append({
                "type": "caching",
                "priority": "medium",
                "title": "Low Cache Hit Ratio",
                "description": f"Cache hit ratio is {cache_perf.get('hit_ratio', 0):.1%}",
                "actions": [
                    "Review cache key strategy and TTL settings",
                    "Identify frequently accessed data for caching",
                    "Consider pre-warming cache for critical queries"
                ]
            })
        
        # Connection pool recommendations
        if pool_perf.get("utilization", 0) > 0.8:
            recommendations.append({
                "type": "infrastructure",
                "priority": "high",
                "title": "High Connection Pool Utilization",
                "description": f"Connection pool utilization is {pool_perf.get('utilization', 0):.1%}",
                "actions": [
                    "Consider increasing connection pool size",
                    "Review connection leak issues",
                    "Optimize query execution times"
                ]
            })
        
        # N+1 query recommendations
        if query_perf.get("potential_n_plus_one", 0) > 5:
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "title": "Potential N+1 Query Issues",
                "description": f"Detected {query_perf.get('potential_n_plus_one', 0)} potential N+1 query patterns",
                "actions": [
                    "Implement batch loading for related data",
                    "Use eager loading strategies",
                    "Review data access patterns"
                ]
            })
        
        return recommendations


# Global dashboard instance
_dashboard: Optional[DatabaseDashboard] = None


async def get_database_dashboard() -> DatabaseDashboard:
    """Get the global database dashboard instance."""
    global _dashboard
    
    if _dashboard is None:
        _dashboard = DatabaseDashboard()
        await _dashboard.start_monitoring()
    
    return _dashboard
