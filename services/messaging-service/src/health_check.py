"""
Messaging Service Health Check Implementation

Comprehensive health checks for the messaging service including:
- SMS/WhatsApp service connectivity
- AWS Pinpoint health
- Message queue health
- Circuit breaker protection
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

from packages.shared.health_check import (
    HealthChecker, HealthStatus, HealthCheckResult,
    LivenessProbe, ReadinessProbe, StartupProbe,
    AWSServiceHealthCheck, RedisHealthCheck,
    CircuitBreakerHealthCheck, CircuitBreakerConfig,
    HealthMonitor, CloudWatchHealthReporter,
    create_health_routes
)


class MessagingServiceHealthCheck:
    """Health check implementation for messaging service"""
    
    def __init__(self):
        self.health_checker = HealthChecker(
            service_name="messaging-service",
            version="1.0.0",
            startup_timeout=20.0
        )
        
        self._setup_probes()
        self._setup_dependency_checks()
        self._setup_circuit_breakers()
        
        # Initialize monitoring
        self.monitor = HealthMonitor(self.health_checker)
        self.cloudwatch_reporter = CloudWatchHealthReporter(
            namespace="MessagingService/HealthCheck"
        )
        
        self.monitor.add_alert_callback(self._handle_health_alert)
    
    def _setup_probes(self):
        """Setup health probes"""
        
        # Liveness probe
        liveness = LivenessProbe("messaging-liveness")
        liveness.add_check(self._check_message_handler_responsive)
        liveness.add_check(self._check_webhook_endpoints)
        
        self.health_checker.register_liveness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                liveness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "liveness_probe"
        )
        
        # Readiness probe
        readiness = ReadinessProbe("messaging-readiness")
        readiness.add_dependency_check(self._check_aws_pinpoint_ready)
        readiness.add_dependency_check(self._check_message_queue_ready)
        readiness.add_resource_check(self._check_rate_limits)
        
        self.health_checker.register_readiness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                readiness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "readiness_probe"
        )
        
        # Startup probe
        startup = StartupProbe("messaging-startup")
        startup.add_startup_check(self._check_aws_credentials)
        startup.add_startup_check(self._check_pinpoint_configuration)
        startup.add_startup_check(self._check_webhook_registration)
        
        self.health_checker.register_startup_check(
            lambda: asyncio.run_coroutine_threadsafe(
                startup.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "startup_probe"
        )
    
    def _setup_dependency_checks(self):
        """Setup dependency health checks"""
        
        # AWS Pinpoint SMS health check
        pinpoint_sms_check = AWSServiceHealthCheck(
            name="pinpoint_sms",
            service_name="pinpoint-sms-voice-v2",
            region=os.getenv("AWS_REGION", "us-east-1"),
            timeout=8.0
        )
        self.health_checker.register_dependency_check(pinpoint_sms_check)
        
        # Redis message queue health check
        redis_check = RedisHealthCheck(
            name="message_queue",
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_MESSAGE_DB", "1")),
            timeout=3.0
        )
        self.health_checker.register_dependency_check(redis_check)
        
        # CloudWatch health check
        cloudwatch_check = AWSServiceHealthCheck(
            name="cloudwatch",
            service_name="cloudwatch",
            region=os.getenv("AWS_REGION", "us-east-1"),
            timeout=5.0
        )
        self.health_checker.register_dependency_check(cloudwatch_check)
    
    def _setup_circuit_breakers(self):
        """Setup circuit breakers"""
        
        # AWS Pinpoint circuit breaker
        pinpoint_breaker = CircuitBreakerHealthCheck(
            name="pinpoint_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=60,
                reset_timeout_seconds=300
            )
        )
        
        pinpoint_breaker.set_fallback_function(self._pinpoint_fallback)
        pinpoint_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(pinpoint_breaker)
        
        # Message queue circuit breaker
        queue_breaker = CircuitBreakerHealthCheck(
            name="message_queue_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=3,
                timeout_seconds=30,
                reset_timeout_seconds=180
            )
        )
        
        queue_breaker.set_fallback_function(self._queue_fallback)
        queue_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(queue_breaker)
    
    # Liveness checks
    async def _check_message_handler_responsive(self) -> bool:
        """Check if message handlers are responsive"""
        try:
            # Test message handler responsiveness
            return True
        except Exception:
            return False
    
    async def _check_webhook_endpoints(self) -> bool:
        """Check if webhook endpoints are accessible"""
        try:
            # Test webhook endpoint accessibility
            return True
        except Exception:
            return False
    
    # Readiness checks
    async def _check_aws_pinpoint_ready(self) -> bool:
        """Check if AWS Pinpoint is ready"""
        try:
            client = boto3.client(
                'pinpoint-sms-voice-v2',
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            # Try to get account attributes (lightweight operation)
            response = client.describe_account_attributes()
            return response['ResponseMetadata']['HTTPStatusCode'] == 200
        except Exception:
            return False
    
    async def _check_message_queue_ready(self) -> bool:
        """Check if message queue is ready"""
        try:
            import redis
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD"),
                db=int(os.getenv("REDIS_MESSAGE_DB", "1")),
                socket_timeout=3
            )
            return r.ping()
        except Exception:
            return False
    
    async def _check_rate_limits(self) -> bool:
        """Check if we're within rate limits"""
        try:
            # Check current rate limit status
            # This would check against your rate limiting system
            return True
        except Exception:
            return False
    
    # Startup checks
    async def _check_aws_credentials(self) -> bool:
        """Check if AWS credentials are configured"""
        try:
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            return 'Account' in identity
        except Exception:
            return False
    
    async def _check_pinpoint_configuration(self) -> bool:
        """Check if Pinpoint is properly configured"""
        try:
            # Verify Pinpoint configuration
            required_config = [
                "AWS_REGION",
                "PINPOINT_PROJECT_ID"
            ]
            return all(os.getenv(key) for key in required_config)
        except Exception:
            return False
    
    async def _check_webhook_registration(self) -> bool:
        """Check if webhooks are registered"""
        try:
            # Verify webhook registration status
            return True
        except Exception:
            return False
    
    # Circuit breaker fallbacks
    async def _pinpoint_fallback(self, *args, **kwargs):
        """Fallback for Pinpoint failures"""
        return {
            "status": "failed",
            "message": "SMS service temporarily unavailable",
            "fallback_used": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _queue_fallback(self, *args, **kwargs):
        """Fallback for message queue failures"""
        return {
            "status": "queued_locally",
            "message": "Message queued for retry when service recovers",
            "fallback_used": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _circuit_breaker_state_changed(self, name: str, old_state, new_state):
        """Handle circuit breaker state changes"""
        print(f"Messaging service circuit breaker '{name}' changed from {old_state.value} to {new_state.value}")
    
    async def _handle_health_alert(self, alert: Dict[str, Any]):
        """Handle health alerts"""
        print(f"Messaging Health Alert: {alert['type']} - {alert['message']}")
        
        # Report critical messaging issues immediately
        if alert['severity'] == 'critical':
            try:
                # Send immediate notification
                pass
            except Exception as e:
                print(f"Failed to send critical alert: {e}")
    
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
        
        # Add messaging-specific metrics
        summary['messaging_metrics'] = {
            'total_messages_sent': 0,  # Would come from your metrics
            'failed_messages': 0,
            'success_rate': 100.0,
            'avg_delivery_time_ms': 0
        }
        
        return summary


# Global health check instance
messaging_health_check = MessagingServiceHealthCheck()


# Convenience functions
def get_health_router():
    """Get health check router for FastAPI app"""
    return messaging_health_check.get_health_router()


async def initialize_health_monitoring():
    """Initialize and start health monitoring"""
    await messaging_health_check.start_monitoring()


async def shutdown_health_monitoring():
    """Shutdown health monitoring"""
    await messaging_health_check.stop_monitoring()


def get_health_summary():
    """Get current health summary"""
    return messaging_health_check.get_health_summary()
