"""Monitoring and metrics for feature flags."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .models import FlagEvaluationResult, FlagContext, FlagUsageMetrics
from .service import FeatureFlagService


logger = logging.getLogger(__name__)


@dataclass
class FlagMetrics:
    """Metrics for a specific feature flag."""
    flag_key: str
    evaluation_count: int = 0
    unique_users: Set[str] = field(default_factory=set)
    variant_counts: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_latency_ms: float = 0.0
    last_evaluated: Optional[datetime] = None
    
    # Time-based metrics
    hourly_counts: Dict[str, int] = field(default_factory=dict)  # hour -> count
    daily_counts: Dict[str, int] = field(default_factory=dict)   # date -> count
    
    @property
    def unique_user_count(self) -> int:
        """Get unique user count."""
        return len(self.unique_users)
    
    @property
    def avg_latency_ms(self) -> float:
        """Get average latency in milliseconds."""
        return self.total_latency_ms / self.evaluation_count if self.evaluation_count > 0 else 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        """Get cache hit rate."""
        total_cache_ops = self.cache_hits + self.cache_misses
        return self.cache_hits / total_cache_ops if total_cache_ops > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Get error rate."""
        total_ops = self.evaluation_count + self.error_count
        return self.error_count / total_ops if total_ops > 0 else 0.0


class FlagEventLogger:
    """Logger for feature flag events."""
    
    def __init__(
        self,
        log_level: int = logging.INFO,
        include_context: bool = True,
        max_context_attrs: int = 10,
    ):
        self.logger = logging.getLogger(f"{__name__}.events")
        self.logger.setLevel(log_level)
        self.include_context = include_context
        self.max_context_attrs = max_context_attrs
    
    async def log_evaluation(
        self,
        result: FlagEvaluationResult,
        context: FlagContext,
        latency_ms: float,
        cache_hit: bool = False,
    ) -> None:
        """Log flag evaluation event."""
        event_data = {
            "event_type": "flag_evaluation",
            "flag_key": result.flag_key,
            "variant": result.variant_key,
            "value": result.value,
            "reason": result.reason,
            "is_default": result.is_default,
            "latency_ms": latency_ms,
            "cache_hit": cache_hit,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if self.include_context:
            context_data = self._sanitize_context(context)
            event_data["context"] = context_data
        
        self.logger.info(f"Flag evaluation: {event_data}")
    
    async def log_error(
        self,
        flag_key: str,
        error: Exception,
        context: Optional[FlagContext] = None,
    ) -> None:
        """Log flag evaluation error."""
        event_data = {
            "event_type": "flag_error",
            "flag_key": flag_key,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if context and self.include_context:
            event_data["context"] = self._sanitize_context(context)
        
        self.logger.error(f"Flag error: {event_data}")
    
    async def log_admin_action(
        self,
        action: str,
        flag_key: str,
        admin_user: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log administrative action."""
        event_data = {
            "event_type": "admin_action",
            "action": action,
            "flag_key": flag_key,
            "admin_user": admin_user,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if details:
            event_data["details"] = details
        
        self.logger.info(f"Admin action: {event_data}")
    
    def _sanitize_context(self, context: FlagContext) -> Dict[str, Any]:
        """Sanitize context for logging."""
        context_dict = context.model_dump()
        
        # Remove sensitive information
        sanitized = {}
        safe_attrs = [
            "user_id", "subscription_tier", "country", "user_segments",
            "timestamp", "session_id"
        ]
        
        for attr in safe_attrs:
            if attr in context_dict and context_dict[attr] is not None:
                sanitized[attr] = context_dict[attr]
        
        # Include limited custom attributes
        if context_dict.get("custom_attributes"):
            custom_attrs = dict(
                list(context_dict["custom_attributes"].items())[:self.max_context_attrs]
            )
            sanitized["custom_attributes"] = custom_attrs
        
        return sanitized


class FlagMonitoringService:
    """Service for monitoring feature flag usage and performance."""
    
    def __init__(
        self,
        flag_service: FeatureFlagService,
        event_logger: Optional[FlagEventLogger] = None,
        metrics_retention_days: int = 30,
    ):
        self.flag_service = flag_service
        self.event_logger = event_logger or FlagEventLogger()
        self.metrics_retention_days = metrics_retention_days
        
        # In-memory metrics store (would use database in production)
        self._metrics: Dict[str, FlagMetrics] = {}
        self._global_metrics = {
            "total_evaluations": 0,
            "total_errors": 0,
            "unique_flags": set(),
            "unique_users": set(),
            "uptime_start": datetime.utcnow(),
        }
        
        # Start background tasks
        self._monitoring_task = None
        self._start_monitoring()
    
    def _start_monitoring(self) -> None:
        """Start background monitoring tasks."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_old_metrics()
                await self._generate_health_report()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
    
    async def record_evaluation(
        self,
        result: FlagEvaluationResult,
        context: FlagContext,
        latency_ms: float,
        cache_hit: bool = False,
    ) -> None:
        """Record flag evaluation metrics."""
        flag_key = result.flag_key
        
        # Get or create flag metrics
        if flag_key not in self._metrics:
            self._metrics[flag_key] = FlagMetrics(flag_key=flag_key)
        
        metrics = self._metrics[flag_key]
        
        # Update metrics
        metrics.evaluation_count += 1
        metrics.total_latency_ms += latency_ms
        metrics.last_evaluated = datetime.utcnow()
        
        if cache_hit:
            metrics.cache_hits += 1
        else:
            metrics.cache_misses += 1
        
        # Track variant distribution
        variant = result.variant_key
        metrics.variant_counts[variant] = metrics.variant_counts.get(variant, 0) + 1
        
        # Track unique users
        if context.user_id:
            metrics.unique_users.add(context.user_id)
            self._global_metrics["unique_users"].add(context.user_id)
        
        # Track time-based metrics
        now = datetime.utcnow()
        hour_key = now.strftime("%Y-%m-%d-%H")
        date_key = now.strftime("%Y-%m-%d")
        
        metrics.hourly_counts[hour_key] = metrics.hourly_counts.get(hour_key, 0) + 1
        metrics.daily_counts[date_key] = metrics.daily_counts.get(date_key, 0) + 1
        
        # Update global metrics
        self._global_metrics["total_evaluations"] += 1
        self._global_metrics["unique_flags"].add(flag_key)
        
        # Log event
        await self.event_logger.log_evaluation(result, context, latency_ms, cache_hit)
    
    async def record_error(
        self,
        flag_key: str,
        error: Exception,
        context: Optional[FlagContext] = None,
    ) -> None:
        """Record flag evaluation error."""
        # Get or create flag metrics
        if flag_key not in self._metrics:
            self._metrics[flag_key] = FlagMetrics(flag_key=flag_key)
        
        self._metrics[flag_key].error_count += 1
        self._global_metrics["total_errors"] += 1
        
        # Log error
        await self.event_logger.log_error(flag_key, error, context)
    
    async def get_flag_metrics(self, flag_key: str) -> Optional[FlagMetrics]:
        """Get metrics for a specific flag."""
        return self._metrics.get(flag_key)
    
    async def get_all_flag_metrics(self) -> Dict[str, FlagMetrics]:
        """Get metrics for all flags."""
        return self._metrics.copy()
    
    async def get_global_metrics(self) -> Dict[str, Any]:
        """Get global system metrics."""
        uptime = datetime.utcnow() - self._global_metrics["uptime_start"]
        
        return {
            "total_evaluations": self._global_metrics["total_evaluations"],
            "total_errors": self._global_metrics["total_errors"],
            "unique_flags_count": len(self._global_metrics["unique_flags"]),
            "unique_users_count": len(self._global_metrics["unique_users"]),
            "uptime_seconds": uptime.total_seconds(),
            "error_rate": (
                self._global_metrics["total_errors"] / 
                max(self._global_metrics["total_evaluations"], 1)
            ),
            "flags_with_metrics": len(self._metrics),
        }
    
    async def get_top_flags(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top flags by evaluation count."""
        sorted_flags = sorted(
            self._metrics.items(),
            key=lambda item: item[1].evaluation_count,
            reverse=True
        )
        
        return [
            {
                "flag_key": flag_key,
                "evaluation_count": metrics.evaluation_count,
                "unique_users": metrics.unique_user_count,
                "avg_latency_ms": metrics.avg_latency_ms,
                "error_rate": metrics.error_rate,
            }
            for flag_key, metrics in sorted_flags[:limit]
        ]
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get system performance report."""
        if not self._metrics:
            return {"status": "no_data"}
        
        # Calculate aggregate metrics
        total_evaluations = sum(m.evaluation_count for m in self._metrics.values())
        total_errors = sum(m.error_count for m in self._metrics.values())
        avg_latency = sum(m.avg_latency_ms for m in self._metrics.values()) / len(self._metrics)
        
        # Find problematic flags
        slow_flags = [
            (key, metrics.avg_latency_ms)
            for key, metrics in self._metrics.items()
            if metrics.avg_latency_ms > 100  # >100ms is slow
        ]
        
        error_prone_flags = [
            (key, metrics.error_rate)
            for key, metrics in self._metrics.items()
            if metrics.error_rate > 0.01  # >1% error rate
        ]
        
        # Cache performance
        cache_stats = [
            (key, metrics.cache_hit_rate)
            for key, metrics in self._metrics.items()
            if metrics.cache_hits + metrics.cache_misses > 0
        ]
        avg_cache_hit_rate = (
            sum(rate for _, rate in cache_stats) / len(cache_stats)
            if cache_stats else 0.0
        )
        
        return {
            "summary": {
                "total_evaluations": total_evaluations,
                "total_errors": total_errors,
                "total_flags": len(self._metrics),
                "avg_latency_ms": avg_latency,
                "avg_cache_hit_rate": avg_cache_hit_rate,
            },
            "performance_issues": {
                "slow_flags": sorted(slow_flags, key=lambda x: x[1], reverse=True)[:5],
                "error_prone_flags": sorted(error_prone_flags, key=lambda x: x[1], reverse=True)[:5],
            },
            "recommendations": self._generate_recommendations(),
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []
        
        # Check for flags with high latency
        slow_flags = [
            key for key, metrics in self._metrics.items()
            if metrics.avg_latency_ms > 50
        ]
        if slow_flags:
            recommendations.append(
                f"Consider optimizing {len(slow_flags)} flags with high latency (>50ms)"
            )
        
        # Check for flags with low cache hit rates
        low_cache_flags = [
            key for key, metrics in self._metrics.items()
            if metrics.cache_hit_rate < 0.8 and metrics.cache_hits + metrics.cache_misses > 100
        ]
        if low_cache_flags:
            recommendations.append(
                f"Improve caching for {len(low_cache_flags)} flags with low hit rates (<80%)"
            )
        
        # Check for flags with high error rates
        error_flags = [
            key for key, metrics in self._metrics.items()
            if metrics.error_rate > 0.005
        ]
        if error_flags:
            recommendations.append(
                f"Investigate {len(error_flags)} flags with high error rates (>0.5%)"
            )
        
        # Check for unused flags
        unused_flags = [
            key for key, metrics in self._metrics.items()
            if metrics.evaluation_count < 10 and metrics.last_evaluated and
            (datetime.utcnow() - metrics.last_evaluated).days > 7
        ]
        if unused_flags:
            recommendations.append(
                f"Consider archiving {len(unused_flags)} unused flags"
            )
        
        return recommendations
    
    async def _cleanup_old_metrics(self) -> None:
        """Clean up old time-based metrics."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.metrics_retention_days)
        cutoff_hour = cutoff_date.strftime("%Y-%m-%d-%H")
        cutoff_day = cutoff_date.strftime("%Y-%m-%d")
        
        for metrics in self._metrics.values():
            # Clean hourly data
            old_hours = [
                hour for hour in metrics.hourly_counts.keys()
                if hour < cutoff_hour
            ]
            for hour in old_hours:
                del metrics.hourly_counts[hour]
            
            # Clean daily data (keep longer)
            very_old_cutoff = cutoff_date - timedelta(days=365)
            very_old_day = very_old_cutoff.strftime("%Y-%m-%d")
            
            old_days = [
                day for day in metrics.daily_counts.keys()
                if day < very_old_day
            ]
            for day in old_days:
                del metrics.daily_counts[day]
    
    async def _generate_health_report(self) -> None:
        """Generate periodic health report."""
        try:
            report = await self.get_performance_report()
            
            # Log warning if there are performance issues
            issues = report.get("performance_issues", {})
            slow_flags = issues.get("slow_flags", [])
            error_flags = issues.get("error_prone_flags", [])
            
            if slow_flags or error_flags:
                logger.warning(
                    f"Feature flag performance issues detected: "
                    f"{len(slow_flags)} slow flags, {len(error_flags)} error-prone flags"
                )
            
        except Exception as e:
            logger.error(f"Health report generation failed: {e}")
    
    async def export_metrics(
        self,
        format: str = "json",
        include_time_series: bool = False,
    ) -> Dict[str, Any]:
        """Export metrics in specified format."""
        data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "global_metrics": await self.get_global_metrics(),
            "flag_metrics": {},
        }
        
        for flag_key, metrics in self._metrics.items():
            flag_data = {
                "evaluation_count": metrics.evaluation_count,
                "unique_user_count": metrics.unique_user_count,
                "variant_counts": metrics.variant_counts,
                "error_count": metrics.error_count,
                "avg_latency_ms": metrics.avg_latency_ms,
                "cache_hit_rate": metrics.cache_hit_rate,
                "error_rate": metrics.error_rate,
                "last_evaluated": metrics.last_evaluated.isoformat() if metrics.last_evaluated else None,
            }
            
            if include_time_series:
                flag_data["hourly_counts"] = metrics.hourly_counts
                flag_data["daily_counts"] = metrics.daily_counts
            
            data["flag_metrics"][flag_key] = flag_data
        
        return data
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
