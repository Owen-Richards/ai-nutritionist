#!/usr/bin/env python3
"""
Test Generator for AI Nutritionist

Generates comprehensive test suites with:
- Unit tests
- Integration tests
- Performance tests
- Load tests
- Mock factories
- Test fixtures
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestConfig:
    """Configuration for test generation"""
    target_file: str
    test_type: str  # unit, integration, performance, load
    class_name: Optional[str] = None
    function_names: List[str] = None
    has_async: bool = True
    has_database: bool = False
    has_api: bool = False
    has_cache: bool = False


class TestGenerator:
    """Generates comprehensive test suites"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    def generate_tests(self, config: TestConfig) -> Dict[str, str]:
        """Generate complete test suite"""
        files = {}
        
        if config.test_type == "unit":
            files.update(self._generate_unit_tests(config))
        elif config.test_type == "integration":
            files.update(self._generate_integration_tests(config))
        elif config.test_type == "performance":
            files.update(self._generate_performance_tests(config))
        elif config.test_type == "load":
            files.update(self._generate_load_tests(config))
        elif config.test_type == "all":
            files.update(self._generate_unit_tests(config))
            files.update(self._generate_integration_tests(config))
            files.update(self._generate_performance_tests(config))
        
        # Generate test fixtures and factories
        files.update(self._generate_test_fixtures(config))
        
        return files
    
    def _generate_unit_tests(self, config: TestConfig) -> Dict[str, str]:
        """Generate unit tests"""
        target_name = Path(config.target_file).stem
        
        return {
            f"tests/unit/test_{target_name}.py": self._create_unit_test_file(config)
        }
    
    def _generate_integration_tests(self, config: TestConfig) -> Dict[str, str]:
        """Generate integration tests"""
        target_name = Path(config.target_file).stem
        
        return {
            f"tests/integration/test_{target_name}_integration.py": self._create_integration_test_file(config)
        }
    
    def _generate_performance_tests(self, config: TestConfig) -> Dict[str, str]:
        """Generate performance tests"""
        target_name = Path(config.target_file).stem
        
        return {
            f"tests/performance/test_{target_name}_performance.py": self._create_performance_test_file(config)
        }
    
    def _generate_load_tests(self, config: TestConfig) -> Dict[str, str]:
        """Generate load tests"""
        target_name = Path(config.target_file).stem
        
        return {
            f"tests/load/test_{target_name}_load.py": self._create_load_test_file(config)
        }
    
    def _generate_test_fixtures(self, config: TestConfig) -> Dict[str, str]:
        """Generate test fixtures and factories"""
        target_name = Path(config.target_file).stem
        
        return {
            f"tests/fixtures/{target_name}_fixtures.py": self._create_fixtures_file(config),
            f"tests/factories/{target_name}_factory.py": self._create_factory_file(config)
        }
    
    def _create_unit_test_file(self, config: TestConfig) -> str:
        """Create unit test file content"""
        target_name = Path(config.target_file).stem
        class_name = config.class_name or f"{target_name.title().replace('_', '')}"
        
        imports = [
            "import pytest",
            "from unittest.mock import Mock, AsyncMock, patch, MagicMock",
            "from datetime import datetime",
            "import json",
            ""
        ]
        
        if config.has_async:
            imports.append("import asyncio")
        
        if config.has_database:
            imports.extend([
                "from moto import mock_dynamodb",
                "import boto3"
            ])
        
        if config.has_api:
            imports.extend([
                "from fastapi.testclient import TestClient",
                "from httpx import AsyncClient"
            ])
        
        if config.has_cache:
            imports.append("from unittest.mock import patch")
        
        # Import the module being tested
        module_path = config.target_file.replace("/", ".").replace(".py", "")
        imports.append(f"from {module_path} import {class_name}")
        
        test_methods = []
        
        if config.function_names:
            for func_name in config.function_names:
                test_methods.append(self._generate_test_method(func_name, config))
        else:
            # Generate common test patterns
            test_methods.extend([
                self._generate_initialization_test(class_name, config),
                self._generate_success_test(class_name, config),
                self._generate_error_test(class_name, config),
                self._generate_validation_test(class_name, config)
            ])
        
        fixtures = self._generate_test_fixtures_code(config)
        
        return f'''"""
Unit tests for {class_name}

Generated test suite covering:
- Initialization and configuration
- Success scenarios
- Error handling
- Edge cases
- Validation
"""

{chr(10).join(imports)}

{fixtures}

class Test{class_name}:
    """Comprehensive test suite for {class_name}"""
    
{chr(10).join(test_methods)}
    
    {'@pytest.mark.asyncio' if config.has_async else ''}
    {'async ' if config.has_async else ''}def test_edge_cases(self{', mock_instance' if config.class_name else ''}):
        """Test edge cases and boundary conditions"""
        # Add edge case tests here
        pass
    
    def test_performance_characteristics(self{', mock_instance' if config.class_name else ''}):
        """Test performance characteristics"""
        import time
        
        start_time = time.time()
        # Add performance test logic here
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
    
    {'@pytest.mark.asyncio' if config.has_async else ''}
    {'async ' if config.has_async else ''}def test_concurrent_operations(self{', mock_instance' if config.class_name else ''}):
        """Test concurrent operations"""
        {'import asyncio' if config.has_async else ''}
        {'tasks = []' if config.has_async else ''}
        {'for i in range(10):' if config.has_async else ''}
        {'    # Add concurrent test tasks' if config.has_async else ''}
        {'    pass' if config.has_async else ''}
        {'    ' if config.has_async else ''}
        {'if tasks:' if config.has_async else ''}
        {'    results = await asyncio.gather(*tasks)' if config.has_async else ''}
        {'    assert len(results) == 10' if config.has_async else ''}
'''
    
    def _generate_test_method(self, func_name: str, config: TestConfig) -> str:
        """Generate a test method for a specific function"""
        return f'''    {'@pytest.mark.asyncio' if config.has_async else ''}
    {'async ' if config.has_async else ''}def test_{func_name}_success(self{', mock_instance' if config.class_name else ''}):
        """Test {func_name} success scenario"""
        # Arrange
        # Add test setup here
        
        # Act
        {'result = await ' if config.has_async else 'result = '}{f'mock_instance.{func_name}()' if config.class_name else f'{func_name}()'}
        
        # Assert
        assert result is not None
    
    {'@pytest.mark.asyncio' if config.has_async else ''}
    {'async ' if config.has_async else ''}def test_{func_name}_error(self{', mock_instance' if config.class_name else ''}):
        """Test {func_name} error handling"""
        # Arrange
        # Add error setup here
        
        # Act & Assert
        with pytest.raises(Exception):
            {'await ' if config.has_async else ''}{f'mock_instance.{func_name}()' if config.class_name else f'{func_name}()'}
'''
    
    def _generate_initialization_test(self, class_name: str, config: TestConfig) -> str:
        """Generate initialization test"""
        return f'''    def test_initialization(self):
        """Test {class_name} initialization"""
        # Arrange & Act
        instance = {class_name}()
        
        # Assert
        assert instance is not None
        assert hasattr(instance, '__dict__')
'''
    
    def _generate_success_test(self, class_name: str, config: TestConfig) -> str:
        """Generate success scenario test"""
        return f'''    {'@pytest.mark.asyncio' if config.has_async else ''}
    {'async ' if config.has_async else ''}def test_main_functionality_success(self, mock_instance):
        """Test main functionality success scenario"""
        # Arrange
        test_data = {{"test": "data"}}
        
        # Act
        {'result = await mock_instance.process(test_data)' if config.has_async else 'result = mock_instance.process(test_data)'}
        
        # Assert
        assert result is not None
'''
    
    def _generate_error_test(self, class_name: str, config: TestConfig) -> str:
        """Generate error handling test"""
        return f'''    {'@pytest.mark.asyncio' if config.has_async else ''}
    {'async ' if config.has_async else ''}def test_error_handling(self, mock_instance):
        """Test error handling scenarios"""
        # Arrange
        invalid_data = None
        
        # Act & Assert
        with pytest.raises(Exception):
            {'await mock_instance.process(invalid_data)' if config.has_async else 'mock_instance.process(invalid_data)'}
'''
    
    def _generate_validation_test(self, class_name: str, config: TestConfig) -> str:
        """Generate validation test"""
        return f'''    {'@pytest.mark.asyncio' if config.has_async else ''}
    {'async ' if config.has_async else ''}def test_input_validation(self, mock_instance):
        """Test input validation"""
        # Test various invalid inputs
        invalid_inputs = [
            None,
            "",
            {{}},
            [],
            "invalid_string",
            -1,
            {{"missing": "required_field"}}
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises((ValueError, TypeError, ValidationError)):
                {'await mock_instance.validate(invalid_input)' if config.has_async else 'mock_instance.validate(invalid_input)'}
'''
    
    def _generate_test_fixtures_code(self, config: TestConfig) -> str:
        """Generate test fixtures"""
        fixtures = []
        
        if config.class_name:
            fixtures.append(f'''@pytest.fixture
def mock_instance():
    """Create mock instance for testing"""
    return Mock(spec={config.class_name})''')
        
        if config.has_database:
            fixtures.append('''@pytest.fixture
def mock_database():
    """Mock database for testing"""
    with mock_dynamodb():
        yield boto3.resource('dynamodb', region_name='us-east-1')''')
        
        if config.has_api:
            fixtures.append('''@pytest.fixture
def test_client():
    """Test client for API testing"""
    from main import app
    return TestClient(app)''')
        
        if config.has_cache:
            fixtures.append('''@pytest.fixture
def mock_cache():
    """Mock cache for testing"""
    return Mock()''')
        
        return chr(10).join(fixtures)
    
    def _create_integration_test_file(self, config: TestConfig) -> str:
        """Create integration test file content"""
        target_name = Path(config.target_file).stem
        class_name = config.class_name or f"{target_name.title().replace('_', '')}"
        
        return f'''"""
Integration tests for {class_name}

Tests the complete workflow with real dependencies
"""

import pytest
import asyncio
from datetime import datetime
import json

{'from moto import mock_dynamodb' if config.has_database else ''}
{'import boto3' if config.has_database else ''}
{'from fastapi.testclient import TestClient' if config.has_api else ''}

from {config.target_file.replace("/", ".").replace(".py", "")} import {class_name}


{'@mock_dynamodb' if config.has_database else ''}
class Test{class_name}Integration:
    """Integration test suite for {class_name}"""
    
    {'@pytest.fixture(autouse=True)' if config.has_database else ''}
    {'def setup_database(self):' if config.has_database else ''}
    {'    """Setup test database"""' if config.has_database else ''}
    {'    # Create test database tables' if config.has_database else ''}
    {'    pass' if config.has_database else ''}
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        # Arrange
        instance = {class_name}()
        test_data = {{"test": "integration_data"}}
        
        # Act
        result = await instance.process(test_data)
        
        # Assert
        assert result is not None
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_real_dependencies_integration(self):
        """Test integration with real dependencies"""
        # Test with actual external services
        pass
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery scenarios"""
        # Test how the system recovers from failures
        pass
    
    @pytest.mark.asyncio
    async def test_data_consistency(self):
        """Test data consistency across operations"""
        # Verify data remains consistent
        pass
'''
    
    def _create_performance_test_file(self, config: TestConfig) -> str:
        """Create performance test file content"""
        target_name = Path(config.target_file).stem
        class_name = config.class_name or f"{target_name.title().replace('_', '')}"
        
        return f'''"""
Performance tests for {class_name}

Tests performance characteristics and benchmarks
"""

import pytest
import time
import asyncio
from datetime import datetime
import statistics
import psutil
import threading

from {config.target_file.replace("/", ".").replace(".py", "")} import {class_name}


class Test{class_name}Performance:
    """Performance test suite for {class_name}"""
    
    def test_response_time_benchmark(self):
        """Test response time under normal load"""
        instance = {class_name}()
        response_times = []
        
        for _ in range(100):
            start_time = time.time()
            # Execute operation
            result = instance.process({{"test": "data"}})
            end_time = time.time()
            
            response_times.append(end_time - start_time)
        
        # Performance assertions
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        assert avg_response_time < 0.1  # Average under 100ms
        assert p95_response_time < 0.5   # 95th percentile under 500ms
        assert max(response_times) < 1.0 # No operation over 1 second
    
    @pytest.mark.asyncio
    async def test_concurrent_performance(self):
        """Test performance under concurrent load"""
        instance = {class_name}()
        concurrent_requests = 50
        
        start_time = time.time()
        
        # Execute concurrent operations
        tasks = []
        for i in range(concurrent_requests):
            task = instance.process({{"request_id": i}})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        throughput = concurrent_requests / total_time
        
        # Performance assertions
        assert len(results) == concurrent_requests
        assert throughput > 10  # At least 10 requests per second
        assert total_time < 10  # Complete within 10 seconds
    
    def test_memory_usage(self):
        """Test memory usage characteristics"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        instance = {class_name}()
        
        # Perform memory-intensive operations
        for _ in range(1000):
            instance.process({{"large_data": "x" * 1000}})
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory assertions (in bytes)
        assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase
    
    def test_cpu_usage(self):
        """Test CPU usage under load"""
        instance = {class_name}()
        
        def cpu_intensive_work():
            for _ in range(1000):
                instance.process({{"cpu_test": "data"}})
        
        # Monitor CPU usage
        cpu_before = psutil.cpu_percent(interval=1)
        
        # Execute CPU-intensive work
        thread = threading.Thread(target=cpu_intensive_work)
        thread.start()
        thread.join()
        
        cpu_after = psutil.cpu_percent(interval=1)
        
        # CPU usage should be reasonable
        assert cpu_after < 80  # Less than 80% CPU usage
    
    @pytest.mark.asyncio
    async def test_throughput_benchmark(self):
        """Test maximum throughput"""
        instance = {class_name}()
        duration = 10  # seconds
        request_count = 0
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            await instance.process({{"throughput_test": request_count}})
            request_count += 1
        
        throughput = request_count / duration
        
        # Throughput assertions
        assert throughput > 50  # At least 50 requests per second
        print(f"Achieved throughput: {{throughput:.2f}} requests/second")
    
    def test_scalability_characteristics(self):
        """Test how performance scales with load"""
        instance = {class_name}()
        load_levels = [10, 50, 100, 200, 500]
        response_times = []
        
        for load in load_levels:
            times = []
            
            for _ in range(load):
                start_time = time.time()
                instance.process({{"load_test": load}})
                end_time = time.time()
                times.append(end_time - start_time)
            
            avg_time = statistics.mean(times)
            response_times.append(avg_time)
        
        # Scalability assertions
        # Response time should not increase exponentially
        for i in range(1, len(response_times)):
            ratio = response_times[i] / response_times[i-1]
            assert ratio < 2.0  # Response time shouldn't double with each load increase
'''
    
    def _create_load_test_file(self, config: TestConfig) -> str:
        """Create load test file content"""
        target_name = Path(config.target_file).stem
        class_name = config.class_name or f"{target_name.title().replace('_', '')}"
        
        return f'''"""
Load tests for {class_name}

Stress testing and load testing scenarios
"""

import pytest
import asyncio
import time
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import statistics
import psutil

from {config.target_file.replace("/", ".").replace(".py", "")} import {class_name}


class Test{class_name}Load:
    """Load test suite for {class_name}"""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test performance under sustained load"""
        instance = {class_name}()
        duration = 60  # 1 minute
        target_rps = 100  # requests per second
        
        start_time = time.time()
        request_count = 0
        errors = 0
        response_times = []
        
        while time.time() - start_time < duration:
            batch_start = time.time()
            
            # Send a batch of requests
            tasks = []
            for _ in range(target_rps):
                request_start = time.time()
                try:
                    task = instance.process({{"load_test": request_count}})
                    tasks.append((task, request_start))
                    request_count += 1
                except Exception:
                    errors += 1
            
            # Wait for batch completion
            for task, req_start in tasks:
                try:
                    await task
                    response_time = time.time() - req_start
                    response_times.append(response_time)
                except Exception:
                    errors += 1
            
            # Control request rate
            batch_duration = time.time() - batch_start
            if batch_duration < 1.0:
                await asyncio.sleep(1.0 - batch_duration)
        
        # Analyze results
        total_requests = request_count
        actual_rps = total_requests / duration
        error_rate = errors / total_requests if total_requests > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # Load test assertions
        assert actual_rps >= target_rps * 0.8  # At least 80% of target RPS
        assert error_rate < 0.01  # Less than 1% error rate
        assert avg_response_time < 1.0  # Average response time under 1 second
        
        print(f"Achieved RPS: {{actual_rps:.2f}}")
        print(f"Error rate: {{error_rate:.2%}}")
        print(f"Average response time: {{avg_response_time:.3f}}s")
    
    @pytest.mark.slow
    def test_stress_testing(self):
        """Test system under extreme stress"""
        instance = {class_name}()
        max_workers = 100
        requests_per_worker = 100
        
        def worker_function(worker_id):
            results = []
            errors = 0
            
            for i in range(requests_per_worker):
                try:
                    start_time = time.time()
                    result = instance.process({{
                        "worker_id": worker_id,
                        "request_id": i,
                        "stress_test": True
                    }})
                    end_time = time.time()
                    
                    results.append({{
                        "success": True,
                        "response_time": end_time - start_time,
                        "result": result
                    }})
                except Exception as e:
                    errors += 1
                    results.append({{
                        "success": False,
                        "error": str(e)
                    }})
            
            return results, errors
        
        # Execute stress test
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for worker_id in range(max_workers):
                future = executor.submit(worker_function, worker_id)
                futures.append(future)
            
            # Collect results
            all_results = []
            total_errors = 0
            
            for future in futures:
                results, errors = future.result()
                all_results.extend(results)
                total_errors += errors
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze stress test results
        total_requests = len(all_results)
        successful_requests = sum(1 for r in all_results if r["success"])
        success_rate = successful_requests / total_requests
        overall_rps = total_requests / total_duration
        
        response_times = [r["response_time"] for r in all_results if r["success"]]
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]
        else:
            avg_response_time = 0
            p95_response_time = 0
        
        # Stress test assertions
        assert success_rate > 0.95  # At least 95% success rate
        assert avg_response_time < 2.0  # Average response time under 2 seconds
        assert p95_response_time < 5.0  # 95th percentile under 5 seconds
        
        print(f"Total requests: {{total_requests}}")
        print(f"Success rate: {{success_rate:.2%}}")
        print(f"Overall RPS: {{overall_rps:.2f}}")
        print(f"Average response time: {{avg_response_time:.3f}}s")
        print(f"95th percentile: {{p95_response_time:.3f}}s")
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_spike_load(self):
        """Test system response to sudden load spikes"""
        instance = {class_name}()
        
        # Baseline load
        baseline_rps = 10
        spike_rps = 500
        spike_duration = 30  # seconds
        
        results = []
        
        # Phase 1: Baseline load
        print("Starting baseline load...")
        for _ in range(baseline_rps * 10):  # 10 seconds
            start_time = time.time()
            await instance.process({{"phase": "baseline"}})
            response_time = time.time() - start_time
            results.append({{"phase": "baseline", "response_time": response_time}})
            await asyncio.sleep(1 / baseline_rps)
        
        # Phase 2: Load spike
        print("Starting load spike...")
        spike_tasks = []
        spike_start = time.time()
        
        for i in range(spike_rps * spike_duration):
            task = instance.process({{"phase": "spike", "request": i}})
            spike_tasks.append(task)
            
            if len(spike_tasks) >= spike_rps:
                # Process batch
                start_time = time.time()
                await asyncio.gather(*spike_tasks, return_exceptions=True)
                batch_time = time.time() - start_time
                results.append({{"phase": "spike", "response_time": batch_time}})
                spike_tasks = []
                
                # Control spike rate
                if batch_time < 1.0:
                    await asyncio.sleep(1.0 - batch_time)
        
        # Process remaining tasks
        if spike_tasks:
            await asyncio.gather(*spike_tasks, return_exceptions=True)
        
        # Phase 3: Recovery
        print("Testing recovery...")
        for _ in range(baseline_rps * 10):  # 10 seconds
            start_time = time.time()
            await instance.process({{"phase": "recovery"}})
            response_time = time.time() - start_time
            results.append({{"phase": "recovery", "response_time": response_time}})
            await asyncio.sleep(1 / baseline_rps)
        
        # Analyze spike test results
        baseline_times = [r["response_time"] for r in results if r["phase"] == "baseline"]
        spike_times = [r["response_time"] for r in results if r["phase"] == "spike"]
        recovery_times = [r["response_time"] for r in results if r["phase"] == "recovery"]
        
        baseline_avg = statistics.mean(baseline_times) if baseline_times else 0
        spike_avg = statistics.mean(spike_times) if spike_times else 0
        recovery_avg = statistics.mean(recovery_times) if recovery_times else 0
        
        # Spike test assertions
        assert recovery_avg < baseline_avg * 2  # Recovery should be reasonable
        assert spike_avg < 10.0  # Even under spike, response time should be manageable
        
        print(f"Baseline average: {{baseline_avg:.3f}}s")
        print(f"Spike average: {{spike_avg:.3f}}s")
        print(f"Recovery average: {{recovery_avg:.3f}}s")
    
    @pytest.mark.slow
    def test_resource_exhaustion(self):
        """Test behavior under resource exhaustion"""
        instance = {class_name}()
        
        # Monitor resource usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Generate increasing load until resource limits
        request_size = 1024  # Start with 1KB requests
        max_memory_increase = 500 * 1024 * 1024  # 500MB limit
        
        request_count = 0
        while True:
            current_memory = process.memory_info().rss
            memory_increase = current_memory - initial_memory
            
            if memory_increase > max_memory_increase:
                break
            
            try:
                # Create increasingly large requests
                large_data = "x" * request_size
                instance.process({{"large_data": large_data, "count": request_count}})
                
                request_count += 1
                request_size = min(request_size * 2, 1024 * 1024)  # Cap at 1MB
                
                if request_count > 10000:  # Safety break
                    break
                    
            except Exception as e:
                print(f"Resource exhaustion at request {{request_count}}: {{e}}")
                break
        
        # Resource exhaustion assertions
        assert request_count > 100  # Should handle at least 100 requests
        print(f"Handled {{request_count}} requests before resource exhaustion")
        print(f"Memory increase: {{memory_increase / 1024 / 1024:.2f}} MB")
'''
    
    def _create_fixtures_file(self, config: TestConfig) -> str:
        """Create test fixtures file content"""
        target_name = Path(config.target_file).stem
        
        return f'''"""
Test fixtures for {target_name}

Reusable test data and setup functions
"""

import pytest
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Any

{'from moto import mock_dynamodb' if config.has_database else ''}
{'import boto3' if config.has_database else ''}


# Test data fixtures
@pytest.fixture
def sample_test_data():
    """Sample test data for testing"""
    return {{
        "id": "test_123",
        "name": "Test Entity",
        "description": "Test description",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "data": {{
            "nested": "value",
            "number": 42,
            "boolean": True
        }}
    }}

@pytest.fixture
def sample_test_list():
    """List of sample test data"""
    return [
        {{"id": f"test_{{i}}", "name": f"Test {{i}}", "value": i}}
        for i in range(10)
    ]

@pytest.fixture
def invalid_test_data():
    """Invalid test data for error testing"""
    return [
        None,
        "",
        {{}},
        [],
        {{"missing": "required_fields"}},
        {{"invalid": "format"}},
    ]

# Environment fixtures
@pytest.fixture
def test_environment():
    """Test environment configuration"""
    return {{
        "DEBUG": True,
        "TESTING": True,
        "DATABASE_URL": "sqlite:///:memory:",
        "CACHE_ENABLED": False
    }}

# Time fixtures
@pytest.fixture
def fixed_datetime():
    """Fixed datetime for consistent testing"""
    return datetime(2023, 1, 1, 12, 0, 0)

@pytest.fixture
def time_range():
    """Time range for testing"""
    start = datetime(2023, 1, 1)
    end = datetime(2023, 12, 31)
    return start, end

# Mock fixtures
@pytest.fixture
def mock_response():
    """Mock HTTP response"""
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
        
        def json(self):
            return self.json_data
    
    return MockResponse

{'# Database fixtures' if config.has_database else ''}
{'@pytest.fixture' if config.has_database else ''}
{'@mock_dynamodb' if config.has_database else ''}
{'def test_dynamodb_table():' if config.has_database else ''}
{'    """Create test DynamoDB table"""' if config.has_database else ''}
{'    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")' if config.has_database else ''}
{'    ' if config.has_database else ''}
{'    table = dynamodb.create_table(' if config.has_database else ''}
{'        TableName="test-table",' if config.has_database else ''}
{'        KeySchema=[' if config.has_database else ''}
{'            {{"AttributeName": "PK", "KeyType": "HASH"}},' if config.has_database else ''}
{'            {{"AttributeName": "SK", "KeyType": "RANGE"}}' if config.has_database else ''}
{'        ],' if config.has_database else ''}
{'        AttributeDefinitions=[' if config.has_database else ''}
{'            {{"AttributeName": "PK", "AttributeType": "S"}},' if config.has_database else ''}
{'            {{"AttributeName": "SK", "AttributeType": "S"}}' if config.has_database else ''}
{'        ],' if config.has_database else ''}
{'        ProvisionedThroughput={{' if config.has_database else ''}
{'            "ReadCapacityUnits": 5,' if config.has_database else ''}
{'            "WriteCapacityUnits": 5' if config.has_database else ''}
{'        }}' if config.has_database else ''}
{'    )' if config.has_database else ''}
{'    ' if config.has_database else ''}
{'    table.wait_until_exists()' if config.has_database else ''}
{'    return table' if config.has_database else ''}

# File fixtures
@pytest.fixture
def temp_file(tmp_path):
    """Temporary file for testing"""
    file_path = tmp_path / "test_file.json"
    test_data = {{"test": "data", "number": 42}}
    
    with open(file_path, "w") as f:
        json.dump(test_data, f)
    
    return file_path

@pytest.fixture
def temp_directory(tmp_path):
    """Temporary directory with test files"""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()
    
    # Create test files
    for i in range(5):
        file_path = test_dir / f"test_file_{{i}}.json"
        with open(file_path, "w") as f:
            json.dump({{"id": i, "data": f"test_{{i}}"}}, f)
    
    return test_dir

# Performance fixtures
@pytest.fixture
def performance_monitor():
    """Performance monitoring context manager"""
    import time
    import psutil
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.start_memory = None
            self.end_memory = None
            self.process = psutil.Process()
        
        def __enter__(self):
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.end_time = time.time()
            self.end_memory = self.process.memory_info().rss
        
        @property
        def duration(self):
            return self.end_time - self.start_time if self.end_time else None
        
        @property
        def memory_delta(self):
            return self.end_memory - self.start_memory if self.end_memory else None
    
    return PerformanceMonitor

# Configuration fixtures
@pytest.fixture
def test_config():
    """Test configuration"""
    return {{
        "api_timeout": 30,
        "retry_attempts": 3,
        "batch_size": 100,
        "cache_ttl": 300,
        "debug": True
    }}
'''
    
    def _create_factory_file(self, config: TestConfig) -> str:
        """Create test factory file content"""
        target_name = Path(config.target_file).stem
        class_name = config.class_name or f"{target_name.title().replace('_', '')}"
        
        return f'''"""
Test factory for {target_name}

Factory methods for creating test data and objects
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
import string
from faker import Faker

fake = Faker()


class {class_name}TestFactory:
    """Factory for creating {class_name} test data"""
    
    @staticmethod
    def create_valid_data(**overrides) -> Dict[str, Any]:
        """Create valid test data"""
        data = {{
            "id": fake.uuid4(),
            "name": fake.word(),
            "description": fake.text(max_nb_chars=200),
            "status": random.choice(["active", "inactive", "pending"]),
            "created_at": fake.date_time_this_year().isoformat(),
            "updated_at": fake.date_time_this_month().isoformat(),
            "metadata": {{
                "source": "test",
                "version": "1.0.0",
                "tags": fake.words(nb=3)
            }}
        }}
        
        data.update(overrides)
        return data
    
    @staticmethod
    def create_invalid_data() -> List[Dict[str, Any]]:
        """Create various invalid test data scenarios"""
        return [
            {{}},  # Empty dict
            {{"id": None}},  # None values
            {{"id": ""}},  # Empty strings
            {{"id": "invalid", "name": None}},  # Mixed invalid
            {{"id": 12345}},  # Wrong types
            {{"invalid_field": "value"}},  # Unknown fields
        ]
    
    @staticmethod
    def create_batch(count: int, **overrides) -> List[Dict[str, Any]]:
        """Create a batch of test data"""
        return [
            {class_name}TestFactory.create_valid_data(**overrides)
            for _ in range(count)
        ]
    
    @staticmethod
    def create_large_data(size_mb: int = 1) -> Dict[str, Any]:
        """Create large test data for performance testing"""
        # Create roughly size_mb megabytes of data
        chars_per_mb = 1024 * 1024
        large_string = ''.join(
            random.choices(string.ascii_letters + string.digits, 
                         k=size_mb * chars_per_mb)
        )
        
        return {{
            "id": fake.uuid4(),
            "large_data": large_string,
            "metadata": {{
                "size_mb": size_mb,
                "created": datetime.now().isoformat()
            }}
        }}
    
    @staticmethod
    def create_time_series_data(
        count: int = 100,
        start_date: Optional[datetime] = None,
        interval_minutes: int = 15
    ) -> List[Dict[str, Any]]:
        """Create time series test data"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        
        data = []
        current_time = start_date
        
        for i in range(count):
            data.append({{
                "id": f"ts_{{i}}",
                "timestamp": current_time.isoformat(),
                "value": random.uniform(0, 100),
                "category": random.choice(["A", "B", "C"]),
                "tags": fake.words(nb=2)
            }})
            current_time += timedelta(minutes=interval_minutes)
        
        return data
    
    @staticmethod
    def create_nested_data(depth: int = 3) -> Dict[str, Any]:
        """Create deeply nested test data"""
        def create_nested_dict(current_depth: int) -> Dict[str, Any]:
            if current_depth <= 0:
                return {{"value": fake.word(), "number": fake.random_int()}}
            
            return {{
                "level": current_depth,
                "data": fake.text(max_nb_chars=50),
                "nested": create_nested_dict(current_depth - 1),
                "list": [
                    create_nested_dict(current_depth - 1)
                    for _ in range(2)
                ]
            }}
        
        return {{
            "id": fake.uuid4(),
            "root": create_nested_dict(depth),
            "metadata": {{
                "depth": depth,
                "created": datetime.now().isoformat()
            }}
        }}
    
    @staticmethod
    def create_edge_case_data() -> List[Dict[str, Any]]:
        """Create edge case test data"""
        return [
            # Unicode and special characters
            {{
                "id": "unicode_test",
                "name": "测试数据 🚀 émojis",
                "description": "Special chars: !@#$%^&*()_+-=[]{{}}|;':\",./<>?"
            }},
            
            # Very long strings
            {{
                "id": "long_string_test",
                "name": "a" * 1000,
                "description": "Very long description " * 100
            }},
            
            # Extreme numbers
            {{
                "id": "number_test",
                "small_number": 0.0000001,
                "large_number": 999999999999999,
                "negative": -999999999
            }},
            
            # Date edge cases
            {{
                "id": "date_test",
                "past_date": "1900-01-01T00:00:00Z",
                "future_date": "2100-12-31T23:59:59Z",
                "leap_year": "2024-02-29T12:00:00Z"
            }},
        ]
    
    @staticmethod
    def create_performance_test_data(
        operation_type: str = "read",
        complexity: str = "simple"
    ) -> Dict[str, Any]:
        """Create data optimized for performance testing"""
        base_data = {{
            "id": fake.uuid4(),
            "operation": operation_type,
            "complexity": complexity,
            "timestamp": datetime.now().isoformat()
        }}
        
        if complexity == "simple":
            base_data.update({{
                "name": fake.word(),
                "value": fake.random_int()
            }})
        elif complexity == "medium":
            base_data.update({{
                "data": fake.json(data_columns={{'name': 'word', 'value': 'random_int'}}, num_rows=10),
                "metadata": fake.pydict(nb_elements=20)
            }})
        elif complexity == "complex":
            base_data.update({{
                "large_list": [fake.pydict(nb_elements=10) for _ in range(100)],
                "nested_data": {{f"level_{{i}}": fake.pydict(nb_elements=50) for i in range(10)}}
            }})
        
        return base_data


# Convenience functions
def quick_valid_data(**overrides) -> Dict[str, Any]:
    """Quick function to create valid test data"""
    return {class_name}TestFactory.create_valid_data(**overrides)

def quick_batch(count: int) -> List[Dict[str, Any]]:
    """Quick function to create batch test data"""
    return {class_name}TestFactory.create_batch(count)

def quick_invalid_data() -> List[Dict[str, Any]]:
    """Quick function to create invalid test data"""
    return {class_name}TestFactory.create_invalid_data()
'''
    
    def create_files(self, files: Dict[str, str]) -> None:
        """Create the generated files"""
        for file_path, content in files.items():
            full_path = self.project_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            print(f"✅ Created: {file_path}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Generate comprehensive test suite")
    parser.add_argument("target", help="Target file to test (e.g., src/services/user_service.py)")
    parser.add_argument("--type", choices=["unit", "integration", "performance", "load", "all"], 
                       default="all", help="Type of tests to generate")
    parser.add_argument("--class", dest="class_name", help="Class name being tested")
    parser.add_argument("--functions", nargs="*", help="Specific functions to test")
    parser.add_argument("--async", action="store_true", help="Include async test patterns")
    parser.add_argument("--database", action="store_true", help="Include database testing")
    parser.add_argument("--api", action="store_true", help="Include API testing")
    parser.add_argument("--cache", action="store_true", help="Include cache testing")
    
    args = parser.parse_args()
    
    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir
    while project_root.parent != project_root:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent
    
    # Create test configuration
    config = TestConfig(
        target_file=args.target,
        test_type=args.type,
        class_name=args.class_name,
        function_names=args.functions or [],
        has_async=getattr(args, 'async', True),
        has_database=args.database,
        has_api=args.api,
        has_cache=args.cache
    )
    
    # Generate tests
    generator = TestGenerator(project_root)
    files = generator.generate_tests(config)
    generator.create_files(files)
    
    print(f"\\n🚀 Generated {args.type} tests for {args.target}!")
    print(f"📁 Files created: {len(files)}")
    print("\\n📝 Next steps:")
    print("1. Review the generated tests and customize as needed")
    print("2. Run the tests: pytest tests/")
    print("3. Add any specific test cases for your business logic")
    print("4. Set up CI/CD to run tests automatically")


if __name__ == "__main__":
    main()
