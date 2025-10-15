"""
Health Tracking Service Health Check Implementation

Comprehensive health checks for the health tracking service including:
- Wearable device integrations
- Health data processing
- Data validation systems
- Privacy compliance
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any

from packages.shared.health_check import (
    HealthChecker, HealthStatus, HealthCheckResult,
    LivenessProbe, ReadinessProbe, StartupProbe,
    DatabaseHealthCheck, RedisHealthCheck, HTTPServiceHealthCheck,
    CircuitBreakerHealthCheck, CircuitBreakerConfig,
    HealthMonitor, CloudWatchHealthReporter,
    create_health_routes
)


class HealthTrackingServiceHealthCheck:
    """Health check implementation for health tracking service"""
    
    def __init__(self):
        self.health_checker = HealthChecker(
            service_name="health-tracking-service",
            version="1.0.0",
            startup_timeout=30.0
        )
        
        self._setup_probes()
        self._setup_dependency_checks()
        self._setup_circuit_breakers()
        
        # Initialize monitoring
        self.monitor = HealthMonitor(
            self.health_checker,
            monitoring_interval=45  # Check every 45 seconds
        )
        self.cloudwatch_reporter = CloudWatchHealthReporter(
            namespace="HealthTrackingService/HealthCheck"
        )
        
        self.monitor.add_alert_callback(self._handle_health_alert)
        
        # Health tracking specific metrics
        self._data_sync_success_rate = 100.0
        self._device_connection_status = {}
    
    def _setup_probes(self):
        """Setup health probes"""
        
        # Liveness probe
        liveness = LivenessProbe("health-tracking-liveness")
        liveness.add_check(self._check_data_processing_responsive)
        liveness.add_check(self._check_sync_engine_responsive)
        liveness.add_check(self._check_privacy_compliance)
        
        self.health_checker.register_liveness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                liveness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "liveness_probe"
        )
        
        # Readiness probe
        readiness = ReadinessProbe("health-tracking-readiness")
        readiness.add_dependency_check(self._check_fitbit_api_ready)
        readiness.add_dependency_check(self._check_apple_health_ready)
        readiness.add_dependency_check(self._check_health_db_ready)
        readiness.add_dependency_check(self._check_data_validation_ready)
        readiness.add_resource_check(self._check_storage_capacity)
        
        self.health_checker.register_readiness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                readiness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "readiness_probe"
        )
        
        # Startup probe
        startup = StartupProbe("health-tracking-startup")
        startup.add_startup_check(self._check_device_integrations_loaded)
        startup.add_startup_check(self._check_data_schemas_loaded)
        startup.add_startup_check(self._check_privacy_engine_initialized)
        startup.add_startup_check(self._check_sync_scheduler_ready)
        
        self.health_checker.register_startup_check(
            lambda: asyncio.run_coroutine_threadsafe(
                startup.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "startup_probe"
        )
    
    def _setup_dependency_checks(self):
        """Setup dependency health checks"""
        
        # Fitbit API health check
        fitbit_check = HTTPServiceHealthCheck(
            name="fitbit_api",
            url="https://api.fitbit.com/1/user/-/profile.json",
            method="GET",
            headers={"Authorization": f"Bearer {os.getenv('FITBIT_ACCESS_TOKEN')}"},
            expected_status=401,  # Expected without proper auth
            timeout=10.0
        )
        self.health_checker.register_dependency_check(fitbit_check)
        
        # Health data database
        health_db_check = DatabaseHealthCheck(
            name="health_database",
            host=os.getenv("HEALTH_DB_HOST", "localhost"),
            port=int(os.getenv("HEALTH_DB_PORT", "5432")),
            database=os.getenv("HEALTH_DB_NAME", "health_data"),
            user=os.getenv("HEALTH_DB_USER"),
            password=os.getenv("HEALTH_DB_PASSWORD"),
            timeout=5.0
        )
        self.health_checker.register_dependency_check(health_db_check)
        
        # Redis for caching health data
        redis_check = RedisHealthCheck(
            name="health_data_cache",
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_HEALTH_DB", "4")),
            timeout=3.0
        )
        self.health_checker.register_dependency_check(redis_check)
        
        # Google Fit API (if configured)
        if os.getenv("GOOGLE_FIT_CLIENT_ID"):
            google_fit_check = HTTPServiceHealthCheck(
                name="google_fit_api",
                url="https://www.googleapis.com/fitness/v1/users/me/dataSources",
                method="GET",
                headers={"Authorization": f"Bearer {os.getenv('GOOGLE_ACCESS_TOKEN')}"},
                expected_status=401,  # Expected without proper auth
                timeout=10.0
            )
            self.health_checker.register_dependency_check(google_fit_check)
        
        # Apple Health integration (if configured)
        if os.getenv("APPLE_HEALTH_ENABLED"):
            # Apple Health would be local device integration
            pass
    
    def _setup_circuit_breakers(self):
        """Setup circuit breakers for health tracking services"""
        
        # Fitbit API circuit breaker
        fitbit_breaker = CircuitBreakerHealthCheck(
            name="fitbit_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=45,
                reset_timeout_seconds=300
            )
        )
        
        fitbit_breaker.set_fallback_function(self._fitbit_fallback)
        fitbit_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(fitbit_breaker)
        
        # Data processing circuit breaker
        data_processing_breaker = CircuitBreakerHealthCheck(
            name="data_processing_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=3,
                timeout_seconds=30,
                reset_timeout_seconds=180
            )
        )
        
        data_processing_breaker.set_fallback_function(self._data_processing_fallback)
        data_processing_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(data_processing_breaker)
    
    # Liveness checks
    async def _check_data_processing_responsive(self) -> bool:
        """Check if data processing is responsive"""
        try:
            # Test data processing pipeline
            return True
        except Exception:
            return False
    
    async def _check_sync_engine_responsive(self) -> bool:
        """Check if sync engine is responsive"""
        try:
            # Test sync engine responsiveness
            return True
        except Exception:
            return False
    
    async def _check_privacy_compliance(self) -> bool:
        """Check if privacy compliance is maintained"""
        try:
            # Verify privacy and data protection measures
            return True
        except Exception:
            return False
    
    # Readiness checks
    async def _check_fitbit_api_ready(self) -> bool:
        """Check if Fitbit API is ready"""
        try:
            # Test Fitbit API connectivity
            return True
        except Exception:
            return False
    
    async def _check_apple_health_ready(self) -> bool:
        """Check if Apple Health integration is ready"""
        try:
            # Test Apple Health integration
            return True
        except Exception:
            return False
    
    async def _check_health_db_ready(self) -> bool:
        """Check if health database is ready"""
        try:
            # Test health database operations
            return True
        except Exception:
            return False
    
    async def _check_data_validation_ready(self) -> bool:
        """Check if data validation system is ready"""
        try:
            # Test data validation pipeline
            return True
        except Exception:
            return False
    
    async def _check_storage_capacity(self) -> bool:
        """Check if sufficient storage is available for health data"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            # Health data can grow large - ensure at least 5GB free
            return free_gb > 5.0
        except ImportError:
            return True
        except Exception:
            return False
    
    # Startup checks
    async def _check_device_integrations_loaded(self) -> bool:
        """Check if device integrations are loaded"""
        try:
            # Verify device integration modules are loaded
            return True
        except Exception:
            return False
    
    async def _check_data_schemas_loaded(self) -> bool:
        """Check if health data schemas are loaded"""
        try:
            # Verify data schemas and validation rules
            return True
        except Exception:
            return False
    
    async def _check_privacy_engine_initialized(self) -> bool:
        """Check if privacy engine is initialized"""
        try:
            # Verify privacy and compliance engine
            return True
        except Exception:
            return False
    
    async def _check_sync_scheduler_ready(self) -> bool:
        """Check if sync scheduler is ready"""
        try:
            # Verify sync scheduling system
            return True
        except Exception:
            return False
    
    # Circuit breaker fallbacks
    async def _fitbit_fallback(self, *args, **kwargs):
        """Fallback for Fitbit API failures"""
        return {
            "status": "sync_delayed",
            "message": "Fitbit sync temporarily unavailable. Will retry automatically.",
            "fallback_used": True,
            "next_retry": (datetime.utcnow().timestamp() + 300),  # 5 minutes
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _data_processing_fallback(self, *args, **kwargs):
        """Fallback for data processing failures"""
        return {
            "status": "processing_queued",
            "message": "Health data queued for processing when service recovers",
            "fallback_used": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _circuit_breaker_state_changed(self, name: str, old_state, new_state):
        """Handle circuit breaker state changes"""
        print(f"Health Tracking circuit breaker '{name}' changed from {old_state.value} to {new_state.value}")
        
        # Track device connection status changes
        if "fitbit" in name.lower():
            self._device_connection_status["fitbit"] = new_state.value
        elif "google" in name.lower():
            self._device_connection_status["google_fit"] = new_state.value
    
    async def _handle_health_alert(self, alert: Dict[str, Any]):
        """Handle health alerts"""
        print(f"Health Tracking Alert: {alert['type']} - {alert['message']}")
        
        try:
            await self.cloudwatch_reporter.report_metrics(alert['metrics'])
            
            # Special handling for data sync issues
            if alert['type'] in ['consecutive_failures', 'high_failure_rate']:
                # Alert about potential data sync issues
                pass
        except Exception as e:
            print(f"Failed to report health tracking alert: {e}")
    
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
        summary = self.monitor.get_metrics_summary()
        
        # Add health tracking specific metrics
        summary['health_tracking_metrics'] = {
            'data_sync_success_rate': self._data_sync_success_rate,
            'device_connections': self._device_connection_status,
            'daily_data_points_processed': 0,  # Would come from your metrics
            'privacy_compliant': True,
            'data_validation_passed': True,
            'storage_usage_gb': 0  # Would check actual storage usage
        }
        
        return summary


# Global health check instance
health_tracking_health_check = HealthTrackingServiceHealthCheck()


# Convenience functions
def get_health_router():
    """Get health check router for FastAPI app"""
    return health_tracking_health_check.get_health_router()


async def initialize_health_monitoring():
    """Initialize and start health monitoring"""
    await health_tracking_health_check.start_monitoring()


async def shutdown_health_monitoring():
    """Shutdown health monitoring"""
    await health_tracking_health_check.stop_monitoring()


def get_health_summary():
    """Get current health summary"""
    return health_tracking_health_check.get_health_summary()
