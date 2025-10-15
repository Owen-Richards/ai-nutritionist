"""
Tests for Chaos Engineering Framework

Comprehensive test suite for validating chaos engineering functionality
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Import chaos engineering components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'chaos-engineering'))

from core.chaos_engine import ChaosEngine, ExperimentConfig, SeverityLevel, ExperimentStatus
from core.experiment_runner import ExperimentRunner
from monitoring.chaos_monitor import ChaosMonitor
from failure_injection.service_failure import ServiceFailureInjector, FailureConfig, FailureType


class TestChaosEngine:
    """Test cases for ChaosEngine"""
    
    @pytest.fixture
    def chaos_engine(self):
        return ChaosEngine()
    
    @pytest.fixture
    def experiment_config(self):
        return ExperimentConfig(
            name="Test Experiment",
            description="Test experiment for unit testing",
            severity=SeverityLevel.LOW,
            duration_seconds=10,
            target_services=["test_service"],
            failure_conditions={"test": True},
            success_criteria={"max_errors": 5},
            rollback_strategy="immediate"
        )
    
    def test_chaos_engine_initialization(self, chaos_engine):
        """Test ChaosEngine initialization"""
        assert chaos_engine is not None
        assert chaos_engine.experiments == {}
        assert chaos_engine.active_experiments == {}
        assert not chaos_engine.is_emergency_stop
    
    @pytest.mark.asyncio
    async def test_pre_flight_checks(self, chaos_engine, experiment_config):
        """Test pre-flight safety checks"""
        # Mock the individual check methods
        with patch.object(chaos_engine, '_check_system_health', return_value=True), \
             patch.object(chaos_engine, '_check_concurrent_experiments', return_value=True), \
             patch.object(chaos_engine, '_check_business_hours', return_value=True), \
             patch.object(chaos_engine, '_check_deployment_status', return_value=True):
            
            result = await chaos_engine._pre_flight_checks(experiment_config)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_pre_flight_checks_failure(self, chaos_engine, experiment_config):
        """Test pre-flight checks with failures"""
        with patch.object(chaos_engine, '_check_system_health', return_value=False):
            result = await chaos_engine._pre_flight_checks(experiment_config)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_emergency_stop_all(self, chaos_engine):
        """Test emergency stop functionality"""
        # Add a mock active experiment
        mock_task = AsyncMock()
        chaos_engine.active_experiments["test_experiment"] = mock_task
        
        await chaos_engine.emergency_stop_all()
        
        assert chaos_engine.is_emergency_stop is True
        # The emergency stop should have been called on the experiment
        # (actual implementation would cancel the task)
    
    def test_get_experiment_status(self, chaos_engine, experiment_config):
        """Test getting experiment status"""
        experiment_id = "test_experiment_123"
        
        # No experiment exists
        result = chaos_engine.get_experiment_status(experiment_id)
        assert result is None
        
        # Add mock experiment result
        from core.chaos_engine import ExperimentResult
        mock_result = ExperimentResult(
            experiment_id=experiment_id,
            name=experiment_config.name,
            status=ExperimentStatus.COMPLETED,
            start_time=datetime.now(),
            end_time=None,
            duration_seconds=None,
            success=True,
            error_count=0,
            recovery_time_seconds=None
        )
        chaos_engine.experiments[experiment_id] = mock_result
        
        result = chaos_engine.get_experiment_status(experiment_id)
        assert result == mock_result


class TestExperimentRunner:
    """Test cases for ExperimentRunner"""
    
    @pytest.fixture
    def experiment_runner(self):
        chaos_engine = ChaosEngine()
        return ExperimentRunner(chaos_engine)
    
    def test_experiment_runner_initialization(self, experiment_runner):
        """Test ExperimentRunner initialization"""
        assert experiment_runner is not None
        assert experiment_runner.chaos_engine is not None
        assert len(experiment_runner.templates) > 0
    
    def test_get_available_templates(self, experiment_runner):
        """Test getting available templates"""
        templates = experiment_runner.get_available_templates()
        
        assert isinstance(templates, list)
        assert len(templates) > 0
        assert "service_failure" in templates
        assert "network_chaos" in templates
        assert "database_chaos" in templates
    
    def test_get_template_info(self, experiment_runner):
        """Test getting template information"""
        info = experiment_runner.get_template_info("service_failure")
        
        assert info is not None
        assert "name" in info
        assert "description" in info
        assert "severity" in info
        assert "duration_seconds" in info
    
    def test_get_template_info_invalid(self, experiment_runner):
        """Test getting info for invalid template"""
        info = experiment_runner.get_template_info("nonexistent_template")
        assert info is None
    
    @pytest.mark.asyncio
    async def test_run_template_invalid(self, experiment_runner):
        """Test running invalid template"""
        with pytest.raises(ValueError, match="Template 'invalid_template' not found"):
            await experiment_runner.run_template("invalid_template")


class TestServiceFailureInjector:
    """Test cases for ServiceFailureInjector"""
    
    @pytest.fixture
    def failure_config(self):
        return FailureConfig(
            failure_type=FailureType.SHUTDOWN,
            target_service="test_service",
            failure_rate=1.0,
            duration_seconds=10
        )
    
    @pytest.fixture
    def service_injector(self, failure_config):
        return ServiceFailureInjector(failure_config)
    
    def test_service_injector_initialization(self, service_injector, failure_config):
        """Test ServiceFailureInjector initialization"""
        assert service_injector is not None
        assert service_injector.config == failure_config
        assert not service_injector.is_active
        assert service_injector.original_state == {}
    
    @pytest.mark.asyncio
    async def test_setup(self, service_injector):
        """Test injector setup"""
        with patch.object(service_injector, '_capture_service_state', return_value={"test": "state"}), \
             patch.object(service_injector, '_validate_target_service', return_value=True):
            
            await service_injector.setup()
            assert service_injector.original_state == {"test": "state"}
    
    @pytest.mark.asyncio
    async def test_setup_invalid_service(self, service_injector):
        """Test setup with invalid service"""
        with patch.object(service_injector, '_capture_service_state', return_value={}), \
             patch.object(service_injector, '_validate_target_service', return_value=False):
            
            with pytest.raises(ValueError, match="Target service test_service not found"):
                await service_injector.setup()
    
    def test_get_injection_status(self, service_injector):
        """Test getting injection status"""
        status = service_injector.get_injection_status()
        
        assert isinstance(status, dict)
        assert "is_active" in status
        assert "failure_type" in status
        assert "target_service" in status
        assert status["is_active"] is False
        assert status["target_service"] == "test_service"


class TestChaosMonitor:
    """Test cases for ChaosMonitor"""
    
    @pytest.fixture
    def chaos_monitor(self):
        return ChaosMonitor()
    
    def test_monitor_initialization(self, chaos_monitor):
        """Test ChaosMonitor initialization"""
        assert chaos_monitor is not None
        assert chaos_monitor.collection_interval == 5
        assert chaos_monitor.retention_hours == 24
        assert len(chaos_monitor.metrics) == 0
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, chaos_monitor):
        """Test starting monitoring"""
        experiment_id = "test_experiment"
        
        with patch.object(chaos_monitor, '_collect_baseline_metrics') as mock_baseline, \
             patch.object(chaos_monitor, '_continuous_monitoring') as mock_continuous:
            
            mock_baseline.return_value = None
            mock_continuous.return_value = AsyncMock()
            
            await chaos_monitor.start_monitoring(experiment_id)
            
            mock_baseline.assert_called_once_with(experiment_id)
            assert experiment_id in chaos_monitor.active_monitors
    
    @pytest.mark.asyncio
    async def test_collect_system_snapshot(self, chaos_monitor):
        """Test collecting system snapshot"""
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_io_counters') as mock_network, \
             patch('psutil.pids', return_value=[1, 2, 3]):
            
            # Mock memory object
            mock_memory.return_value.percent = 60.0
            
            # Mock disk object
            mock_disk.return_value.used = 500
            mock_disk.return_value.total = 1000
            
            # Mock network object
            mock_network.return_value.bytes_sent = 1000
            mock_network.return_value.bytes_recv = 2000
            mock_network.return_value.packets_sent = 10
            mock_network.return_value.packets_recv = 20
            
            snapshot = await chaos_monitor._collect_system_snapshot()
            
            assert snapshot.cpu_usage == 50.0
            assert snapshot.memory_usage == 60.0
            assert snapshot.disk_usage == 50.0  # (500/1000) * 100
            assert snapshot.process_count == 3
            assert snapshot.network_io["bytes_sent"] == 1000
    
    def test_add_custom_collector(self, chaos_monitor):
        """Test adding custom metric collector"""
        async def custom_collector():
            return {"test_metric": 42.0}
        
        chaos_monitor.add_custom_collector(custom_collector)
        
        assert len(chaos_monitor.custom_collectors) == 1
        assert chaos_monitor.custom_collectors[0] == custom_collector


class TestIntegration:
    """Integration tests for chaos engineering framework"""
    
    @pytest.mark.asyncio
    async def test_full_experiment_workflow(self):
        """Test complete experiment workflow"""
        # Create components
        chaos_engine = ChaosEngine()
        monitor = ChaosMonitor()
        
        # Create experiment configuration
        config = ExperimentConfig(
            name="Integration Test",
            description="Full workflow integration test",
            severity=SeverityLevel.LOW,
            duration_seconds=1,  # Very short for testing
            target_services=["test_service"],
            failure_conditions={"test": True},
            success_criteria={"max_errors": 0},
            rollback_strategy="immediate"
        )
        
        # Mock injector
        mock_injector = Mock()
        mock_injector.setup = AsyncMock()
        mock_injector.inject_failure = AsyncMock()
        mock_injector.stop_failure = AsyncMock()
        mock_injector.cleanup = AsyncMock()
        mock_injector.emergency_rollback = AsyncMock()
        
        # Mock monitor methods
        monitor.collect_metrics = AsyncMock(return_value={"cpu": 50})
        monitor.is_recovered = AsyncMock(return_value=True)
        monitor.calculate_impact = AsyncMock(return_value={"impact": 0.1})
        
        # Mock safety checks to pass
        with patch.object(chaos_engine, '_pre_flight_checks', return_value=True), \
             patch.object(chaos_engine, '_collect_baseline_metrics', return_value={"baseline": True}), \
             patch.object(chaos_engine, '_collect_impact_metrics', return_value={"impact": 0.1}), \
             patch.object(chaos_engine, '_measure_recovery_time', return_value=1.0), \
             patch.object(chaos_engine, '_evaluate_success', return_value=True), \
             patch.object(chaos_engine, '_generate_recommendations', return_value=["Test recommendation"]):
            
            # Run experiment
            result = await chaos_engine.run_experiment(
                config=config,
                injectors=[mock_injector],
                monitors=[monitor]
            )
            
            # Verify result
            assert result is not None
            assert result.name == "Integration Test"
            assert result.success is True
            assert result.recovery_time_seconds == 1.0
            
            # Verify injector was called
            mock_injector.setup.assert_called_once()
            mock_injector.inject_failure.assert_called_once()
            mock_injector.stop_failure.assert_called_once()
            mock_injector.cleanup.assert_called_once()


# Performance and load tests
class TestPerformance:
    """Performance tests for chaos engineering framework"""
    
    @pytest.mark.asyncio
    async def test_monitoring_performance(self):
        """Test monitoring performance under load"""
        monitor = ChaosMonitor()
        
        # Simulate high-frequency metric collection
        start_time = time.time()
        
        for i in range(100):
            snapshot = await monitor._collect_system_snapshot()
            assert snapshot is not None
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 100 snapshots in reasonable time (< 5 seconds)
        assert duration < 5.0
        
        # Average time per snapshot should be reasonable (< 50ms)
        avg_time = duration / 100
        assert avg_time < 0.05
    
    @pytest.mark.asyncio
    async def test_concurrent_experiments(self):
        """Test handling multiple concurrent experiments"""
        chaos_engine = ChaosEngine()
        
        # Create multiple experiment configurations
        configs = []
        for i in range(3):
            config = ExperimentConfig(
                name=f"Concurrent Test {i}",
                description=f"Concurrent experiment {i}",
                severity=SeverityLevel.LOW,
                duration_seconds=1,
                target_services=[f"test_service_{i}"],
                failure_conditions={"test": True},
                success_criteria={"max_errors": 0},
                rollback_strategy="immediate"
            )
            configs.append(config)
        
        # Mock components for all experiments
        with patch.object(chaos_engine, '_pre_flight_checks', return_value=True), \
             patch.object(chaos_engine, '_collect_baseline_metrics', return_value={}), \
             patch.object(chaos_engine, '_collect_impact_metrics', return_value={}), \
             patch.object(chaos_engine, '_measure_recovery_time', return_value=1.0), \
             patch.object(chaos_engine, '_evaluate_success', return_value=True), \
             patch.object(chaos_engine, '_generate_recommendations', return_value=[]):
            
            # Create mock injectors
            mock_injectors = []
            for i in range(3):
                mock_injector = Mock()
                mock_injector.setup = AsyncMock()
                mock_injector.inject_failure = AsyncMock()
                mock_injector.stop_failure = AsyncMock()
                mock_injector.cleanup = AsyncMock()
                mock_injector.emergency_rollback = AsyncMock()
                mock_injectors.append([mock_injector])
            
            # Run experiments concurrently
            tasks = [
                chaos_engine.run_experiment(config, injectors, [])
                for config, injectors in zip(configs, mock_injectors)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all experiments completed successfully
            assert len(results) == 3
            for result in results:
                assert result is not None
                assert result.success is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
