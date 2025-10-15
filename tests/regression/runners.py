"""
Parallel Test Runner
High-performance parallel test execution with smart scheduling
"""

import asyncio
import concurrent.futures
import subprocess
import threading
import time
import queue
import json
from typing import List, Dict, Optional, Callable, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

from .config import RegressionTestConfig, TestSuiteConfig
from .selectors import TestFile, TestSelection


class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"
    FLAKY = "flaky"


@dataclass
class TestResult:
    """Result of a single test execution"""
    test_file: str
    status: TestStatus
    duration: float
    output: str = ""
    error: str = ""
    worker_id: Optional[str] = None
    retry_count: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class TestBatch:
    """A batch of tests to run together"""
    tests: List[TestFile]
    suite_config: TestSuiteConfig
    worker_id: str
    estimated_duration: float


@dataclass
class ExecutionSummary:
    """Summary of test execution"""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    flaky: int
    total_duration: float
    start_time: float
    end_time: float
    worker_count: int
    results: List[TestResult]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_tests == 0:
            return 1.0
        return self.passed / self.total_tests
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        return 1.0 - self.success_rate


class TestWorker:
    """Individual test worker for parallel execution"""
    
    def __init__(self, worker_id: str, config: RegressionTestConfig, result_queue: queue.Queue):
        self.worker_id = worker_id
        self.config = config
        self.result_queue = result_queue
        self.current_test = None
        self._shutdown = threading.Event()
    
    def run_batch(self, batch: TestBatch) -> List[TestResult]:
        """Run a batch of tests"""
        results = []
        
        for test_file in batch.tests:
            if self._shutdown.is_set():
                break
            
            self.current_test = test_file
            result = self._run_single_test(test_file, batch.suite_config)
            results.append(result)
            self.result_queue.put(result)
        
        return results
    
    def _run_single_test(self, test_file: TestFile, suite_config: TestSuiteConfig) -> TestResult:
        """Run a single test file"""
        start_time = time.time()
        
        # Build pytest command
        cmd = self._build_pytest_command(test_file, suite_config)
        
        try:
            # Set up environment
            env = dict(os.environ)
            env.update(suite_config.environment_vars)
            
            # Run test with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=suite_config.timeout,
                cwd=self.config.project_root,
                env=env
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Determine status
            if result.returncode == 0:
                status = TestStatus.PASSED
            elif result.returncode == 5:  # pytest exit code for no tests collected
                status = TestStatus.SKIPPED
            else:
                status = TestStatus.FAILED
            
            return TestResult(
                test_file=str(test_file.path),
                status=status,
                duration=duration,
                output=result.stdout,
                error=result.stderr,
                worker_id=self.worker_id,
                start_time=start_time,
                end_time=end_time
            )
            
        except subprocess.TimeoutExpired:
            end_time = time.time()
            return TestResult(
                test_file=str(test_file.path),
                status=TestStatus.TIMEOUT,
                duration=end_time - start_time,
                error=f"Test timed out after {suite_config.timeout} seconds",
                worker_id=self.worker_id,
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            end_time = time.time()
            return TestResult(
                test_file=str(test_file.path),
                status=TestStatus.ERROR,
                duration=end_time - start_time,
                error=str(e),
                worker_id=self.worker_id,
                start_time=start_time,
                end_time=end_time
            )
    
    def _build_pytest_command(self, test_file: TestFile, suite_config: TestSuiteConfig) -> List[str]:
        """Build pytest command for test execution"""
        cmd = [self.config.pytest_executable]
        
        # Add test file
        cmd.append(str(test_file.path))
        
        # Add markers
        if suite_config.markers:
            cmd.extend(["-m", " and ".join(suite_config.markers)])
        
        # Add output options
        cmd.extend([
            "-v",  # verbose
            "--tb=short",  # short traceback
            "--no-header",  # no header
            "-q"  # quiet
        ])
        
        # Add JUnit XML output for CI
        if self.config.ci_mode:
            junit_file = f"junit-{self.worker_id}-{int(time.time())}.xml"
            cmd.extend(["--junit-xml", str(self.config.reporting.output_dir / junit_file)])
        
        return cmd
    
    def shutdown(self):
        """Signal worker to shutdown"""
        self._shutdown.set()


class ParallelTestRunner:
    """High-performance parallel test runner"""
    
    def __init__(self, config: RegressionTestConfig):
        self.config = config
        self.workers = []
        self.result_queue = queue.Queue()
        self.results = []
        self._shutdown = threading.Event()
        
    def run_tests(self, test_selection: TestSelection, 
                  progress_callback: Optional[Callable[[TestResult], None]] = None) -> ExecutionSummary:
        """Run selected tests in parallel"""
        
        if not test_selection.selected_tests:
            return ExecutionSummary(
                total_tests=0, passed=0, failed=0, skipped=0, errors=0, flaky=0,
                total_duration=0.0, start_time=time.time(), end_time=time.time(),
                worker_count=0, results=[]
            )
        
        start_time = time.time()
        
        # Create test batches
        batches = self._create_test_batches(test_selection.selected_tests)
        
        # Start result collector thread
        collector_thread = threading.Thread(
            target=self._collect_results,
            args=(progress_callback,),
            daemon=True
        )
        collector_thread.start()
        
        # Execute batches in parallel
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.parallel.max_workers
        ) as executor:
            
            # Create workers
            futures = []
            for i, batch in enumerate(batches):
                worker = TestWorker(f"worker-{i}", self.config, self.result_queue)
                self.workers.append(worker)
                
                future = executor.submit(worker.run_batch, batch)
                futures.append(future)
            
            # Wait for all workers to complete
            concurrent.futures.wait(futures, timeout=self.config.parallel.worker_timeout)
        
        # Signal completion and wait for collector
        self.result_queue.put(None)  # Sentinel value
        collector_thread.join(timeout=10)
        
        end_time = time.time()
        
        # Compile execution summary
        return self._compile_summary(start_time, end_time, len(self.workers))
    
    def _create_test_batches(self, test_files: List[TestFile]) -> List[TestBatch]:
        """Create balanced test batches for parallel execution"""
        
        if not test_files:
            return []
        
        # Group tests by suite configuration
        suite_groups = defaultdict(list)
        for test_file in test_files:
            # Find matching suite config
            suite_config = self._find_suite_config(test_file)
            suite_key = suite_config.name if suite_config else "default"
            suite_groups[suite_key].append((test_file, suite_config))
        
        # Create batches
        batches = []
        worker_count = min(self.config.parallel.max_workers, len(test_files))
        
        for suite_key, tests_and_configs in suite_groups.items():
            # Sort by estimated duration (longest first for better load balancing)
            tests_and_configs.sort(key=lambda x: x[0].avg_duration, reverse=True)
            
            # Distribute tests across workers
            batch_size = max(1, len(tests_and_configs) // worker_count)
            
            for i in range(0, len(tests_and_configs), batch_size):
                batch_tests = [tc[0] for tc in tests_and_configs[i:i + batch_size]]
                suite_config = tests_and_configs[i][1] if tests_and_configs else None
                
                if batch_tests and suite_config:
                    estimated_duration = sum(t.avg_duration for t in batch_tests)
                    
                    batch = TestBatch(
                        tests=batch_tests,
                        suite_config=suite_config,
                        worker_id=f"batch-{len(batches)}",
                        estimated_duration=estimated_duration
                    )
                    batches.append(batch)
        
        return batches
    
    def _find_suite_config(self, test_file: TestFile) -> Optional[TestSuiteConfig]:
        """Find matching suite configuration for test file"""
        
        for suite_config in self.config.test_suites:
            # Check if test file matches suite patterns
            if self._test_matches_suite(test_file, suite_config):
                return suite_config
        
        # Return default suite config
        return TestSuiteConfig(
            name="default",
            category=test_file.category,
            priority=test_file.priority,
            path=test_file.path.parent,
            timeout=300
        )
    
    def _test_matches_suite(self, test_file: TestFile, suite_config: TestSuiteConfig) -> bool:
        """Check if test file matches suite configuration"""
        
        # Check category match
        if test_file.category != suite_config.category:
            return False
        
        # Check path match
        if not str(test_file.path).startswith(str(suite_config.path)):
            return False
        
        # Check pattern match
        if suite_config.patterns:
            test_name = test_file.path.name
            for pattern in suite_config.patterns:
                if pattern in test_name or fnmatch.fnmatch(test_name, pattern):
                    return True
            return False
        
        return True
    
    def _collect_results(self, progress_callback: Optional[Callable[[TestResult], None]]):
        """Collect results from worker queue"""
        
        while True:
            try:
                result = self.result_queue.get(timeout=1.0)
                
                if result is None:  # Sentinel value
                    break
                
                self.results.append(result)
                
                if progress_callback:
                    progress_callback(result)
                    
            except queue.Empty:
                if self._shutdown.is_set():
                    break
                continue
    
    def _compile_summary(self, start_time: float, end_time: float, worker_count: int) -> ExecutionSummary:
        """Compile execution summary from results"""
        
        status_counts = defaultdict(int)
        for result in self.results:
            status_counts[result.status] += 1
        
        return ExecutionSummary(
            total_tests=len(self.results),
            passed=status_counts[TestStatus.PASSED],
            failed=status_counts[TestStatus.FAILED],
            skipped=status_counts[TestStatus.SKIPPED],
            errors=status_counts[TestStatus.ERROR],
            flaky=status_counts[TestStatus.FLAKY],
            total_duration=end_time - start_time,
            start_time=start_time,
            end_time=end_time,
            worker_count=worker_count,
            results=self.results.copy()
        )
    
    def run_flaky_detection(self, test_files: List[TestFile], runs_per_test: int = 10) -> Dict[str, float]:
        """Run flaky test detection by running tests multiple times"""
        
        flaky_results = {}
        
        for test_file in test_files:
            results = []
            
            for run in range(runs_per_test):
                # Create a simple test selection for this file
                selection = TestSelection(
                    selected_tests=[test_file],
                    reason=f"Flaky detection run {run + 1}",
                    confidence=1.0,
                    estimated_duration=test_file.avg_duration
                )
                
                summary = self.run_tests(selection)
                
                if summary.results:
                    result = summary.results[0]
                    results.append(result.status == TestStatus.PASSED)
            
            # Calculate success rate
            if results:
                success_rate = sum(results) / len(results)
                flaky_results[str(test_file.path)] = success_rate
        
        return flaky_results
    
    def shutdown(self):
        """Shutdown test runner"""
        self._shutdown.set()
        
        for worker in self.workers:
            worker.shutdown()


import os
import fnmatch
