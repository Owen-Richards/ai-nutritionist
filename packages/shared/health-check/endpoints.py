"""
Health Check Endpoints

Provides FastAPI router and endpoints for health checks.
"""

import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Response
from typing import Dict, Any, Optional

from .core import HealthChecker, HealthStatus, ServiceHealth


class HealthCheckRouter:
    """Router factory for health check endpoints"""
    
    def __init__(self, health_checker: HealthChecker):
        self.health_checker = health_checker
        self.router = APIRouter()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup health check routes"""
        
        @self.router.get("/health/live")
        async def liveness_probe(response: Response):
            """
            Liveness probe endpoint
            
            Indicates whether the service is running and should receive traffic.
            Used by orchestrators to restart containers if this fails.
            """
            try:
                health = await self.health_checker.check_liveness()
                
                if health.overall_status == HealthStatus.HEALTHY:
                    response.status_code = 200
                    return health.to_dict()
                else:
                    response.status_code = 503
                    return health.to_dict()
                    
            except Exception as e:
                response.status_code = 503
                return {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
        
        @self.router.get("/health/ready")
        async def readiness_probe(response: Response):
            """
            Readiness probe endpoint
            
            Indicates whether the service is ready to handle requests.
            Traffic should only be routed to ready services.
            """
            try:
                health = await self.health_checker.check_readiness()
                
                if health.overall_status == HealthStatus.HEALTHY:
                    response.status_code = 200
                    return health.to_dict()
                else:
                    response.status_code = 503
                    return health.to_dict()
                    
            except Exception as e:
                response.status_code = 503
                return {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
        
        @self.router.get("/health/startup")
        async def startup_probe(response: Response):
            """
            Startup probe endpoint
            
            Indicates whether the service has completed its startup sequence.
            Used to delay other probes until startup is complete.
            """
            try:
                health = await self.health_checker.check_startup()
                
                if health.overall_status == HealthStatus.HEALTHY:
                    response.status_code = 200
                    return health.to_dict()
                else:
                    response.status_code = 503
                    return health.to_dict()
                    
            except Exception as e:
                response.status_code = 503
                return {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
        
        @self.router.get("/health/dependencies")
        async def dependency_check(response: Response):
            """
            Dependency health check endpoint
            
            Reports the health status of all external dependencies.
            """
            try:
                health = await self.health_checker.check_dependencies()
                
                # Dependencies can be degraded but still functional
                if health.overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                    response.status_code = 200
                else:
                    response.status_code = 503
                
                return health.to_dict()
                    
            except Exception as e:
                response.status_code = 503
                return {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
        
        @self.router.get("/health")
        async def comprehensive_health_check():
            """
            Comprehensive health check endpoint
            
            Returns the status of all health check types.
            """
            try:
                all_health = await self.health_checker.check_all()
                
                # Determine overall service status
                overall_status = HealthStatus.HEALTHY
                total_checks = 0
                healthy_checks = 0
                
                for check_type, health in all_health.items():
                    if health.overall_status == HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.UNHEALTHY
                        break
                    elif health.overall_status == HealthStatus.DEGRADED:
                        overall_status = HealthStatus.DEGRADED
                    
                    total_checks += len(health.checks)
                    healthy_checks += len([c for c in health.checks if c.status == HealthStatus.HEALTHY])
                
                # Calculate health score
                health_score = (healthy_checks / total_checks * 100) if total_checks > 0 else 100
                
                result = {
                    'service_name': self.health_checker.service_name,
                    'overall_status': overall_status.value,
                    'health_score': round(health_score, 2),
                    'uptime_seconds': self.health_checker._get_uptime(),
                    'startup_completed': self.health_checker.is_startup_completed(),
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'version': self.health_checker.version,
                    'checks': {
                        check_type: health.to_dict() 
                        for check_type, health in all_health.items()
                    }
                }
                
                return result
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail={
                        'status': 'unhealthy',
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }
                )


def health_check_endpoint(health_checker: HealthChecker):
    """
    Decorator for creating simple health check endpoints
    
    Usage:
        @health_check_endpoint(health_checker)
        async def custom_health():
            return {"custom": "check"}
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                custom_result = await func(*args, **kwargs)
                health = await health_checker.check_all()
                
                return {
                    **health,
                    'custom': custom_result,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail={
                        'status': 'unhealthy',
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }
                )
        return wrapper
    return decorator


def create_health_routes(health_checker: HealthChecker) -> APIRouter:
    """
    Factory function to create health check router
    
    Args:
        health_checker: Configured HealthChecker instance
        
    Returns:
        FastAPI router with health check endpoints
    """
    health_router = HealthCheckRouter(health_checker)
    return health_router.router
