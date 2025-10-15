"""
Centralized Health Check System

Aggregates health checks from all services and provides:
- System-wide health overview
- Service dependency mapping
- Cross-service health correlation
- Global health dashboard
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

import httpx
from fastapi import APIRouter, HTTPException

from packages.shared.health_check import (
    HealthStatus, HealthChecker, HealthMonitor,
    CloudWatchHealthReporter, create_health_routes
)

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration"""
    name: str
    url: str
    health_path: str = "/health"
    timeout: float = 10.0
    critical: bool = True


@dataclass
class SystemHealthSummary:
    """System-wide health summary"""
    overall_status: HealthStatus
    total_services: int
    healthy_services: int
    unhealthy_services: int
    degraded_services: int
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    uptime_seconds: float = 0.0
    health_score: float = 0.0
    service_details: Dict[str, Any] = field(default_factory=dict)


class SystemHealthChecker:
    """
    Centralized health checker that monitors all services
    """
    
    def __init__(self):
        self.system_start_time = datetime.utcnow()
        
        # Service endpoints
        self.services = {
            "nutrition-service": ServiceEndpoint(
                name="nutrition-service",
                url="http://nutrition-service:8000",
                critical=True
            ),
            "messaging-service": ServiceEndpoint(
                name="messaging-service", 
                url="http://messaging-service:8001",
                critical=True
            ),
            "ai-coach-service": ServiceEndpoint(
                name="ai-coach-service",
                url="http://ai-coach-service:8002",
                critical=True
            ),
            "payment-service": ServiceEndpoint(
                name="payment-service",
                url="http://payment-service:8003",
                critical=True
            ),
            "health-tracking-service": ServiceEndpoint(
                name="health-tracking-service",
                url="http://health-tracking-service:8004",
                critical=False  # Can be degraded without system failure
            )
        }
        
        # Health history
        self._health_history: List[SystemHealthSummary] = []
        self._service_dependencies = self._build_dependency_map()
        
        # Monitoring
        self.cloudwatch_reporter = CloudWatchHealthReporter(
            namespace="System/HealthCheck"
        )
        
        # Circuit breaker status tracking
        self._circuit_breaker_states: Dict[str, Dict[str, str]] = {}
        
    def _build_dependency_map(self) -> Dict[str, List[str]]:
        """Build service dependency map"""
        return {
            "nutrition-service": ["ai-coach-service"],
            "messaging-service": ["nutrition-service"],
            "ai-coach-service": ["nutrition-service", "health-tracking-service"],
            "payment-service": [],
            "health-tracking-service": ["nutrition-service"]
        }
    
    async def check_all_services(self) -> SystemHealthSummary:
        """Check health of all services"""
        service_results = {}
        
        # Check each service
        for service_name, endpoint in self.services.items():
            try:
                service_health = await self._check_service(endpoint)
                service_results[service_name] = service_health
            except Exception as e:
                logger.error(f"Failed to check {service_name}: {e}")
                service_results[service_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                }
        
        # Analyze results
        summary = self._analyze_system_health(service_results)
        
        # Store in history
        self._health_history.append(summary)
        
        # Clean up old history (keep last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self._health_history = [
            h for h in self._health_history 
            if h.timestamp > cutoff_time
        ]
        
        return summary
    
    async def _check_service(self, endpoint: ServiceEndpoint) -> Dict[str, Any]:
        """Check individual service health"""
        async with httpx.AsyncClient(timeout=endpoint.timeout) as client:
            try:
                response = await client.get(f"{endpoint.url}{endpoint.health_path}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.utcnow().isoformat() + 'Z'
                    }
                    
            except httpx.TimeoutException:
                return {
                    "status": "unhealthy",
                    "error": f"Timeout after {endpoint.timeout}s",
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                }
    
    def _analyze_system_health(self, service_results: Dict[str, Any]) -> SystemHealthSummary:
        """Analyze overall system health"""
        total_services = len(service_results)
        healthy_services = 0
        unhealthy_services = 0
        degraded_services = 0
        critical_issues = []
        warnings = []
        
        for service_name, result in service_results.items():
            status = result.get("status", "unknown")
            endpoint = self.services[service_name]
            
            if status == "healthy":
                healthy_services += 1
            elif status == "degraded":
                degraded_services += 1
                warnings.append(f"{service_name} is degraded")
            else:  # unhealthy or unknown
                unhealthy_services += 1
                if endpoint.critical:
                    critical_issues.append(f"Critical service {service_name} is unhealthy")
                else:
                    warnings.append(f"{service_name} is unhealthy")
        
        # Determine overall status
        if critical_issues:
            overall_status = HealthStatus.UNHEALTHY
        elif unhealthy_services > 0 or degraded_services > 0:
            if degraded_services > unhealthy_services:
                overall_status = HealthStatus.DEGRADED
            else:
                overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Calculate health score
        if total_services > 0:
            health_score = (healthy_services + degraded_services * 0.5) / total_services * 100
        else:
            health_score = 0.0
        
        return SystemHealthSummary(
            overall_status=overall_status,
            total_services=total_services,
            healthy_services=healthy_services,
            unhealthy_services=unhealthy_services,
            degraded_services=degraded_services,
            critical_issues=critical_issues,
            warnings=warnings,
            uptime_seconds=(datetime.utcnow() - self.system_start_time).total_seconds(),
            health_score=health_score,
            service_details=service_results
        )
    
    async def check_dependencies(self, service_name: str) -> Dict[str, Any]:
        """Check health of service dependencies"""
        dependencies = self._service_dependencies.get(service_name, [])
        dependency_results = {}
        
        for dep_service in dependencies:
            if dep_service in self.services:
                try:
                    endpoint = self.services[dep_service]
                    result = await self._check_service(endpoint)
                    dependency_results[dep_service] = result
                except Exception as e:
                    dependency_results[dep_service] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
        
        return dependency_results
    
    async def get_service_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed metrics for a specific service"""
        if service_name not in self.services:
            return None
        
        endpoint = self.services[service_name]
        
        try:
            # Try to get detailed metrics
            async with httpx.AsyncClient(timeout=endpoint.timeout) as client:
                response = await client.get(f"{endpoint.url}/health/dependencies")
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        
        # Fall back to basic health check
        try:
            return await self._check_service(endpoint)
        except Exception as e:
            return {"error": str(e)}
    
    def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get health trends over time"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_history = [
            h for h in self._health_history 
            if h.timestamp > cutoff_time
        ]
        
        if not recent_history:
            return {"message": "No historical data available"}
        
        # Calculate trends
        health_scores = [h.health_score for h in recent_history]
        availability_over_time = []
        
        for h in recent_history:
            availability_over_time.append({
                "timestamp": h.timestamp.isoformat() + 'Z',
                "health_score": h.health_score,
                "overall_status": h.overall_status.value,
                "healthy_services": h.healthy_services,
                "total_services": h.total_services
            })
        
        return {
            "period_hours": hours,
            "data_points": len(recent_history),
            "average_health_score": sum(health_scores) / len(health_scores),
            "min_health_score": min(health_scores),
            "max_health_score": max(health_scores),
            "availability_over_time": availability_over_time,
            "incidents_detected": len([h for h in recent_history if h.critical_issues])
        }
    
    def get_circuit_breaker_summary(self) -> Dict[str, Any]:
        """Get circuit breaker status summary"""
        return {
            "circuit_breakers": self._circuit_breaker_states,
            "open_breakers": [
                name for service_breakers in self._circuit_breaker_states.values()
                for name, state in service_breakers.items()
                if state == "open"
            ],
            "total_breakers": sum(
                len(breakers) for breakers in self._circuit_breaker_states.values()
            )
        }


class SystemHealthRouter:
    """FastAPI router for system health endpoints"""
    
    def __init__(self, health_checker: SystemHealthChecker):
        self.health_checker = health_checker
        self.router = APIRouter()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup system health routes"""
        
        @self.router.get("/system/health")
        async def system_health():
            """Get overall system health status"""
            try:
                summary = await self.health_checker.check_all_services()
                return {
                    "overall_status": summary.overall_status.value,
                    "health_score": summary.health_score,
                    "uptime_seconds": summary.uptime_seconds,
                    "services": {
                        "total": summary.total_services,
                        "healthy": summary.healthy_services,
                        "unhealthy": summary.unhealthy_services,
                        "degraded": summary.degraded_services
                    },
                    "critical_issues": summary.critical_issues,
                    "warnings": summary.warnings,
                    "timestamp": summary.timestamp.isoformat() + 'Z'
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/system/health/detailed")
        async def detailed_system_health():
            """Get detailed system health including all service details"""
            try:
                summary = await self.health_checker.check_all_services()
                
                return {
                    "system_summary": {
                        "overall_status": summary.overall_status.value,
                        "health_score": summary.health_score,
                        "uptime_seconds": summary.uptime_seconds,
                        "total_services": summary.total_services,
                        "healthy_services": summary.healthy_services,
                        "unhealthy_services": summary.unhealthy_services,
                        "degraded_services": summary.degraded_services,
                        "critical_issues": summary.critical_issues,
                        "warnings": summary.warnings
                    },
                    "service_details": summary.service_details,
                    "circuit_breakers": self.health_checker.get_circuit_breaker_summary(),
                    "timestamp": summary.timestamp.isoformat() + 'Z'
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/system/health/trends")
        async def health_trends(hours: int = 24):
            """Get system health trends over time"""
            try:
                trends = self.health_checker.get_health_trends(hours)
                return trends
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/system/health/services/{service_name}")
        async def service_health(service_name: str):
            """Get detailed health for specific service"""
            try:
                metrics = await self.health_checker.get_service_metrics(service_name)
                if metrics is None:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                dependencies = await self.health_checker.check_dependencies(service_name)
                
                return {
                    "service_name": service_name,
                    "health": metrics,
                    "dependencies": dependencies,
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/system/health/circuit-breakers")
        async def circuit_breaker_status():
            """Get circuit breaker status across all services"""
            try:
                return self.health_checker.get_circuit_breaker_summary()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))


# Global system health checker
system_health_checker = SystemHealthChecker()


def get_system_health_router() -> APIRouter:
    """Get system health router for FastAPI app"""
    system_router = SystemHealthRouter(system_health_checker)
    return system_router.router


async def initialize_system_health_monitoring():
    """Initialize system health monitoring"""
    logger.info("System health monitoring initialized")


async def get_system_health_summary():
    """Get current system health summary"""
    return await system_health_checker.check_all_services()


def get_health_trends(hours: int = 24):
    """Get system health trends"""
    return system_health_checker.get_health_trends(hours)
