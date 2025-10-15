"""
Health Check System Usage Examples

This file demonstrates how to use the comprehensive health check system
across different services and scenarios.
"""

import asyncio
import os
from datetime import datetime

# Example 1: Basic Service Health Check Setup
async def example_basic_service_setup():
    """Example of setting up basic health checks for a service"""
    
    from packages.shared.health_check import (
        HealthChecker, LivenessProbe, ReadinessProbe, StartupProbe
    )
    
    # Initialize health checker
    health_checker = HealthChecker(
        service_name="example-service",
        version="1.0.0",
        startup_timeout=30.0
    )
    
    # Setup basic probes
    liveness = LivenessProbe("example-liveness")
    readiness = ReadinessProbe("example-readiness")
    startup = StartupProbe("example-startup")
    
    # Add custom checks
    async def check_database_connection():
        # Your database check logic
        return True
    
    async def check_api_responsiveness():
        # Your API check logic
        return True
    
    liveness.add_check(check_api_responsiveness)
    readiness.add_dependency_check(check_database_connection)
    startup.add_startup_check(check_database_connection)
    
    # Register with health checker
    health_checker.register_liveness_check(
        lambda: asyncio.run_coroutine_threadsafe(
            liveness.check(), asyncio.get_event_loop()
        ).result().status.value == "healthy"
    )
    
    # Perform health checks
    liveness_result = await health_checker.check_liveness()
    print(f"Liveness: {liveness_result.overall_status.value}")
    
    readiness_result = await health_checker.check_readiness()
    print(f"Readiness: {readiness_result.overall_status.value}")


# Example 2: Circuit Breaker Usage
async def example_circuit_breaker():
    """Example of using circuit breakers with health checks"""
    
    from packages.shared.health_check import (
        CircuitBreakerHealthCheck, CircuitBreakerConfig
    )
    
    # Create circuit breaker
    breaker = CircuitBreakerHealthCheck(
        name="external_api_breaker",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=30
        )
    )
    
    # Set fallback function
    async def api_fallback(*args, **kwargs):
        return {"error": "Service temporarily unavailable", "fallback": True}
    
    breaker.set_fallback_function(api_fallback)
    
    # Use circuit breaker
    async def call_external_api():
        # Simulate API call that might fail
        import random
        if random.random() < 0.3:  # 30% failure rate
            raise Exception("API call failed")
        return {"data": "success"}
    
    try:
        result = await breaker.call(call_external_api)
        print(f"API Result: {result}")
    except Exception as e:
        print(f"API Error: {e}")
    
    # Check circuit breaker health
    health_result = await breaker.health_check()
    print(f"Circuit Breaker Health: {health_result.status.value}")


# Example 3: FastAPI Integration
async def example_fastapi_integration():
    """Example of integrating health checks with FastAPI"""
    
    from fastapi import FastAPI
    from packages.shared.health_check import create_health_routes, HealthChecker
    from services.nutrition_service.src.health_check import get_health_router
    
    app = FastAPI(title="Example Service")
    
    # Add health check routes
    health_router = get_health_router()
    app.include_router(health_router, prefix="/health", tags=["health"])
    
    # Add system health routes
    from src.health.system_health import get_system_health_router
    system_router = get_system_health_router()
    app.include_router(system_router, prefix="/system", tags=["system-health"])
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        # Initialize health monitoring
        from services.nutrition_service.src.health_check import initialize_health_monitoring
        await initialize_health_monitoring()
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        # Cleanup health monitoring
        from services.nutrition_service.src.health_check import shutdown_health_monitoring
        await shutdown_health_monitoring()
    
    return app


# Example 4: Custom Dependency Health Check
async def example_custom_dependency():
    """Example of creating a custom dependency health check"""
    
    from packages.shared.health_check import DependencyCheck, HealthCheckResult, HealthStatus
    import time
    
    class CustomAPIHealthCheck(DependencyCheck):
        def __init__(self, api_url: str, api_key: str):
            super().__init__(name="custom_api", timeout=10.0)
            self.api_url = api_url
            self.api_key = api_key
        
        async def check_health(self) -> HealthCheckResult:
            start_time = time.time()
            
            try:
                # Your custom health check logic
                # For example, check API endpoint
                import httpx
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.api_url}/health",
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                
                duration_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return self._create_result(
                        status=HealthStatus.HEALTHY,
                        duration_ms=duration_ms,
                        message="Custom API is healthy",
                        details={"status_code": response.status_code}
                    )
                else:
                    return self._create_result(
                        status=HealthStatus.UNHEALTHY,
                        duration_ms=duration_ms,
                        message=f"Custom API returned {response.status_code}",
                        error=f"HTTP {response.status_code}"
                    )
            
            except Exception as e:
                return self._create_result(
                    status=HealthStatus.UNHEALTHY,
                    duration_ms=(time.time() - start_time) * 1000,
                    message="Custom API check failed",
                    error=str(e)
                )
    
    # Use the custom health check
    custom_check = CustomAPIHealthCheck(
        api_url="https://api.example.com",
        api_key="your-api-key"
    )
    
    result = await custom_check.check_health()
    print(f"Custom API Health: {result.status.value} - {result.message}")


# Example 5: Health Monitoring with Alerts
async def example_health_monitoring():
    """Example of setting up health monitoring with alerts"""
    
    from packages.shared.health_check import HealthMonitor, HealthChecker
    
    # Create health checker
    health_checker = HealthChecker("example-service")
    
    # Create monitor
    monitor = HealthMonitor(
        health_checker=health_checker,
        monitoring_interval=30,  # Check every 30 seconds
        retention_hours=24
    )
    
    # Add alert callback
    async def handle_alert(alert):
        print(f"ALERT: {alert['type']} - {alert['message']}")
        
        # You could send to Slack, email, etc.
        if alert['severity'] == 'critical':
            # Send immediate notification
            pass
    
    monitor.add_alert_callback(handle_alert)
    
    # Start monitoring
    await monitor.start_monitoring()
    
    # Let it run for a bit
    await asyncio.sleep(60)
    
    # Get metrics summary
    summary = monitor.get_metrics_summary()
    print(f"Health Summary: {summary}")
    
    # Stop monitoring
    await monitor.stop_monitoring()


# Example 6: CloudWatch Integration
async def example_cloudwatch_integration():
    """Example of integrating health checks with CloudWatch"""
    
    from src.health.cloudwatch_integration import (
        setup_cloudwatch_monitoring,
        send_health_metrics_to_cloudwatch
    )
    
    # Setup CloudWatch monitoring infrastructure
    setup_result = await setup_cloudwatch_monitoring()
    print(f"CloudWatch Setup: {setup_result}")
    
    # Send sample metrics
    sample_metrics = {
        'system': {
            'health_score': 95.5,
            'healthy_services': 4,
            'unhealthy_services': 1,
            'uptime_seconds': 86400
        },
        'services': {
            'nutrition-service': {
                'health_score': 98.0,
                'avg_response_time_ms': 150,
                'error_rate': 1.2
            },
            'payment-service': {
                'health_score': 85.0,
                'avg_response_time_ms': 300,
                'error_rate': 5.0
            }
        },
        'circuit_breakers': {
            'open_breakers': ['openai_api'],
            'total_breakers': 10
        },
        'dependencies': {
            'Database': 'healthy',
            'Redis': 'healthy',
            'OpenAI': 'unhealthy',
            'AWS': 'healthy'
        }
    }
    
    await send_health_metrics_to_cloudwatch(sample_metrics)
    print("Metrics sent to CloudWatch")


# Example 7: System-wide Health Check
async def example_system_health():
    """Example of checking system-wide health"""
    
    from src.health.system_health import (
        get_system_health_summary,
        get_health_trends
    )
    
    # Get current system health
    system_health = await get_system_health_summary()
    
    print(f"System Status: {system_health.overall_status.value}")
    print(f"Health Score: {system_health.health_score}%")
    print(f"Services: {system_health.healthy_services}/{system_health.total_services} healthy")
    
    if system_health.critical_issues:
        print(f"Critical Issues: {system_health.critical_issues}")
    
    if system_health.warnings:
        print(f"Warnings: {system_health.warnings}")
    
    # Get health trends
    trends = get_health_trends(hours=24)
    print(f"24h Health Trends: {trends}")


# Example 8: Production Deployment Pattern
async def example_production_deployment():
    """Example of production deployment with health checks"""
    
    import logging
    from fastapi import FastAPI
    from contextlib import asynccontextmanager
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Health check instances
    health_services = {}
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info("Starting health check system...")
        
        try:
            # Initialize each service health check
            from services.nutrition_service.src.health_check import nutrition_health_check
            from services.messaging_service.src.health_check import messaging_health_check
            from services.ai_coach_service.src.health_check import ai_coach_health_check
            from services.payment_service.src.health_check import payment_health_check
            from services.health_tracking_service.src.health_check import health_tracking_health_check
            
            health_services.update({
                'nutrition': nutrition_health_check,
                'messaging': messaging_health_check,
                'ai_coach': ai_coach_health_check,
                'payment': payment_health_check,
                'health_tracking': health_tracking_health_check
            })
            
            # Start monitoring for each service
            for name, service in health_services.items():
                await service.start_monitoring()
                logger.info(f"Started health monitoring for {name}")
            
            # Setup CloudWatch monitoring
            from src.health.cloudwatch_integration import setup_cloudwatch_monitoring
            await setup_cloudwatch_monitoring()
            logger.info("CloudWatch monitoring configured")
            
            logger.info("Health check system startup complete")
            
        except Exception as e:
            logger.error(f"Failed to start health check system: {e}")
            raise
        
        yield
        
        # Shutdown
        logger.info("Shutting down health check system...")
        
        for name, service in health_services.items():
            try:
                await service.stop_monitoring()
                logger.info(f"Stopped health monitoring for {name}")
            except Exception as e:
                logger.error(f"Error stopping {name} monitoring: {e}")
        
        logger.info("Health check system shutdown complete")
    
    # Create FastAPI app with health checks
    app = FastAPI(
        title="AI Nutritionist - Production",
        lifespan=lifespan
    )
    
    # Add health check routes
    from src.health.system_health import get_system_health_router
    app.include_router(get_system_health_router(), tags=["health"])
    
    return app


# Main example runner
async def main():
    """Run all examples"""
    
    print("=== Health Check System Examples ===\n")
    
    examples = [
        ("Basic Service Setup", example_basic_service_setup),
        ("Circuit Breaker Usage", example_circuit_breaker),
        ("Custom Dependency Check", example_custom_dependency),
        ("Health Monitoring", example_health_monitoring),
        ("System Health Check", example_system_health),
    ]
    
    for name, example_func in examples:
        print(f"Running: {name}")
        try:
            await example_func()
            print(f"✅ {name} completed successfully\n")
        except Exception as e:
            print(f"❌ {name} failed: {e}\n")


if __name__ == "__main__":
    # Set environment variables for examples
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("REDIS_HOST", "localhost")
    
    # Run examples
    asyncio.run(main())
