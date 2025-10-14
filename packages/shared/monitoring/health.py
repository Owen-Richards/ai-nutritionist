"""
Health check framework for service monitoring and alerting.

Provides:
- Service health checks
- Dependency health monitoring
- Health status aggregation
- Alert integration
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
import threading
from concurrent.futures import ThreadPoolExecutor, Future

from .logging import StructuredLogger, LogLevel, EventType
from .metrics import MetricsRegistry, get_registry


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ServiceHealth:
    """Overall service health status."""
    service_name: str
    status: HealthStatus
    checks: List[HealthCheckResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "checks": [check.to_dict() for check in self.checks],
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": self.uptime_seconds
        }


class HealthCheck(ABC):
    """Abstract base class for health checks."""
    
    def __init__(self, name: str, timeout_seconds: float = 5.0):
        self.name = name
        self.timeout_seconds = timeout_seconds
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """Perform the health check."""
        pass
    
    def sync_check(self) -> HealthCheckResult:
        """Synchronous wrapper for async health check."""
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.check())


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity."""
    
    def __init__(self, name: str, connection_factory: Callable, timeout_seconds: float = 5.0):
        super().__init__(name, timeout_seconds)
        self.connection_factory = connection_factory
    
    async def check(self) -> HealthCheckResult:
        """Check database connectivity."""
        start_time = time.time()
        
        try:
            # Try to get a connection and perform a simple query
            connection = await asyncio.wait_for(
                self._test_connection(),
                timeout=self.timeout_seconds
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                duration_ms=duration_ms,
                details={"connection_test": "passed"}
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Database connection timeout",
                duration_ms=duration_ms,
                details={"error": "timeout", "timeout_seconds": self.timeout_seconds}
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                duration_ms=duration_ms,
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    async def _test_connection(self):
        """Test database connection."""
        # This would be implemented based on your database type
        # For now, we'll simulate it
        connection = self.connection_factory()
        # Perform a simple test query
        # await connection.execute("SELECT 1")
        return connection


class ExternalAPIHealthCheck(HealthCheck):
    """Health check for external API dependencies."""
    
    def __init__(self, name: str, url: str, timeout_seconds: float = 5.0, expected_status: int = 200):
        super().__init__(name, timeout_seconds)
        self.url = url
        self.expected_status = expected_status
    
    async def check(self) -> HealthCheckResult:
        """Check external API health."""
        import aiohttp
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
                ) as response:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if response.status == self.expected_status:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.HEALTHY,
                            message=f"API responded with status {response.status}",
                            duration_ms=duration_ms,
                            details={
                                "status_code": response.status,
                                "url": self.url,
                                "response_time_ms": duration_ms
                            }
                        )
                    else:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.DEGRADED,
                            message=f"API responded with unexpected status {response.status}",
                            duration_ms=duration_ms,
                            details={
                                "status_code": response.status,
                                "expected_status": self.expected_status,
                                "url": self.url
                            }
                        )
                        
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="API request timeout",
                duration_ms=duration_ms,
                details={"error": "timeout", "url": self.url, "timeout_seconds": self.timeout_seconds}
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"API request failed: {str(e)}",
                duration_ms=duration_ms,
                details={"error": str(e), "error_type": type(e).__name__, "url": self.url}
            )


class MemoryHealthCheck(HealthCheck):
    """Health check for memory usage."""
    
    def __init__(self, name: str = "memory", warning_threshold: float = 80.0, critical_threshold: float = 95.0):
        super().__init__(name)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def check(self) -> HealthCheckResult:
        """Check memory usage."""
        import psutil
        
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            duration_ms = (time.time() - start_time) * 1000
            
            if usage_percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage: {usage_percent:.1f}%"
            elif usage_percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {usage_percent:.1f}%"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                duration_ms=duration_ms,
                details={
                    "usage_percent": usage_percent,
                    "total_mb": memory.total / (1024 * 1024),
                    "available_mb": memory.available / (1024 * 1024),
                    "used_mb": memory.used / (1024 * 1024),
                    "warning_threshold": self.warning_threshold,
                    "critical_threshold": self.critical_threshold
                }
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"Memory check failed: {str(e)}",
                duration_ms=duration_ms,
                details={"error": str(e), "error_type": type(e).__name__}
            )


class DiskHealthCheck(HealthCheck):
    """Health check for disk usage."""
    
    def __init__(self, name: str = "disk", path: str = "/", warning_threshold: float = 80.0, critical_threshold: float = 95.0):
        super().__init__(name)
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def check(self) -> HealthCheckResult:
        """Check disk usage."""
        import psutil
        
        start_time = time.time()
        
        try:
            disk = psutil.disk_usage(self.path)
            usage_percent = (disk.used / disk.total) * 100
            
            duration_ms = (time.time() - start_time) * 1000
            
            if usage_percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk usage: {usage_percent:.1f}%"
            elif usage_percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {usage_percent:.1f}%"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                duration_ms=duration_ms,
                details={
                    "usage_percent": usage_percent,
                    "total_gb": disk.total / (1024 * 1024 * 1024),
                    "free_gb": disk.free / (1024 * 1024 * 1024),
                    "used_gb": disk.used / (1024 * 1024 * 1024),
                    "path": self.path,
                    "warning_threshold": self.warning_threshold,
                    "critical_threshold": self.critical_threshold
                }
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"Disk check failed: {str(e)}",
                duration_ms=duration_ms,
                details={"error": str(e), "error_type": type(e).__name__, "path": self.path}
            )


class HealthMonitor:
    """Health monitoring service."""
    
    def __init__(self, service_name: str = "ai-nutritionist"):
        self.service_name = service_name
        self.checks: Dict[str, HealthCheck] = {}
        self.logger = StructuredLogger()
        self.metrics = get_registry()
        self.start_time = datetime.now(timezone.utc)
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.Lock()
    
    def add_check(self, check: HealthCheck) -> None:
        """Add a health check."""
        with self._lock:
            self.checks[check.name] = check
    
    def remove_check(self, name: str) -> None:
        """Remove a health check."""
        with self._lock:
            self.checks.pop(name, None)
    
    async def check_health(self, check_names: Optional[List[str]] = None) -> ServiceHealth:
        """Perform health checks and return service health."""
        start_time = time.time()
        
        # Determine which checks to run
        if check_names:
            checks_to_run = {name: check for name, check in self.checks.items() if name in check_names}
        else:
            checks_to_run = self.checks.copy()
        
        # Run health checks concurrently
        results = []
        if checks_to_run:
            tasks = [check.check() for check in checks_to_run.values()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to failed health check results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    check_name = list(checks_to_run.keys())[i]
                    results[i] = HealthCheckResult(
                        name=check_name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check failed: {str(result)}",
                        details={"error": str(result), "error_type": type(result).__name__}
                    )
        
        # Determine overall service health
        overall_status = self._calculate_overall_status(results)
        
        # Calculate uptime
        uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        service_health = ServiceHealth(
            service_name=self.service_name,
            status=overall_status,
            checks=results,
            uptime_seconds=uptime_seconds
        )
        
        # Log health check results
        duration_ms = (time.time() - start_time) * 1000
        self.logger.info(
            f"Health check completed for {self.service_name}",
            extra={
                "health_check": service_health.to_dict(),
                "duration_ms": duration_ms,
                "checks_count": len(results)
            }
        )
        
        # Record metrics
        self.metrics.counter("health_checks_total").increment(
            tags={"service": self.service_name, "status": overall_status.value}
        )
        
        self.metrics.histogram("health_check_duration_ms").observe(
            duration_ms, tags={"service": self.service_name}
        )
        
        # Record individual check metrics
        for result in results:
            self.metrics.counter("health_check_result_total").increment(
                tags={
                    "service": self.service_name,
                    "check": result.name,
                    "status": result.status.value
                }
            )
            
            if result.duration_ms:
                self.metrics.histogram("health_check_individual_duration_ms").observe(
                    result.duration_ms,
                    tags={"service": self.service_name, "check": result.name}
                )
        
        # Log business events for unhealthy services
        if overall_status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]:
            self.logger.business_event(
                event_type=EventType.SYSTEM_EVENT,
                entity_type="service",
                entity_id=self.service_name,
                action="health_degraded",
                metadata={
                    "status": overall_status.value,
                    "failed_checks": [r.name for r in results if r.status == HealthStatus.UNHEALTHY],
                    "degraded_checks": [r.name for r in results if r.status == HealthStatus.DEGRADED]
                },
                level=LogLevel.WARN if overall_status == HealthStatus.DEGRADED else LogLevel.ERROR
            )
        
        return service_health
    
    def sync_check_health(self, check_names: Optional[List[str]] = None) -> ServiceHealth:
        """Synchronous wrapper for health checks."""
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.check_health(check_names))
    
    def _calculate_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Calculate overall service health status."""
        if not results:
            return HealthStatus.UNKNOWN
        
        # If any check is unhealthy, service is unhealthy
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            return HealthStatus.UNHEALTHY
        
        # If any check is degraded, service is degraded
        if any(r.status == HealthStatus.DEGRADED for r in results):
            return HealthStatus.DEGRADED
        
        # If any check is unknown, service is unknown
        if any(r.status == HealthStatus.UNKNOWN for r in results):
            return HealthStatus.UNKNOWN
        
        # All checks are healthy
        return HealthStatus.HEALTHY
    
    def start_periodic_checks(self, interval_seconds: int = 60) -> None:
        """Start periodic health checks in background."""
        def run_periodic_checks():
            while True:
                try:
                    health = self.sync_check_health()
                    # Health results are already logged in check_health method
                except Exception as e:
                    self.logger.error(f"Periodic health check failed: {e}")
                
                time.sleep(interval_seconds)
        
        thread = threading.Thread(target=run_periodic_checks, daemon=True)
        thread.start()


# Global health monitor
default_monitor = HealthMonitor()


def get_health_monitor(service_name: str = "ai-nutritionist") -> HealthMonitor:
    """Get health monitor for a service."""
    if service_name == "ai-nutritionist":
        return default_monitor
    return HealthMonitor(service_name)


def setup_basic_health_checks(monitor: Optional[HealthMonitor] = None) -> HealthMonitor:
    """Setup basic health checks for the service."""
    if monitor is None:
        monitor = default_monitor
    
    # Add basic system health checks
    monitor.add_check(MemoryHealthCheck())
    monitor.add_check(DiskHealthCheck())
    
    return monitor
