"""
Integration tests for the structured logging framework.

Tests all components working together:
- Logging with correlation IDs
- Metrics collection
- Distributed tracing
- Health monitoring
- Business event tracking
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from packages.shared.monitoring import (
    setup_logging, setup_metrics, setup_tracing, get_health_monitor,
    LogLevel, EventType, StructuredLogger, MetricsRegistry,
    InMemoryMetricCollector, BusinessMetrics, HealthMonitor,
    performance_monitor, audit_log, trace_operation
)
from packages.shared.monitoring.setup import (
    MonitoringConfig, MonitoringManager, setup_service_monitoring
)


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.logger = setup_logging(
            service_name="test-service",
            log_level=LogLevel.DEBUG,
            use_cloudwatch=False
        )
    
    def test_basic_logging(self):
        """Test basic structured logging."""
        self.logger.info("Test message", extra={"test_data": "value"})
        self.logger.warn("Warning message")
        self.logger.error("Error message", error=Exception("Test error"))
    
    def test_business_event_logging(self):
        """Test business event logging."""
        self.logger.business_event(
            event_type=EventType.USER_ACTION,
            entity_type="user",
            entity_id="test_user",
            action="login",
            metadata={"source": "web", "success": True}
        )
    
    def test_correlation_id_tracking(self):
        """Test correlation ID tracking across operations."""
        correlation_id = "test_correlation_123"
        self.logger.context.correlation_id = correlation_id
        self.logger.context.user_id = "test_user"
        
        self.logger.info("Operation started")
        
        # Correlation ID should be maintained
        assert self.logger.context.correlation_id == correlation_id
        assert self.logger.context.user_id == "test_user"
    
    def test_operation_context(self):
        """Test operation context manager."""
        with self.logger.operation_context("test_operation", user_id="test_user") as ctx:
            ctx.info("Operation in progress")
            time.sleep(0.01)  # Simulate work
        
        # Context should be restored after operation
        assert self.logger.context.operation != "test_operation"
    
    def test_pii_masking(self):
        """Test PII masking functionality."""
        from packages.shared.monitoring.logging import PIIMasker
        
        data = {
            "email": "user@example.com",
            "phone": "555-123-4567",
            "message": "Contact user@example.com at 555-123-4567"
        }
        
        masked_data = PIIMasker.mask_data(data)
        
        assert "[MASKED_EMAIL]" in str(masked_data)
        assert "[MASKED_PHONE]" in str(masked_data)


class TestMetricsCollection:
    """Test metrics collection functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.collector = InMemoryMetricCollector()
        self.registry = MetricsRegistry(self.collector)
        self.business_metrics = BusinessMetrics(self.registry)
    
    def test_counter_metrics(self):
        """Test counter metrics."""
        counter = self.registry.counter("test_counter")
        
        counter.increment()
        counter.increment(2.0, tags={"service": "test"})
        
        assert counter.get_value() == 3.0
        
        # Check recorded metrics
        metrics = self.collector.get_metrics("test_counter")
        assert len(metrics) == 2
    
    def test_gauge_metrics(self):
        """Test gauge metrics."""
        gauge = self.registry.gauge("test_gauge")
        
        gauge.set(100.0)
        gauge.increment(50.0)
        gauge.decrement(25.0)
        
        assert gauge.get_value() == 125.0
    
    def test_histogram_metrics(self):
        """Test histogram metrics."""
        histogram = self.registry.histogram("test_histogram")
        
        # Record some observations
        for value in [100, 200, 300, 400, 500]:
            histogram.observe(value)
        
        summary = histogram.get_summary()
        
        assert summary["count"] == 5
        assert summary["min"] == 100
        assert summary["max"] == 500
        assert summary["avg"] == 300
    
    def test_business_metrics(self):
        """Test business metrics tracking."""
        self.business_metrics.track_user_action("login", "user_123", success=True)
        self.business_metrics.track_api_request("/api/test", "GET", 200, 150.0)
        self.business_metrics.track_database_operation("select", "users", 25.0, success=True)
        
        # Verify metrics were recorded
        all_metrics = self.registry.get_all_metrics()
        assert "user_action_login_total" in all_metrics["counters"]
        assert "api_requests_total" in all_metrics["counters"]
        assert "db_operations_total" in all_metrics["counters"]


class TestDistributedTracing:
    """Test distributed tracing functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.tracer = setup_tracing(
            service_name="test-service",
            use_xray=False,
            use_logging=True
        )
    
    def test_basic_tracing(self):
        """Test basic span creation and management."""
        with self.tracer.trace("test_operation") as span:
            span.add_tag("test_tag", "test_value")
            span.add_log("Test log message")
            time.sleep(0.01)
        
        assert span.status.value == "OK"
        assert span.duration_ms is not None
        assert span.duration_ms > 0
    
    def test_nested_spans(self):
        """Test nested span relationships."""
        with self.tracer.trace("parent_operation") as parent_span:
            parent_span.add_tag("level", "parent")
            
            with self.tracer.trace("child_operation") as child_span:
                child_span.add_tag("level", "child")
                assert child_span.parent_span_id == parent_span.span_id
                assert child_span.trace_id == parent_span.trace_id
    
    def test_span_error_handling(self):
        """Test span error handling."""
        try:
            with self.tracer.trace("error_operation") as span:
                raise Exception("Test error")
        except Exception:
            pass
        
        assert span.status.value == "ERROR"
        assert "error" in span.tags
        assert span.tags["error"] == "true"
    
    def test_trace_operation_decorator(self):
        """Test trace operation decorator."""
        @trace_operation("decorated_operation")
        def test_function():
            time.sleep(0.01)
            return "success"
        
        result = test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_async_trace_operation_decorator(self):
        """Test async trace operation decorator."""
        @trace_operation("async_decorated_operation")
        async def async_test_function():
            await asyncio.sleep(0.01)
            return "async_success"
        
        result = await async_test_function()
        assert result == "async_success"


class TestHealthMonitoring:
    """Test health monitoring functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.health_monitor = HealthMonitor("test-service")
    
    @pytest.mark.asyncio
    async def test_basic_health_checks(self):
        """Test basic health check functionality."""
        from packages.shared.monitoring.health import MemoryHealthCheck, DiskHealthCheck
        
        # Add health checks
        self.health_monitor.add_check(MemoryHealthCheck())
        self.health_monitor.add_check(DiskHealthCheck())
        
        # Run health check
        health_status = await self.health_monitor.check_health()
        
        assert health_status.service_name == "test-service"
        assert len(health_status.checks) == 2
        assert health_status.uptime_seconds is not None
    
    @pytest.mark.asyncio
    async def test_custom_health_check(self):
        """Test custom health check implementation."""
        from packages.shared.monitoring.health import HealthCheck, HealthStatus, HealthCheckResult
        
        class TestHealthCheck(HealthCheck):
            def __init__(self, should_pass: bool):
                super().__init__("test_check")
                self.should_pass = should_pass
            
            async def check(self) -> HealthCheckResult:
                if self.should_pass:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.HEALTHY,
                        message="Test check passed"
                    )
                else:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message="Test check failed"
                    )
        
        # Test passing check
        self.health_monitor.add_check(TestHealthCheck(should_pass=True))
        health_status = await self.health_monitor.check_health()
        assert health_status.status == HealthStatus.HEALTHY
        
        # Test failing check
        self.health_monitor.add_check(TestHealthCheck(should_pass=False))
        health_status = await self.health_monitor.check_health()
        assert health_status.status == HealthStatus.UNHEALTHY


class TestPerformanceDecorators:
    """Test performance monitoring decorators."""
    
    def setup_method(self):
        """Setup test environment."""
        self.logger = setup_logging("test-service", LogLevel.DEBUG, use_cloudwatch=False)
    
    def test_performance_monitor_decorator(self):
        """Test performance monitor decorator."""
        @performance_monitor("test_function")
        def test_function():
            time.sleep(0.01)
            return "success"
        
        result = test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_async_performance_monitor_decorator(self):
        """Test async performance monitor decorator."""
        @performance_monitor("async_test_function")
        async def async_test_function():
            await asyncio.sleep(0.01)
            return "async_success"
        
        result = await async_test_function()
        assert result == "async_success"
    
    def test_audit_log_decorator(self):
        """Test audit log decorator."""
        @audit_log(EventType.USER_ACTION, "user", "update")
        def update_user(user_id: str):
            return f"Updated user {user_id}"
        
        result = update_user("test_user")
        assert result == "Updated user test_user"
    
    def test_combined_decorators(self):
        """Test multiple decorators working together."""
        @performance_monitor("combined_operation")
        @audit_log(EventType.BUSINESS_EVENT, "data", "process")
        @trace_operation("combined_trace")
        def combined_function(data: str):
            time.sleep(0.01)
            return f"Processed {data}"
        
        result = combined_function("test_data")
        assert result == "Processed test_data"


class TestMonitoringIntegration:
    """Test complete monitoring integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = MonitoringConfig(
            service_name="integration-test",
            environment="test",
            log_level=LogLevel.DEBUG,
            use_cloudwatch_logs=False,
            use_cloudwatch_metrics=False,
            use_xray=False,
            enable_health_checks=True
        )
        self.monitoring = MonitoringManager(self.config)
    
    def test_complete_setup(self):
        """Test complete monitoring setup."""
        self.monitoring.setup_all()
        
        assert self.monitoring.logger is not None
        assert self.monitoring.metrics is not None
        assert self.monitoring.tracer is not None
        assert self.monitoring.health_monitor is not None
        assert self.monitoring.business_metrics is not None
    
    @pytest.mark.asyncio
    async def test_integrated_operation(self):
        """Test integrated operation with all monitoring components."""
        self.monitoring.setup_all()
        
        logger = self.monitoring.get_logger()
        metrics = self.monitoring.get_metrics()
        tracer = self.monitoring.get_tracer()
        business_metrics = self.monitoring.get_business_metrics()
        
        # Set context
        logger.context.correlation_id = "integration_test_123"
        logger.context.user_id = "test_user"
        
        # Perform integrated operation
        with tracer.trace("integrated_operation") as span:
            logger.info("Starting integrated operation")
            
            # Track metrics
            counter = metrics.counter("integration_operations")
            counter.increment(tags={"type": "test"})
            
            # Track business event
            logger.business_event(
                event_type=EventType.BUSINESS_EVENT,
                entity_type="integration",
                action="test_operation",
                metadata={"test": True}
            )
            
            # Simulate work
            await asyncio.sleep(0.01)
            
            span.add_tag("operation_type", "integration_test")
            logger.info("Integrated operation completed")
        
        # Verify health status
        health_monitor = self.monitoring.get_health_monitor()
        if health_monitor:
            health_status = await health_monitor.check_health()
            assert health_status.service_name == "integration-test"
    
    def test_service_monitoring_setup(self):
        """Test service monitoring setup function."""
        monitoring = setup_service_monitoring("test-service", self.config)
        
        assert monitoring.logger is not None
        assert monitoring.metrics is not None
        assert monitoring.tracer is not None


class TestErrorScenarios:
    """Test error scenarios and resilience."""
    
    def setup_method(self):
        """Setup test environment."""
        self.logger = setup_logging("error-test", LogLevel.DEBUG, use_cloudwatch=False)
    
    def test_logging_with_invalid_data(self):
        """Test logging with invalid or problematic data."""
        # Test with circular reference
        circular_data = {"key": "value"}
        circular_data["self"] = circular_data
        
        # Should not raise exception
        self.logger.info("Test with circular data", extra={"data": str(circular_data)[:100]})
    
    def test_metrics_with_invalid_values(self):
        """Test metrics with invalid values."""
        collector = InMemoryMetricCollector()
        registry = MetricsRegistry(collector)
        
        counter = registry.counter("test_counter")
        
        # Test with valid values
        counter.increment(1.0)
        
        # Test with invalid values (should raise ValueError)
        with pytest.raises(ValueError):
            counter.increment(-1.0)  # Negative increment
    
    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Test health check timeout handling."""
        from packages.shared.monitoring.health import HealthCheck, HealthCheckResult, HealthStatus
        
        class TimeoutHealthCheck(HealthCheck):
            def __init__(self):
                super().__init__("timeout_check", timeout_seconds=0.001)
            
            async def check(self) -> HealthCheckResult:
                await asyncio.sleep(0.1)  # Longer than timeout
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Should not reach here"
                )
        
        health_monitor = HealthMonitor("timeout-test")
        health_monitor.add_check(TimeoutHealthCheck())
        
        # Should handle timeout gracefully
        health_status = await health_monitor.check_health()
        assert len(health_status.checks) == 1
        # Check should be marked as unhealthy due to timeout or exception


class TestCloudWatchIntegration:
    """Test CloudWatch integration (mocked)."""
    
    @patch('boto3.client')
    def test_cloudwatch_logs_setup(self, mock_boto_client):
        """Test CloudWatch logs setup."""
        mock_logs_client = Mock()
        mock_boto_client.return_value = mock_logs_client
        
        from packages.shared.monitoring.logging import CloudWatchLogHandler
        
        handler = CloudWatchLogHandler(
            log_group="/test/log-group",
            log_stream="test-stream"
        )
        
        # Mock successful log group creation
        mock_logs_client.create_log_group.return_value = {}
        mock_logs_client.create_log_stream.return_value = {}
        mock_logs_client.put_log_events.return_value = {"nextSequenceToken": "token123"}
        
        # Test log handling
        handler.handle('{"test": "log message"}')
        
        # Verify client was called
        mock_logs_client.put_log_events.assert_called_once()
    
    @patch('boto3.client')
    def test_cloudwatch_metrics_setup(self, mock_boto_client):
        """Test CloudWatch metrics setup."""
        mock_cloudwatch_client = Mock()
        mock_boto_client.return_value = mock_cloudwatch_client
        
        from packages.shared.monitoring.metrics import CloudWatchMetricCollector
        
        collector = CloudWatchMetricCollector("TestNamespace")
        
        # Mock successful metric put
        mock_cloudwatch_client.put_metric_data.return_value = {}
        
        # Record some metrics
        collector.record("test_metric", 123.45, {"service": "test"})
        collector.flush()
        
        # Verify client was called
        mock_cloudwatch_client.put_metric_data.assert_called_once()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
