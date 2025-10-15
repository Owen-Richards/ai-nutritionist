"""
Core Health Check Components

Provides the fundamental health checking classes and enums.
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Union, Callable, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HealthCheckType(Enum):
    """Types of health checks"""
    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"
    DEPENDENCY = "dependency"


@dataclass
class HealthCheckResult:
    """Result of a health check operation"""
    status: HealthStatus
    check_type: HealthCheckType
    service_name: str
    check_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'status': self.status.value,
            'check_type': self.check_type.value,
            'service_name': self.service_name,
            'check_name': self.check_name,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'duration_ms': self.duration_ms,
            'message': self.message,
            'details': self.details,
            'error': self.error
        }


@dataclass
class ServiceHealth:
    """Overall health status of a service"""
    service_name: str
    overall_status: HealthStatus
    checks: List[HealthCheckResult] = field(default_factory=list)
    uptime_seconds: float = 0.0
    start_time: datetime = field(default_factory=datetime.utcnow)
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'service_name': self.service_name,
            'overall_status': self.overall_status.value,
            'uptime_seconds': self.uptime_seconds,
            'start_time': self.start_time.isoformat() + 'Z',
            'version': self.version,
            'checks': [check.to_dict() for check in self.checks]
        }


class DependencyCheck(ABC):
    """Abstract base class for dependency health checks"""
    
    def __init__(self, name: str, timeout: float = 5.0):
        self.name = name
        self.timeout = timeout
    
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform the health check and return result"""
        pass
    
    def _create_result(
        self,
        status: HealthStatus,
        duration_ms: float,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> HealthCheckResult:
        """Helper to create health check result"""
        return HealthCheckResult(
            status=status,
            check_type=HealthCheckType.DEPENDENCY,
            service_name="dependency",
            check_name=self.name,
            duration_ms=duration_ms,
            message=message,
            details=details or {},
            error=error
        )


class HealthChecker:
    """Main health checker that orchestrates all health checks"""
    
    def __init__(
        self,
        service_name: str,
        version: Optional[str] = None,
        startup_timeout: float = 30.0
    ):
        self.service_name = service_name
        self.version = version
        self.startup_timeout = startup_timeout
        self.start_time = datetime.utcnow()
        
        # Health check registries
        self._liveness_checks: List[Callable[[], Union[bool, HealthCheckResult]]] = []
        self._readiness_checks: List[Callable[[], Union[bool, HealthCheckResult]]] = []
        self._startup_checks: List[Callable[[], Union[bool, HealthCheckResult]]] = []
        self._dependency_checks: List[DependencyCheck] = []
        
        # State tracking
        self._startup_completed = False
        self._last_startup_check = None
        
        logger.info(f"Health checker initialized for service: {service_name}")
    
    def register_liveness_check(
        self, 
        check_func: Callable[[], Union[bool, HealthCheckResult]],
        name: Optional[str] = None
    ):
        """Register a liveness check function"""
        if name:
            check_func._health_check_name = name
        self._liveness_checks.append(check_func)
        logger.debug(f"Registered liveness check: {name or check_func.__name__}")
    
    def register_readiness_check(
        self, 
        check_func: Callable[[], Union[bool, HealthCheckResult]],
        name: Optional[str] = None
    ):
        """Register a readiness check function"""
        if name:
            check_func._health_check_name = name
        self._readiness_checks.append(check_func)
        logger.debug(f"Registered readiness check: {name or check_func.__name__}")
    
    def register_startup_check(
        self, 
        check_func: Callable[[], Union[bool, HealthCheckResult]],
        name: Optional[str] = None
    ):
        """Register a startup check function"""
        if name:
            check_func._health_check_name = name
        self._startup_checks.append(check_func)
        logger.debug(f"Registered startup check: {name or check_func.__name__}")
    
    def register_dependency_check(self, dependency_check: DependencyCheck):
        """Register a dependency health check"""
        self._dependency_checks.append(dependency_check)
        logger.debug(f"Registered dependency check: {dependency_check.name}")
    
    async def check_liveness(self) -> ServiceHealth:
        """Perform liveness checks"""
        return await self._perform_checks(
            self._liveness_checks,
            HealthCheckType.LIVENESS,
            "Liveness checks"
        )
    
    async def check_readiness(self) -> ServiceHealth:
        """Perform readiness checks"""
        # If startup hasn't completed, service is not ready
        if not self._startup_completed:
            startup_health = await self.check_startup()
            if startup_health.overall_status != HealthStatus.HEALTHY:
                return ServiceHealth(
                    service_name=self.service_name,
                    overall_status=HealthStatus.UNHEALTHY,
                    checks=[HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        check_type=HealthCheckType.READINESS,
                        service_name=self.service_name,
                        check_name="startup_dependency",
                        message="Service startup not completed"
                    )],
                    uptime_seconds=self._get_uptime(),
                    start_time=self.start_time,
                    version=self.version
                )
        
        return await self._perform_checks(
            self._readiness_checks + self._dependency_checks,
            HealthCheckType.READINESS,
            "Readiness checks"
        )
    
    async def check_startup(self) -> ServiceHealth:
        """Perform startup checks"""
        current_time = datetime.utcnow()
        
        # Check if startup timeout exceeded
        if (current_time - self.start_time).total_seconds() > self.startup_timeout:
            self._startup_completed = False
            return ServiceHealth(
                service_name=self.service_name,
                overall_status=HealthStatus.UNHEALTHY,
                checks=[HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    check_type=HealthCheckType.STARTUP,
                    service_name=self.service_name,
                    check_name="startup_timeout",
                    message=f"Startup timeout exceeded: {self.startup_timeout}s"
                )],
                uptime_seconds=self._get_uptime(),
                start_time=self.start_time,
                version=self.version
            )
        
        # Perform startup checks
        health = await self._perform_checks(
            self._startup_checks,
            HealthCheckType.STARTUP,
            "Startup checks"
        )
        
        # Mark startup as completed if all checks pass
        if health.overall_status == HealthStatus.HEALTHY:
            self._startup_completed = True
            logger.info(f"Service {self.service_name} startup completed successfully")
        
        return health
    
    async def check_dependencies(self) -> ServiceHealth:
        """Perform dependency checks"""
        return await self._perform_checks(
            self._dependency_checks,
            HealthCheckType.DEPENDENCY,
            "Dependency checks"
        )
    
    async def check_all(self) -> Dict[str, ServiceHealth]:
        """Perform all health checks"""
        results = {}
        
        # Run all check types
        liveness = await self.check_liveness()
        readiness = await self.check_readiness()
        startup = await self.check_startup()
        dependencies = await self.check_dependencies()
        
        results['liveness'] = liveness
        results['readiness'] = readiness
        results['startup'] = startup
        results['dependencies'] = dependencies
        
        return results
    
    async def _perform_checks(
        self,
        checks: List[Union[Callable, DependencyCheck]],
        check_type: HealthCheckType,
        description: str
    ) -> ServiceHealth:
        """Execute a list of health checks"""
        check_results = []
        overall_status = HealthStatus.HEALTHY
        
        if not checks:
            # No checks registered means healthy by default
            check_results.append(HealthCheckResult(
                status=HealthStatus.HEALTHY,
                check_type=check_type,
                service_name=self.service_name,
                check_name="no_checks",
                message=f"No {description.lower()} registered - default healthy"
            ))
        else:
            # Execute all checks
            for check in checks:
                try:
                    start_time = time.time()
                    
                    if isinstance(check, DependencyCheck):
                        result = await check.check_health()
                    else:
                        # Call the check function
                        if asyncio.iscoroutinefunction(check):
                            check_result = await check()
                        else:
                            check_result = check()
                        
                        # Convert boolean result to HealthCheckResult
                        if isinstance(check_result, bool):
                            result = HealthCheckResult(
                                status=HealthStatus.HEALTHY if check_result else HealthStatus.UNHEALTHY,
                                check_type=check_type,
                                service_name=self.service_name,
                                check_name=getattr(check, '_health_check_name', check.__name__),
                                duration_ms=(time.time() - start_time) * 1000
                            )
                        else:
                            result = check_result
                            result.duration_ms = (time.time() - start_time) * 1000
                    
                    check_results.append(result)
                    
                    # Update overall status
                    if result.status == HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.UNHEALTHY
                    elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                    
                except Exception as e:
                    error_result = HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        check_type=check_type,
                        service_name=self.service_name,
                        check_name=getattr(check, 'name', getattr(check, '__name__', 'unknown')),
                        duration_ms=(time.time() - start_time) * 1000,
                        error=str(e),
                        message=f"Health check failed with exception: {e}"
                    )
                    check_results.append(error_result)
                    overall_status = HealthStatus.UNHEALTHY
                    
                    logger.error(f"Health check failed: {e}")
        
        return ServiceHealth(
            service_name=self.service_name,
            overall_status=overall_status,
            checks=check_results,
            uptime_seconds=self._get_uptime(),
            start_time=self.start_time,
            version=self.version
        )
    
    def _get_uptime(self) -> float:
        """Get service uptime in seconds"""
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    def is_startup_completed(self) -> bool:
        """Check if startup phase is completed"""
        return self._startup_completed
