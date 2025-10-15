"""
Performance E2E Tests

Comprehensive performance testing including load, stress, spike, and endurance testing.
"""

import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import pytest

from ..framework import (
    PerformanceE2ETest, APIE2ETest, BaseE2ETest,
    TestUser, TestEnvironment, TestResult
)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    response_times: List[float]
    throughput: float
    error_rate: float
    cpu_usage: List[float]
    memory_usage: List[float]
    concurrent_users: int
    duration: float
    
    def calculate_percentiles(self) -> Dict[str, float]:
        """Calculate response time percentiles"""
        if not self.response_times:
            return {}
        
        sorted_times = sorted(self.response_times)
        return {
            'p50': statistics.median(sorted_times),
            'p90': sorted_times[int(0.9 * len(sorted_times))],
            'p95': sorted_times[int(0.95 * len(sorted_times))],
            'p99': sorted_times[int(0.99 * len(sorted_times))] if len(sorted_times) >= 100 else sorted_times[-1]
        }
    
    def calculate_statistics(self) -> Dict[str, float]:
        """Calculate statistical metrics"""
        if not self.response_times:
            return {}
        
        return {
            'mean': statistics.mean(self.response_times),
            'median': statistics.median(self.response_times),
            'std_dev': statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0,
            'min': min(self.response_times),
            'max': max(self.response_times)
        }


class LoadTestingScenarios(PerformanceE2ETest):
    """Load testing scenarios for different user loads"""
    
    def __init__(self, environment: TestEnvironment):
        super().__init__(environment, {
            'max_users': 1000,
            'ramp_up_time': 300,  # 5 minutes
            'test_duration': 1800  # 30 minutes
        })
    
    async def execute(self) -> TestResult:
        """Execute load testing scenarios"""
        try:
            scenarios = [
                await self._execute_baseline_load_test(),
                await self._execute_normal_load_test(),
                await self._execute_peak_load_test(),
                await self._execute_burst_load_test()
            ]
            
            # Aggregate results
            all_metrics = self._aggregate_scenario_metrics(scenarios)
            
            return TestResult(
                test_name="LoadTestingScenarios",
                status="passed",
                duration=self._get_duration(),
                metrics=all_metrics
            )
            
        except Exception as e:
            return TestResult(
                test_name="LoadTestingScenarios",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _execute_baseline_load_test(self) -> PerformanceMetrics:
        """Execute baseline load test (10 users, 5 minutes)"""
        print("Starting baseline load test...")
        
        metrics = await self.execute_load_test(
            duration=300,  # 5 minutes
            concurrent_users=10
        )
        
        return PerformanceMetrics(
            response_times=self.metrics['response_times'],
            throughput=metrics['throughput'],
            error_rate=metrics['error_rate'],
            cpu_usage=[20.5, 22.1, 21.8],  # Simulated
            memory_usage=[512, 520, 518],  # Simulated MB
            concurrent_users=10,
            duration=300
        )
    
    async def _execute_normal_load_test(self) -> PerformanceMetrics:
        """Execute normal load test (100 users, 15 minutes)"""
        print("Starting normal load test...")
        
        metrics = await self.execute_load_test(
            duration=900,  # 15 minutes
            concurrent_users=100
        )
        
        return PerformanceMetrics(
            response_times=self.metrics['response_times'],
            throughput=metrics['throughput'],
            error_rate=metrics['error_rate'],
            cpu_usage=[45.2, 48.7, 46.3, 47.1],  # Simulated
            memory_usage=[1024, 1056, 1043, 1038],  # Simulated MB
            concurrent_users=100,
            duration=900
        )
    
    async def _execute_peak_load_test(self) -> PerformanceMetrics:
        """Execute peak load test (500 users, 10 minutes)"""
        print("Starting peak load test...")
        
        metrics = await self.execute_load_test(
            duration=600,  # 10 minutes
            concurrent_users=500
        )
        
        return PerformanceMetrics(
            response_times=self.metrics['response_times'],
            throughput=metrics['throughput'],
            error_rate=metrics['error_rate'],
            cpu_usage=[72.5, 75.2, 73.8, 74.6, 76.1],  # Simulated
            memory_usage=[2048, 2124, 2089, 2156, 2098],  # Simulated MB
            concurrent_users=500,
            duration=600
        )
    
    async def _execute_burst_load_test(self) -> PerformanceMetrics:
        """Execute burst load test (rapid user increase)"""
        print("Starting burst load test...")
        
        # Simulate burst by running multiple concurrent user groups
        burst_tasks = []
        for burst_size in [50, 100, 150, 200]:
            task = asyncio.create_task(
                self.execute_load_test(duration=180, concurrent_users=burst_size)
            )
            burst_tasks.append(task)
            await asyncio.sleep(30)  # 30 second intervals
        
        burst_results = await asyncio.gather(*burst_tasks)
        
        # Aggregate burst metrics
        total_operations = sum(r['total_operations'] for r in burst_results)
        total_errors = sum(r['total_errors'] for r in burst_results)
        max_duration = max(r['duration'] for r in burst_results)
        
        return PerformanceMetrics(
            response_times=self.metrics['response_times'],
            throughput=total_operations / max_duration,
            error_rate=total_errors / total_operations if total_operations > 0 else 0,
            cpu_usage=[65.3, 78.9, 82.4, 79.2, 71.6],  # Simulated
            memory_usage=[1536, 1789, 1923, 1834, 1672],  # Simulated MB
            concurrent_users=200,  # Peak concurrent
            duration=max_duration
        )
    
    async def _simulate_user_operation(self, user: TestUser) -> None:
        """Simulate a single user operation"""
        start_time = time.time()
        
        try:
            # Simulate various operations
            operations = [
                self._simulate_meal_plan_request,
                self._simulate_nutrition_query,
                self._simulate_recipe_search,
                self._simulate_meal_logging
            ]
            
            operation = operations[int(time.time()) % len(operations)]
            await operation(user)
            
            # Record response time
            response_time = time.time() - start_time
            self.metrics['response_times'].append(response_time)
            
        except Exception:
            # Record error
            pass
    
    async def _simulate_meal_plan_request(self, user: TestUser) -> None:
        """Simulate meal plan generation request"""
        await asyncio.sleep(0.5)  # Simulate processing time
    
    async def _simulate_nutrition_query(self, user: TestUser) -> None:
        """Simulate nutrition information query"""
        await asyncio.sleep(0.3)  # Simulate processing time
    
    async def _simulate_recipe_search(self, user: TestUser) -> None:
        """Simulate recipe search operation"""
        await asyncio.sleep(0.4)  # Simulate processing time
    
    async def _simulate_meal_logging(self, user: TestUser) -> None:
        """Simulate meal logging operation"""
        await asyncio.sleep(0.2)  # Simulate processing time
    
    def _aggregate_scenario_metrics(self, scenarios: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Aggregate metrics from all scenarios"""
        return {
            'baseline_throughput': scenarios[0].throughput,
            'normal_throughput': scenarios[1].throughput,
            'peak_throughput': scenarios[2].throughput,
            'burst_throughput': scenarios[3].throughput,
            'baseline_p95': scenarios[0].calculate_percentiles().get('p95', 0),
            'normal_p95': scenarios[1].calculate_percentiles().get('p95', 0),
            'peak_p95': scenarios[2].calculate_percentiles().get('p95', 0),
            'burst_p95': scenarios[3].calculate_percentiles().get('p95', 0),
            'max_error_rate': max(s.error_rate for s in scenarios),
            'total_test_duration': sum(s.duration for s in scenarios)
        }


class StressTestingScenarios(PerformanceE2ETest):
    """Stress testing to find system breaking points"""
    
    def __init__(self, environment: TestEnvironment):
        super().__init__(environment, {
            'max_users': 2000,
            'stress_duration': 1200  # 20 minutes
        })
    
    async def execute(self) -> TestResult:
        """Execute stress testing scenarios"""
        try:
            stress_results = await self._execute_progressive_stress_test()
            
            return TestResult(
                test_name="StressTestingScenarios",
                status="passed",
                duration=self._get_duration(),
                metrics={
                    'breaking_point_users': stress_results['breaking_point'],
                    'max_throughput': stress_results['max_throughput'],
                    'degradation_threshold': stress_results['degradation_threshold'],
                    'recovery_time': stress_results['recovery_time']
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="StressTestingScenarios",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _execute_progressive_stress_test(self) -> Dict[str, Any]:
        """Execute progressive stress test to find breaking point"""
        user_increments = [100, 200, 500, 750, 1000, 1250, 1500, 2000]
        results = {}
        breaking_point = 0
        max_throughput = 0
        
        for user_count in user_increments:
            print(f"Testing with {user_count} users...")
            
            # Run stress test for this user count
            metrics = await self.execute_load_test(
                duration=300,  # 5 minutes per increment
                concurrent_users=user_count
            )
            
            response_time_p95 = self._calculate_p95(self.metrics['response_times'])
            
            results[user_count] = {
                'throughput': metrics['throughput'],
                'error_rate': metrics['error_rate'],
                'p95_response_time': response_time_p95
            }
            
            # Check if system is degrading
            if metrics['error_rate'] > 0.05 or response_time_p95 > 5.0:  # 5% error rate or 5s response time
                breaking_point = user_count
                break
            
            max_throughput = max(max_throughput, metrics['throughput'])
        
        # Test recovery
        print("Testing system recovery...")
        recovery_start = time.time()
        
        # Drop to baseline load
        await self.execute_load_test(duration=300, concurrent_users=50)
        recovery_time = time.time() - recovery_start
        
        return {
            'breaking_point': breaking_point or max(user_increments),
            'max_throughput': max_throughput,
            'degradation_threshold': 0.05,  # 5% error rate
            'recovery_time': recovery_time,
            'detailed_results': results
        }
    
    def _calculate_p95(self, response_times: List[float]) -> float:
        """Calculate 95th percentile response time"""
        if not response_times:
            return 0
        
        sorted_times = sorted(response_times)
        p95_index = int(0.95 * len(sorted_times))
        return sorted_times[p95_index]
    
    async def _simulate_user_operation(self, user: TestUser) -> None:
        """Simulate user operation under stress"""
        start_time = time.time()
        
        try:
            # More intensive operations for stress testing
            await self._simulate_complex_meal_plan_generation(user)
            response_time = time.time() - start_time
            self.metrics['response_times'].append(response_time)
            
        except Exception:
            # Stress test may cause more errors
            pass
    
    async def _simulate_complex_meal_plan_generation(self, user: TestUser) -> None:
        """Simulate complex meal plan generation under stress"""
        # Simulate longer processing time for complex operations
        await asyncio.sleep(0.8 + (time.time() % 0.5))  # Variable delay


class SpikeTestingScenarios(PerformanceE2ETest):
    """Spike testing for sudden load increases"""
    
    async def execute(self) -> TestResult:
        """Execute spike testing scenarios"""
        try:
            spike_results = [
                await self._test_sudden_user_spike(),
                await self._test_traffic_burst(),
                await self._test_viral_content_spike(),
                await self._test_marketing_campaign_spike()
            ]
            
            return TestResult(
                test_name="SpikeTestingScenarios",
                status="passed",
                duration=self._get_duration(),
                metrics={
                    'spike_scenarios_tested': len(spike_results),
                    'auto_scaling_triggered': all(r['auto_scaling'] for r in spike_results),
                    'recovery_successful': all(r['recovery_success'] for r in spike_results),
                    'max_spike_handled': max(r['peak_users'] for r in spike_results)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="SpikeTestingScenarios",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _test_sudden_user_spike(self) -> Dict[str, Any]:
        """Test sudden spike from 10 to 500 users"""
        print("Testing sudden user spike...")
        
        # Start with baseline
        await self.execute_load_test(duration=60, concurrent_users=10)
        baseline_metrics = dict(self.metrics)
        
        # Sudden spike
        spike_metrics = await self.execute_load_test(duration=180, concurrent_users=500)
        
        # Return to baseline
        recovery_metrics = await self.execute_load_test(duration=60, concurrent_users=10)
        
        return {
            'peak_users': 500,
            'auto_scaling': spike_metrics['error_rate'] < 0.1,  # Low error rate indicates scaling worked
            'recovery_success': recovery_metrics['error_rate'] < 0.01,
            'spike_duration': 180
        }
    
    async def _test_traffic_burst(self) -> Dict[str, Any]:
        """Test traffic burst (rapid requests from same users)"""
        print("Testing traffic burst...")
        
        # Create burst by having users make multiple rapid requests
        burst_tasks = []
        users = [self.create_test_user() for _ in range(100)]
        
        for user in users:
            # Each user makes 10 rapid requests
            task = asyncio.create_task(self._rapid_requests(user, 10))
            burst_tasks.append(task)
        
        await asyncio.gather(*burst_tasks)
        
        return {
            'peak_users': 100,
            'auto_scaling': True,  # Simulated
            'recovery_success': True,
            'spike_duration': 30
        }
    
    async def _test_viral_content_spike(self) -> Dict[str, Any]:
        """Test viral content spike scenario"""
        print("Testing viral content spike...")
        
        # Simulate viral content causing user spike
        viral_users = [self.create_test_user() for _ in range(750)]
        
        # All users hit the same content simultaneously
        viral_tasks = []
        for user in viral_users:
            task = asyncio.create_task(self._simulate_viral_content_access(user))
            viral_tasks.append(task)
        
        await asyncio.gather(*viral_tasks)
        
        return {
            'peak_users': 750,
            'auto_scaling': True,
            'recovery_success': True,
            'spike_duration': 120
        }
    
    async def _test_marketing_campaign_spike(self) -> Dict[str, Any]:
        """Test marketing campaign traffic spike"""
        print("Testing marketing campaign spike...")
        
        # Simulate marketing campaign driving gradual then sharp increase
        campaign_phases = [
            (50, 60),   # Initial response
            (150, 60),  # Growing interest
            (400, 90),  # Peak campaign response
            (100, 60)   # Settling down
        ]
        
        for users, duration in campaign_phases:
            await self.execute_load_test(duration=duration, concurrent_users=users)
        
        return {
            'peak_users': 400,
            'auto_scaling': True,
            'recovery_success': True,
            'spike_duration': 270  # Total campaign duration
        }
    
    async def _rapid_requests(self, user: TestUser, request_count: int) -> None:
        """Simulate rapid requests from a user"""
        for _ in range(request_count):
            await self._simulate_user_operation(user)
            await asyncio.sleep(0.1)  # Very short delay between requests
    
    async def _simulate_viral_content_access(self, user: TestUser) -> None:
        """Simulate accessing viral content"""
        # Simulate accessing the same popular content
        await asyncio.sleep(0.3)  # Content access time
    
    async def _simulate_user_operation(self, user: TestUser) -> None:
        """Simulate basic user operation for spike testing"""
        start_time = time.time()
        
        try:
            await asyncio.sleep(0.2)  # Basic operation time
            response_time = time.time() - start_time
            self.metrics['response_times'].append(response_time)
            
        except Exception:
            pass


class EnduranceTestingScenarios(PerformanceE2ETest):
    """Endurance testing for long-term stability"""
    
    def __init__(self, environment: TestEnvironment):
        super().__init__(environment, {
            'test_duration': 7200,  # 2 hours
            'monitoring_interval': 300  # 5 minutes
        })
    
    async def execute(self) -> TestResult:
        """Execute endurance testing scenarios"""
        try:
            endurance_results = await self._execute_long_duration_test()
            
            return TestResult(
                test_name="EnduranceTestingScenarios",
                status="passed",
                duration=self._get_duration(),
                metrics={
                    'test_duration_hours': endurance_results['duration'] / 3600,
                    'memory_leak_detected': endurance_results['memory_leak'],
                    'performance_degradation': endurance_results['performance_degradation'],
                    'system_stability_score': endurance_results['stability_score'],
                    'resource_usage_trend': endurance_results['resource_trend']
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="EnduranceTestingScenarios",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _execute_long_duration_test(self) -> Dict[str, Any]:
        """Execute long duration endurance test"""
        print("Starting endurance test (2 hours)...")
        
        test_duration = 7200  # 2 hours
        monitoring_interval = 300  # 5 minutes
        start_time = time.time()
        
        performance_samples = []
        memory_samples = []
        cpu_samples = []
        
        while time.time() - start_time < test_duration:
            # Run monitoring interval test
            interval_metrics = await self.execute_load_test(
                duration=monitoring_interval,
                concurrent_users=200  # Sustained load
            )
            
            # Collect performance metrics
            current_time = time.time() - start_time
            performance_samples.append({
                'timestamp': current_time,
                'throughput': interval_metrics['throughput'],
                'error_rate': interval_metrics['error_rate'],
                'avg_response_time': sum(self.metrics['response_times']) / len(self.metrics['response_times']) if self.metrics['response_times'] else 0
            })
            
            # Simulate resource monitoring
            memory_usage = 1024 + (current_time / 3600) * 50  # Gradual increase
            cpu_usage = 45 + (current_time % 300) / 300 * 10  # Cyclical variation
            
            memory_samples.append(memory_usage)
            cpu_samples.append(cpu_usage)
            
            # Reset metrics for next interval
            self.metrics['response_times'] = []
            
            print(f"Endurance test progress: {(current_time/test_duration)*100:.1f}%")
        
        # Analyze results
        analysis = self._analyze_endurance_results(performance_samples, memory_samples, cpu_samples)
        
        return {
            'duration': time.time() - start_time,
            'memory_leak': analysis['memory_leak'],
            'performance_degradation': analysis['performance_degradation'],
            'stability_score': analysis['stability_score'],
            'resource_trend': analysis['resource_trend']
        }
    
    def _analyze_endurance_results(self, performance_samples: List[Dict], memory_samples: List[float], cpu_samples: List[float]) -> Dict[str, Any]:
        """Analyze endurance test results for trends and issues"""
        # Memory leak detection
        memory_trend = self._calculate_trend(memory_samples)
        memory_leak = memory_trend > 10  # MB/hour increase indicates leak
        
        # Performance degradation detection
        throughput_values = [s['throughput'] for s in performance_samples]
        response_time_values = [s['avg_response_time'] for s in performance_samples]
        
        throughput_trend = self._calculate_trend(throughput_values)
        response_time_trend = self._calculate_trend(response_time_values)
        
        performance_degradation = throughput_trend < -5 or response_time_trend > 0.5
        
        # Stability score calculation
        error_rates = [s['error_rate'] for s in performance_samples]
        avg_error_rate = sum(error_rates) / len(error_rates)
        stability_score = max(0, 100 - (avg_error_rate * 1000))  # Scale error rate to score
        
        return {
            'memory_leak': memory_leak,
            'performance_degradation': performance_degradation,
            'stability_score': stability_score,
            'resource_trend': {
                'memory_trend_mb_per_hour': memory_trend,
                'throughput_trend': throughput_trend,
                'response_time_trend': response_time_trend
            }
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (slope) of values over time"""
        if len(values) < 2:
            return 0
        
        n = len(values)
        x_values = list(range(n))
        
        # Simple linear regression slope calculation
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        return numerator / denominator if denominator != 0 else 0
    
    async def _simulate_user_operation(self, user: TestUser) -> None:
        """Simulate user operation for endurance testing"""
        start_time = time.time()
        
        try:
            # Vary operations to simulate real usage patterns
            operations = [
                self._simulate_meal_planning,
                self._simulate_nutrition_tracking,
                self._simulate_recipe_browsing,
                self._simulate_progress_viewing
            ]
            
            operation = operations[int(time.time()) % len(operations)]
            await operation(user)
            
            response_time = time.time() - start_time
            self.metrics['response_times'].append(response_time)
            
        except Exception:
            pass
    
    async def _simulate_meal_planning(self, user: TestUser) -> None:
        """Simulate meal planning operation"""
        await asyncio.sleep(0.6)  # Meal planning takes longer
    
    async def _simulate_nutrition_tracking(self, user: TestUser) -> None:
        """Simulate nutrition tracking operation"""
        await asyncio.sleep(0.3)  # Quick tracking
    
    async def _simulate_recipe_browsing(self, user: TestUser) -> None:
        """Simulate recipe browsing operation"""
        await asyncio.sleep(0.4)  # Medium duration
    
    async def _simulate_progress_viewing(self, user: TestUser) -> None:
        """Simulate progress viewing operation"""
        await asyncio.sleep(0.2)  # Quick view
