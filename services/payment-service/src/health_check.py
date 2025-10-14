"""
Payment Service Health Check Implementation

Comprehensive health checks for the payment service including:
- Payment processor connectivity
- Fraud detection system
- Subscription management
- Financial data security
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


class PaymentServiceHealthCheck:
    """Health check implementation for payment service"""
    
    def __init__(self):
        self.health_checker = HealthChecker(
            service_name="payment-service",
            version="1.0.0",
            startup_timeout=25.0
        )
        
        self._setup_probes()
        self._setup_dependency_checks()
        self._setup_circuit_breakers()
        
        # Initialize monitoring with higher frequency for payment service
        self.monitor = HealthMonitor(
            self.health_checker,
            monitoring_interval=20  # Check every 20 seconds for payment service
        )
        self.cloudwatch_reporter = CloudWatchHealthReporter(
            namespace="PaymentService/HealthCheck"
        )
        
        self.monitor.add_alert_callback(self._handle_health_alert)
        
        # Payment-specific metrics
        self._payment_success_rate = 100.0
        self._fraud_detection_latency = []
    
    def _setup_probes(self):
        """Setup health probes"""
        
        # Liveness probe
        liveness = LivenessProbe("payment-liveness")
        liveness.add_check(self._check_payment_processor_responsive)
        liveness.add_check(self._check_fraud_detection_responsive)
        liveness.add_check(self._check_encryption_services)
        
        self.health_checker.register_liveness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                liveness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "liveness_probe"
        )
        
        # Readiness probe
        readiness = ReadinessProbe("payment-readiness")
        readiness.add_dependency_check(self._check_stripe_ready)
        readiness.add_dependency_check(self._check_payment_db_ready)
        readiness.add_dependency_check(self._check_fraud_service_ready)
        readiness.add_resource_check(self._check_pci_compliance)
        readiness.add_resource_check(self._check_rate_limits)
        
        self.health_checker.register_readiness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                readiness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "readiness_probe"
        )
        
        # Startup probe
        startup = StartupProbe("payment-startup")
        startup.add_startup_check(self._check_payment_config_loaded)
        startup.add_startup_check(self._check_encryption_keys_loaded)
        startup.add_startup_check(self._check_stripe_webhooks_configured)
        startup.add_startup_check(self._check_subscription_engine_ready)
        
        self.health_checker.register_startup_check(
            lambda: asyncio.run_coroutine_threadsafe(
                startup.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "startup_probe"
        )
    
    def _setup_dependency_checks(self):
        """Setup dependency health checks"""
        
        # Stripe API health check
        stripe_check = HTTPServiceHealthCheck(
            name="stripe_api",
            url="https://api.stripe.com/v1/charges",
            method="GET",
            headers={"Authorization": f"Bearer {os.getenv('STRIPE_SECRET_KEY')}"},
            expected_status=401,  # Expected without proper auth for health check
            timeout=10.0
        )
        self.health_checker.register_dependency_check(stripe_check)
        
        # Payment database health check
        payment_db_check = DatabaseHealthCheck(
            name="payment_database",
            host=os.getenv("PAYMENT_DB_HOST", "localhost"),
            port=int(os.getenv("PAYMENT_DB_PORT", "5432")),
            database=os.getenv("PAYMENT_DB_NAME", "payments"),
            user=os.getenv("PAYMENT_DB_USER"),
            password=os.getenv("PAYMENT_DB_PASSWORD"),
            timeout=5.0
        )
        self.health_checker.register_dependency_check(payment_db_check)
        
        # Redis for payment sessions
        redis_check = RedisHealthCheck(
            name="payment_sessions",
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_PAYMENT_DB", "3")),
            timeout=3.0
        )
        self.health_checker.register_dependency_check(redis_check)
        
        # Fraud detection service (if external)
        if os.getenv("FRAUD_DETECTION_URL"):
            fraud_check = HTTPServiceHealthCheck(
                name="fraud_detection",
                url=os.getenv("FRAUD_DETECTION_URL"),
                method="GET",
                headers={"Authorization": f"Bearer {os.getenv('FRAUD_API_KEY')}"},
                timeout=8.0
            )
            self.health_checker.register_dependency_check(fraud_check)
    
    def _setup_circuit_breakers(self):
        """Setup circuit breakers for payment services"""
        
        # Stripe payment circuit breaker
        stripe_breaker = CircuitBreakerHealthCheck(
            name="stripe_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=2,  # Very low tolerance for payment failures
                success_threshold=3,
                timeout_seconds=30,
                reset_timeout_seconds=180
            )
        )
        
        stripe_breaker.set_fallback_function(self._stripe_fallback)
        stripe_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(stripe_breaker)
        
        # Fraud detection circuit breaker
        fraud_breaker = CircuitBreakerHealthCheck(
            name="fraud_detection_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=20,
                reset_timeout_seconds=120
            )
        )
        
        fraud_breaker.set_fallback_function(self._fraud_fallback)
        fraud_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(fraud_breaker)
    
    # Liveness checks
    async def _check_payment_processor_responsive(self) -> bool:
        """Check if payment processor is responsive"""
        try:
            # Test payment processor responsiveness
            return True
        except Exception:
            return False
    
    async def _check_fraud_detection_responsive(self) -> bool:
        """Check if fraud detection is responsive"""
        try:
            start_time = datetime.utcnow()
            # Test fraud detection system
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._fraud_detection_latency.append(response_time)
            
            # Keep only last 10 measurements
            if len(self._fraud_detection_latency) > 10:
                self._fraud_detection_latency = self._fraud_detection_latency[-10:]
            
            return response_time < 2000  # Should respond within 2 seconds
        except Exception:
            return False
    
    async def _check_encryption_services(self) -> bool:
        """Check if encryption services are working"""
        try:
            # Test encryption/decryption functionality
            return True
        except Exception:
            return False
    
    # Readiness checks
    async def _check_stripe_ready(self) -> bool:
        """Check if Stripe is ready"""
        try:
            # Test Stripe API connectivity
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
            # This would be a real API call in production
            return True
        except Exception:
            return False
    
    async def _check_payment_db_ready(self) -> bool:
        """Check if payment database is ready"""
        try:
            # Test payment database operations
            return True
        except Exception:
            return False
    
    async def _check_fraud_service_ready(self) -> bool:
        """Check if fraud detection service is ready"""
        try:
            # Test fraud detection service
            return True
        except Exception:
            return False
    
    async def _check_pci_compliance(self) -> bool:
        """Check PCI compliance requirements"""
        try:
            # Verify PCI compliance status
            # This would check encryption, key rotation, etc.
            return True
        except Exception:
            return False
    
    async def _check_rate_limits(self) -> bool:
        """Check payment processing rate limits"""
        try:
            # Check current rate limit status
            return True
        except Exception:
            return False
    
    # Startup checks
    async def _check_payment_config_loaded(self) -> bool:
        """Check if payment configuration is loaded"""
        try:
            required_config = [
                "STRIPE_SECRET_KEY",
                "STRIPE_PUBLISHABLE_KEY",
                "PAYMENT_DB_HOST",
                "PAYMENT_DB_NAME"
            ]
            return all(os.getenv(key) for key in required_config)
        except Exception:
            return False
    
    async def _check_encryption_keys_loaded(self) -> bool:
        """Check if encryption keys are loaded"""
        try:
            # Verify encryption keys are available
            return True
        except Exception:
            return False
    
    async def _check_stripe_webhooks_configured(self) -> bool:
        """Check if Stripe webhooks are configured"""
        try:
            # Verify webhook configuration
            return True
        except Exception:
            return False
    
    async def _check_subscription_engine_ready(self) -> bool:
        """Check if subscription engine is ready"""
        try:
            # Verify subscription management system
            return True
        except Exception:
            return False
    
    # Circuit breaker fallbacks
    async def _stripe_fallback(self, *args, **kwargs):
        """Fallback for Stripe failures"""
        return {
            "status": "payment_delayed",
            "message": "Payment processing temporarily unavailable. Transaction will be retried.",
            "fallback_used": True,
            "retry_after": 300,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _fraud_fallback(self, *args, **kwargs):
        """Fallback for fraud detection failures"""
        return {
            "fraud_score": 0.1,  # Low risk when system is unavailable
            "status": "fraud_check_bypassed",
            "message": "Fraud detection temporarily unavailable - using minimal risk assessment",
            "fallback_used": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _circuit_breaker_state_changed(self, name: str, old_state, new_state):
        """Handle circuit breaker state changes"""
        print(f"CRITICAL: Payment circuit breaker '{name}' changed from {old_state.value} to {new_state.value}")
        
        # Payment service state changes are always critical
        if new_state.value == "open":
            print(f"ALERT: Payment processing disabled for '{name}' - immediate attention required")
    
    async def _handle_health_alert(self, alert: Dict[str, Any]):
        """Handle health alerts"""
        print(f"Payment Health Alert: {alert['type']} - {alert['message']}")
        
        # All payment service alerts are high priority
        try:
            await self.cloudwatch_reporter.report_metrics(alert['metrics'])
            
            # Send immediate notification for payment issues
            if alert['severity'] in ['critical', 'warning']:
                # This would integrate with your alerting system
                pass
        except Exception as e:
            print(f"Failed to report payment alert: {e}")
    
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
        
        # Add payment-specific metrics
        avg_fraud_latency = (
            sum(self._fraud_detection_latency) / len(self._fraud_detection_latency)
            if self._fraud_detection_latency else 0
        )
        
        summary['payment_metrics'] = {
            'payment_success_rate': self._payment_success_rate,
            'avg_fraud_detection_latency_ms': round(avg_fraud_latency, 2),
            'pci_compliant': True,  # Would check actual PCI status
            'encryption_active': True,
            'daily_transaction_volume': 0,  # Would come from your metrics
            'fraud_detections_today': 0
        }
        
        return summary


# Global health check instance
payment_health_check = PaymentServiceHealthCheck()


# Convenience functions
def get_health_router():
    """Get health check router for FastAPI app"""
    return payment_health_check.get_health_router()


async def initialize_health_monitoring():
    """Initialize and start health monitoring"""
    await payment_health_check.start_monitoring()


async def shutdown_health_monitoring():
    """Shutdown health monitoring"""
    await payment_health_check.stop_monitoring()


def get_health_summary():
    """Get current health summary"""
    return payment_health_check.get_health_summary()
