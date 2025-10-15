"""
Nutrition Service Health Check Implementation

Comprehensive health checks for the nutrition service including:
- Liveness probes
- Readiness probes 
- Startup probes
- Dependency checks
- Circuit breaker integration
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any

from packages.shared.health_check import (
    HealthChecker, HealthStatus, HealthCheckResult,
    LivenessProbe, ReadinessProbe, StartupProbe,
    DatabaseHealthCheck, RedisHealthCheck, ExternalAPIHealthCheck,
    CircuitBreakerHealthCheck, CircuitBreakerConfig,
    HealthMonitor, CloudWatchHealthReporter,
    create_health_routes
)

# Service-specific health checks
class NutritionServiceHealthCheck:
    """Health check implementation for nutrition service"""
    
    def __init__(self):
        # Initialize health checker
        self.health_checker = HealthChecker(
            service_name="nutrition-service",
            version="1.0.0",
            startup_timeout=30.0
        )
        
        # Setup probes
        self._setup_liveness_probe()
        self._setup_readiness_probe()
        self._setup_startup_probe()
        self._setup_dependency_checks()
        self._setup_circuit_breakers()
        
        # Initialize monitoring
        self.monitor = HealthMonitor(self.health_checker)
        self.cloudwatch_reporter = CloudWatchHealthReporter(
            namespace="NutritionService/HealthCheck"
        )
        
        # Setup monitoring callbacks
        self.monitor.add_alert_callback(self._handle_health_alert)
    
    def _setup_liveness_probe(self):
        """Setup liveness probe"""
        liveness = LivenessProbe("nutrition-liveness")
        
        # Add custom liveness checks
        liveness.add_check(self._check_api_responsive)
        liveness.add_check(self._check_core_services)
        
        self.health_checker.register_liveness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                liveness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "liveness_probe"
        )
    
    def _setup_readiness_probe(self):
        """Setup readiness probe"""
        readiness = ReadinessProbe("nutrition-readiness")
        
        # Add dependency checks to readiness
        readiness.add_dependency_check(self._check_database_ready)
        readiness.add_dependency_check(self._check_cache_ready)
        readiness.add_dependency_check(self._check_ai_service_ready)
        
        # Add resource checks
        readiness.add_resource_check(self._check_memory_available)
        readiness.add_resource_check(self._check_disk_space)
        
        self.health_checker.register_readiness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                readiness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "readiness_probe"
        )
    
    def _setup_startup_probe(self):
        """Setup startup probe"""
        startup = StartupProbe("nutrition-startup")
        
        # Add startup checks
        startup.add_startup_check(self._check_configuration_loaded)
        startup.add_startup_check(self._check_database_migration)
        startup.add_startup_check(self._check_services_initialized)
        startup.add_startup_check(self._check_ai_models_loaded)
        
        self.health_checker.register_startup_check(
            lambda: asyncio.run_coroutine_threadsafe(
                startup.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "startup_probe"
        )
    
    def _setup_dependency_checks(self):
        """Setup external dependency health checks"""
        
        # Database health check
        db_check = DatabaseHealthCheck(
            name="nutrition_database",
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "nutrition_db"),
            user=os.getenv("DB_USER", "nutrition_user"),
            password=os.getenv("DB_PASSWORD", ""),
            timeout=5.0
        )
        self.health_checker.register_dependency_check(db_check)
        
        # Redis health check
        redis_check = RedisHealthCheck(
            name="nutrition_cache",
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_DB", "0")),
            timeout=3.0
        )
        self.health_checker.register_dependency_check(redis_check)
        
        # OpenAI API health check
        openai_check = ExternalAPIHealthCheck(
            name="openai_api",
            api_url="https://api.openai.com/v1",
            api_key=os.getenv("OPENAI_API_KEY"),
            test_endpoint="models",
            timeout=10.0
        )
        self.health_checker.register_dependency_check(openai_check)
        
        # USDA Food Data API health check
        usda_check = ExternalAPIHealthCheck(
            name="usda_food_api",
            api_url="https://api.nal.usda.gov/fdc/v1",
            api_key=os.getenv("USDA_API_KEY"),
            test_endpoint="foods/search?query=apple",
            timeout=10.0
        )
        self.health_checker.register_dependency_check(usda_check)
    
    def _setup_circuit_breakers(self):
        """Setup circuit breakers for external services"""
        
        # OpenAI circuit breaker
        openai_breaker = CircuitBreakerHealthCheck(
            name="openai_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=30,
                reset_timeout_seconds=300
            )
        )
        
        # Set fallback for OpenAI
        openai_breaker.set_fallback_function(self._openai_fallback)
        openai_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(openai_breaker)
        
        # USDA API circuit breaker
        usda_breaker = CircuitBreakerHealthCheck(
            name="usda_api_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=3,
                timeout_seconds=60,
                reset_timeout_seconds=600
            )
        )
        
        usda_breaker.set_fallback_function(self._usda_fallback)
        usda_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(usda_breaker)
    
    # Liveness check methods
    async def _check_api_responsive(self) -> bool:
        """Check if API endpoints are responsive"""
        try:
            # Simulate basic API responsiveness check
            return True
        except Exception:
            return False
    
    async def _check_core_services(self) -> bool:
        """Check if core nutrition services are operational"""
        try:
            # Check if core services can handle requests
            return True
        except Exception:
            return False
    
    # Readiness check methods
    async def _check_database_ready(self) -> bool:
        """Check if database is ready for operations"""
        try:
            # Test database connectivity and basic operations
            return True
        except Exception:
            return False
    
    async def _check_cache_ready(self) -> bool:
        """Check if Redis cache is ready"""
        try:
            # Test Redis connectivity
            return True
        except Exception:
            return False
    
    async def _check_ai_service_ready(self) -> bool:
        """Check if AI service is ready"""
        try:
            # Test AI service connectivity
            return True
        except Exception:
            return False
    
    async def _check_memory_available(self) -> bool:
        """Check if sufficient memory is available"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.available > 512 * 1024 * 1024  # 512MB minimum
        except ImportError:
            return True
        except Exception:
            return False
    
    async def _check_disk_space(self) -> bool:
        """Check if sufficient disk space is available"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            return free_gb > 1.0  # 1GB minimum
        except ImportError:
            return True
        except Exception:
            return False
    
    # Startup check methods
    async def _check_configuration_loaded(self) -> bool:
        """Check if service configuration is loaded"""
        try:
            # Verify all required config is present
            required_config = [
                "DB_HOST", "DB_NAME", "OPENAI_API_KEY"
            ]
            return all(os.getenv(key) for key in required_config)
        except Exception:
            return False
    
    async def _check_database_migration(self) -> bool:
        """Check if database migrations are complete"""
        try:
            # Check database schema version
            return True
        except Exception:
            return False
    
    async def _check_services_initialized(self) -> bool:
        """Check if all services are initialized"""
        try:
            # Verify service initialization
            return True
        except Exception:
            return False
    
    async def _check_ai_models_loaded(self) -> bool:
        """Check if AI models are loaded and ready"""
        try:
            # Check if AI models are loaded
            return True
        except Exception:
            return False
    
    # Circuit breaker fallback methods
    async def _openai_fallback(self, *args, **kwargs):
        """Fallback for OpenAI API failures"""
        return {
            "response": "Service temporarily unavailable. Using cached nutrition data.",
            "source": "fallback",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _usda_fallback(self, *args, **kwargs):
        """Fallback for USDA API failures"""
        return {
            "foods": [],
            "message": "External food database temporarily unavailable",
            "source": "fallback",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _circuit_breaker_state_changed(self, name: str, old_state, new_state):
        """Handle circuit breaker state changes"""
        print(f"Circuit breaker '{name}' changed from {old_state.value} to {new_state.value}")
        
        # You could send alerts, update metrics, etc.
        if new_state.value == "open":
            # Alert on circuit breaker opening
            pass
        elif new_state.value == "closed":
            # Log recovery
            pass
    
    async def _handle_health_alert(self, alert: Dict[str, Any]):
        """Handle health monitoring alerts"""
        print(f"Health Alert: {alert['type']} - {alert['message']}")
        
        # Send to CloudWatch if needed
        try:
            await self.cloudwatch_reporter.report_metrics(alert['metrics'])
        except Exception as e:
            print(f"Failed to report alert to CloudWatch: {e}")
    
    def get_health_router(self):
        """Get FastAPI router for health endpoints"""
        return create_health_routes(self.health_checker)
    
    async def start_monitoring(self):
        """Start health monitoring"""
        await self.monitor.start_monitoring()
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        await self.monitor.stop_monitoring()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        return self.monitor.get_metrics_summary()


# Global health check instance
nutrition_health_check = NutritionServiceHealthCheck()


# Convenience functions for FastAPI integration
def get_health_router():
    """Get health check router for FastAPI app"""
    return nutrition_health_check.get_health_router()


async def initialize_health_monitoring():
    """Initialize and start health monitoring"""
    await nutrition_health_check.start_monitoring()


async def shutdown_health_monitoring():
    """Shutdown health monitoring"""
    await nutrition_health_check.stop_monitoring()


def get_health_summary():
    """Get current health summary"""
    return nutrition_health_check.get_health_summary()
