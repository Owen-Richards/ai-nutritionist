"""
Health Check Probes

Provides specific probe implementations for different health check types.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import logging

from .core import HealthCheckResult, HealthStatus, HealthCheckType

logger = logging.getLogger(__name__)


@dataclass
class ProbeConfig:
    """Configuration for health check probes"""
    initial_delay_seconds: float = 0
    period_seconds: float = 10
    timeout_seconds: float = 5
    failure_threshold: int = 3
    success_threshold: int = 1


class LivenessProbe:
    """
    Liveness probe implementation
    
    Checks if the application is running and can handle requests.
    If this fails, the container should be restarted.
    """
    
    def __init__(self, name: str = "liveness", config: Optional[ProbeConfig] = None):
        self.name = name
        self.config = config or ProbeConfig()
        self.failure_count = 0
        self.success_count = 0
        self.last_check_time: Optional[datetime] = None
        self.last_status = HealthStatus.UNKNOWN
        
        # Default checks
        self._checks: List[Callable] = []
        self._add_default_checks()
    
    def _add_default_checks(self):
        """Add default liveness checks"""
        # Check if process is responsive
        self.add_check(self._check_process_responsive)
        
        # Check memory usage (basic)
        self.add_check(self._check_memory_usage)
    
    def add_check(self, check_func: Callable):
        """Add a custom liveness check"""
        self._checks.append(check_func)
        logger.debug(f"Added liveness check: {check_func.__name__}")
    
    async def check(self) -> HealthCheckResult:
        """Perform liveness check"""
        start_time = time.time()
        self.last_check_time = datetime.utcnow()
        
        try:
            # Run all checks
            for check in self._checks:
                if asyncio.iscoroutinefunction(check):
                    result = await asyncio.wait_for(check(), timeout=self.config.timeout_seconds)
                else:
                    result = check()
                
                if not result:
                    self._record_failure()
                    return HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        check_type=HealthCheckType.LIVENESS,
                        service_name="probe",
                        check_name=self.name,
                        duration_ms=(time.time() - start_time) * 1000,
                        message=f"Liveness check failed: {check.__name__}",
                        details={'failure_count': self.failure_count}
                    )
            
            self._record_success()
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                check_type=HealthCheckType.LIVENESS,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                message="All liveness checks passed",
                details={'success_count': self.success_count}
            )
            
        except asyncio.TimeoutError:
            self._record_failure()
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type=HealthCheckType.LIVENESS,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                error="Timeout",
                message=f"Liveness check timed out after {self.config.timeout_seconds}s"
            )
        except Exception as e:
            self._record_failure()
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type=HealthCheckType.LIVENESS,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
                message=f"Liveness check failed: {e}"
            )
    
    def _check_process_responsive(self) -> bool:
        """Basic responsiveness check"""
        # Simple check - if we can execute this, process is responsive
        return True
    
    def _check_memory_usage(self) -> bool:
        """Basic memory usage check"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            # Fail if system memory usage is above 95%
            return memory.percent < 95
        except ImportError:
            # If psutil not available, assume OK
            return True
        except Exception:
            # If any error, assume OK for liveness
            return True
    
    def _record_success(self):
        """Record successful check"""
        self.success_count += 1
        self.failure_count = 0
        self.last_status = HealthStatus.HEALTHY
    
    def _record_failure(self):
        """Record failed check"""
        self.failure_count += 1
        self.success_count = 0
        self.last_status = HealthStatus.UNHEALTHY


class ReadinessProbe:
    """
    Readiness probe implementation
    
    Checks if the application is ready to receive traffic.
    Traffic should only be routed to ready instances.
    """
    
    def __init__(self, name: str = "readiness", config: Optional[ProbeConfig] = None):
        self.name = name
        self.config = config or ProbeConfig()
        self.failure_count = 0
        self.success_count = 0
        self.last_check_time: Optional[datetime] = None
        self.last_status = HealthStatus.UNKNOWN
        
        # Dependency checks
        self._dependency_checks: List[Callable] = []
        
        # Resource checks
        self._resource_checks: List[Callable] = []
        self._add_default_checks()
    
    def _add_default_checks(self):
        """Add default readiness checks"""
        # Check if resources are available
        self.add_resource_check(self._check_cpu_usage)
        self.add_resource_check(self._check_disk_space)
    
    def add_dependency_check(self, check_func: Callable):
        """Add a dependency readiness check"""
        self._dependency_checks.append(check_func)
        logger.debug(f"Added dependency readiness check: {check_func.__name__}")
    
    def add_resource_check(self, check_func: Callable):
        """Add a resource readiness check"""
        self._resource_checks.append(check_func)
        logger.debug(f"Added resource readiness check: {check_func.__name__}")
    
    async def check(self) -> HealthCheckResult:
        """Perform readiness check"""
        start_time = time.time()
        self.last_check_time = datetime.utcnow()
        
        try:
            check_results = []
            
            # Check dependencies first
            for check in self._dependency_checks:
                try:
                    if asyncio.iscoroutinefunction(check):
                        result = await asyncio.wait_for(check(), timeout=self.config.timeout_seconds)
                    else:
                        result = check()
                    
                    if not result:
                        check_results.append(f"Dependency check failed: {check.__name__}")
                except Exception as e:
                    check_results.append(f"Dependency check error: {check.__name__} - {e}")
            
            # Check resources
            for check in self._resource_checks:
                try:
                    if asyncio.iscoroutinefunction(check):
                        result = await asyncio.wait_for(check(), timeout=self.config.timeout_seconds)
                    else:
                        result = check()
                    
                    if not result:
                        check_results.append(f"Resource check failed: {check.__name__}")
                except Exception as e:
                    check_results.append(f"Resource check error: {check.__name__} - {e}")
            
            if check_results:
                self._record_failure()
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    check_type=HealthCheckType.READINESS,
                    service_name="probe",
                    check_name=self.name,
                    duration_ms=(time.time() - start_time) * 1000,
                    message="Readiness checks failed",
                    details={
                        'failed_checks': check_results,
                        'failure_count': self.failure_count
                    }
                )
            
            self._record_success()
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                check_type=HealthCheckType.READINESS,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                message="All readiness checks passed",
                details={'success_count': self.success_count}
            )
            
        except asyncio.TimeoutError:
            self._record_failure()
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type=HealthCheckType.READINESS,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                error="Timeout",
                message=f"Readiness check timed out after {self.config.timeout_seconds}s"
            )
        except Exception as e:
            self._record_failure()
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type=HealthCheckType.READINESS,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
                message=f"Readiness check failed: {e}"
            )
    
    def _check_cpu_usage(self) -> bool:
        """Check CPU usage"""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            # Fail if CPU usage is above 90%
            return cpu_percent < 90
        except ImportError:
            return True
        except Exception:
            return True
    
    def _check_disk_space(self) -> bool:
        """Check disk space"""
        try:
            import psutil
            disk_usage = psutil.disk_usage('/')
            # Fail if disk usage is above 90%
            return (disk_usage.used / disk_usage.total) < 0.9
        except ImportError:
            return True
        except Exception:
            return True
    
    def _record_success(self):
        """Record successful check"""
        self.success_count += 1
        self.failure_count = 0
        self.last_status = HealthStatus.HEALTHY
    
    def _record_failure(self):
        """Record failed check"""
        self.failure_count += 1
        self.success_count = 0
        self.last_status = HealthStatus.UNHEALTHY


class StartupProbe:
    """
    Startup probe implementation
    
    Checks if the application has started successfully.
    Other probes should wait until startup completes.
    """
    
    def __init__(self, name: str = "startup", config: Optional[ProbeConfig] = None):
        self.name = name
        self.config = config or ProbeConfig(
            period_seconds=5,  # Check more frequently during startup
            timeout_seconds=10,
            failure_threshold=10  # Allow more failures during startup
        )
        self.failure_count = 0
        self.success_count = 0
        self.last_check_time: Optional[datetime] = None
        self.last_status = HealthStatus.UNKNOWN
        self.startup_completed = False
        
        # Startup checks
        self._startup_checks: List[Callable] = []
    
    def add_startup_check(self, check_func: Callable):
        """Add a startup check"""
        self._startup_checks.append(check_func)
        logger.debug(f"Added startup check: {check_func.__name__}")
    
    async def check(self) -> HealthCheckResult:
        """Perform startup check"""
        start_time = time.time()
        self.last_check_time = datetime.utcnow()
        
        # If startup already completed, return success
        if self.startup_completed:
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                check_type=HealthCheckType.STARTUP,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                message="Startup completed successfully",
                details={'startup_completed': True}
            )
        
        try:
            # Run all startup checks
            for check in self._startup_checks:
                try:
                    if asyncio.iscoroutinefunction(check):
                        result = await asyncio.wait_for(check(), timeout=self.config.timeout_seconds)
                    else:
                        result = check()
                    
                    if not result:
                        self._record_failure()
                        return HealthCheckResult(
                            status=HealthStatus.UNHEALTHY,
                            check_type=HealthCheckType.STARTUP,
                            service_name="probe",
                            check_name=self.name,
                            duration_ms=(time.time() - start_time) * 1000,
                            message=f"Startup check failed: {check.__name__}",
                            details={
                                'failure_count': self.failure_count,
                                'startup_completed': False
                            }
                        )
                except Exception as e:
                    self._record_failure()
                    return HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        check_type=HealthCheckType.STARTUP,
                        service_name="probe",
                        check_name=self.name,
                        duration_ms=(time.time() - start_time) * 1000,
                        error=str(e),
                        message=f"Startup check error: {check.__name__} - {e}"
                    )
            
            # All checks passed - startup completed
            self._record_success()
            self.startup_completed = True
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                check_type=HealthCheckType.STARTUP,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                message="Startup checks completed successfully",
                details={
                    'success_count': self.success_count,
                    'startup_completed': True
                }
            )
            
        except asyncio.TimeoutError:
            self._record_failure()
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type=HealthCheckType.STARTUP,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                error="Timeout",
                message=f"Startup check timed out after {self.config.timeout_seconds}s"
            )
        except Exception as e:
            self._record_failure()
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                check_type=HealthCheckType.STARTUP,
                service_name="probe",
                check_name=self.name,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
                message=f"Startup check failed: {e}"
            )
    
    def is_startup_completed(self) -> bool:
        """Check if startup is completed"""
        return self.startup_completed
    
    def reset_startup(self):
        """Reset startup state (for testing or restart scenarios)"""
        self.startup_completed = False
        self.failure_count = 0
        self.success_count = 0
        self.last_status = HealthStatus.UNKNOWN
        logger.info(f"Startup probe '{self.name}' reset")
    
    def _record_success(self):
        """Record successful check"""
        self.success_count += 1
        self.failure_count = 0
        self.last_status = HealthStatus.HEALTHY
    
    def _record_failure(self):
        """Record failed check"""
        self.failure_count += 1
        self.success_count = 0
        self.last_status = HealthStatus.UNHEALTHY
