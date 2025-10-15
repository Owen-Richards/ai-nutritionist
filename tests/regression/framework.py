"""
Regression Testing Framework
Main framework orchestrator for comprehensive regression testing
"""

import asyncio
import os
import sys
import time
import logging
from typing import Optional, List, Dict, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .config import RegressionTestConfig, TestTrigger, DEFAULT_CONFIG
from .selectors import TestSelector, TestSelection
from .runners import ParallelTestRunner, ExecutionSummary
from .reporters import RegressionReporter, RegressionReport


class FrameworkMode(Enum):
    """Regression testing framework modes"""
    PRE_COMMIT = "pre_commit"
    PULL_REQUEST = "pull_request"
    NIGHTLY = "nightly"
    RELEASE = "release"
    FLAKY_DETECTION = "flaky_detection"
    CUSTOM = "custom"


@dataclass
class FrameworkResult:
    """Result of regression testing framework execution"""
    mode: FrameworkMode
    selection: TestSelection
    summary: ExecutionSummary
    report: RegressionReport
    success: bool
    duration: float
    recommendations: List[str]


class RegressionTestFramework:
    """Main regression testing framework orchestrator"""
    
    def __init__(self, config: Optional[RegressionTestConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.selector = TestSelector(self.config.project_root)
        self.runner = ParallelTestRunner(self.config)
        self.reporter = RegressionReporter(self.config)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
    
    def _setup_logging(self):
        """Setup logging for the framework"""
        log_level = logging.DEBUG if not self.config.ci_mode else logging.INFO
        
        # Ensure output directory exists
        self.config.reporting.output_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.config.reporting.output_dir / "regression.log")
            ] if not self.config.ci_mode else [logging.StreamHandler(sys.stdout)]
        )
    
    def run_pre_commit_tests(self, max_duration: int = 300) -> FrameworkResult:
        """Run fast regression tests for pre-commit hooks"""
        self.logger.info("🚀 Running pre-commit regression tests")
        
        return self._run_framework(
            mode=FrameworkMode.PRE_COMMIT,
            selection_method=lambda: self.selector.select_tests_for_commit(max_duration),
            execution_id=f"pre_commit_{int(time.time())}"
        )
    
    def run_pull_request_tests(self, max_duration: int = 1800) -> FrameworkResult:
        """Run comprehensive tests for pull request validation"""
        self.logger.info("🔍 Running pull request regression tests")
        
        return self._run_framework(
            mode=FrameworkMode.PULL_REQUEST,
            selection_method=lambda: self.selector.select_tests_for_pr(max_duration),
            execution_id=f"pr_{int(time.time())}"
        )
    
    def run_nightly_tests(self) -> FrameworkResult:
        """Run full nightly regression suite"""
        self.logger.info("🌙 Running nightly regression tests")
        
        return self._run_framework(
            mode=FrameworkMode.NIGHTLY,
            selection_method=lambda: self.selector.select_tests_for_nightly(),
            execution_id=f"nightly_{int(time.time())}"
        )
    
    def run_release_tests(self) -> FrameworkResult:
        """Run comprehensive release validation tests"""
        self.logger.info("🚢 Running release regression tests")
        
        # For release, run all stable tests
        selection = TestSelection(
            selected_tests=self.selector._get_all_tests(),
            reason="Release validation - comprehensive testing",
            confidence=1.0,
            estimated_duration=sum(t.avg_duration for t in self.selector._get_all_tests())
        )
        
        return self._run_framework(
            mode=FrameworkMode.RELEASE,
            selection_method=lambda: selection,
            execution_id=f"release_{int(time.time())}"
        )
    
    def run_flaky_detection(self, runs_per_test: int = 10) -> FrameworkResult:
        """Run flaky test detection analysis"""
        self.logger.info("🔍 Running flaky test detection")
        
        start_time = time.time()
        
        # Get potentially flaky tests
        flaky_selection = self.selector.select_flaky_tests()
        
        if not flaky_selection.selected_tests:
            self.logger.info("No potentially flaky tests identified")
            
            # Create empty results
            empty_summary = ExecutionSummary(
                total_tests=0, passed=0, failed=0, skipped=0, errors=0, flaky=0,
                total_duration=0.0, start_time=start_time, end_time=time.time(),
                worker_count=0, results=[]
            )
            
            report = self.reporter.generate_report(empty_summary, "flaky_detection_empty")
            
            return FrameworkResult(
                mode=FrameworkMode.FLAKY_DETECTION,
                selection=flaky_selection,
                summary=empty_summary,
                report=report,
                success=True,
                duration=time.time() - start_time,
                recommendations=["No flaky tests detected - test suite is stable"]
            )
        
        # Run flaky detection
        self.logger.info(f"Analyzing {len(flaky_selection.selected_tests)} potentially flaky tests")
        flaky_results = self.runner.run_flaky_detection(flaky_selection.selected_tests, runs_per_test)
        
        # Generate report
        end_time = time.time()
        
        # Create summary for flaky detection
        flaky_summary = ExecutionSummary(
            total_tests=len(flaky_selection.selected_tests),
            passed=sum(1 for rate in flaky_results.values() if rate >= 0.9),
            failed=sum(1 for rate in flaky_results.values() if rate < 0.5),
            skipped=0,
            errors=0,
            flaky=sum(1 for rate in flaky_results.values() if 0.5 <= rate < 0.9),
            total_duration=end_time - start_time,
            start_time=start_time,
            end_time=end_time,
            worker_count=self.config.parallel.max_workers,
            results=[]
        )
        
        report = self.reporter.generate_report(flaky_summary, "flaky_detection")
        
        # Add flaky-specific recommendations
        truly_flaky = [test for test, rate in flaky_results.items() if 0.2 <= rate <= 0.8]
        recommendations = [
            f"Identified {len(truly_flaky)} flaky tests that should be fixed or quarantined",
            f"Success rates: {dict(flaky_results)}"
        ]
        
        return FrameworkResult(
            mode=FrameworkMode.FLAKY_DETECTION,
            selection=flaky_selection,
            summary=flaky_summary,
            report=report,
            success=len(truly_flaky) == 0,
            duration=end_time - start_time,
            recommendations=recommendations
        )
    
    def run_custom_tests(self, test_patterns: List[str], 
                        execution_id: Optional[str] = None) -> FrameworkResult:
        """Run custom test selection"""
        self.logger.info(f"🎯 Running custom test selection: {test_patterns}")
        
        # Find tests matching patterns
        selected_tests = []
        for pattern in test_patterns:
            matching_tests = list(self.config.project_root.glob(f"**/{pattern}"))
            for test_path in matching_tests:
                if self.selector._is_test_file(test_path):
                    test_file = self.selector._get_test_file_info(test_path)
                    if test_file:
                        selected_tests.append(test_file)
        
        custom_selection = TestSelection(
            selected_tests=selected_tests,
            reason=f"Custom test selection: {test_patterns}",
            confidence=1.0,
            estimated_duration=sum(t.avg_duration for t in selected_tests)
        )
        
        return self._run_framework(
            mode=FrameworkMode.CUSTOM,
            selection_method=lambda: custom_selection,
            execution_id=execution_id or f"custom_{int(time.time())}"
        )
    
    def _run_framework(self, mode: FrameworkMode, 
                      selection_method: Callable[[], TestSelection],
                      execution_id: str) -> FrameworkResult:
        """Internal method to run regression testing framework"""
        
        start_time = time.time()
        
        try:
            # Select tests
            self.logger.info("🔍 Selecting tests...")
            selection = selection_method()
            
            self.logger.info(f"📊 Selected {len(selection.selected_tests)} tests "
                           f"(confidence: {selection.confidence:.2f}, "
                           f"estimated duration: {selection.estimated_duration:.1f}s)")
            
            if not selection.selected_tests:
                self.logger.warning("⚠️  No tests selected")
                
                empty_summary = ExecutionSummary(
                    total_tests=0, passed=0, failed=0, skipped=0, errors=0, flaky=0,
                    total_duration=0.0, start_time=start_time, end_time=time.time(),
                    worker_count=0, results=[]
                )
                
                report = self.reporter.generate_report(empty_summary, execution_id)
                
                return FrameworkResult(
                    mode=mode,
                    selection=selection,
                    summary=empty_summary,
                    report=report,
                    success=True,
                    duration=time.time() - start_time,
                    recommendations=["No tests selected - verify test selection criteria"]
                )
            
            # Execute tests
            self.logger.info("🚀 Executing tests...")
            
            def progress_callback(result):
                if result.status.value in ['passed', 'failed', 'error']:
                    status_emoji = "✅" if result.status.value == 'passed' else "❌"
                    test_name = Path(result.test_file).name
                    self.logger.info(f"{status_emoji} {test_name} ({result.duration:.1f}s)")
            
            summary = self.runner.run_tests(selection, progress_callback)
            
            # Generate report
            self.logger.info("📊 Generating report...")
            report = self.reporter.generate_report(summary, execution_id)
            
            # Determine success
            success = self._determine_success(mode, summary)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Log summary
            self._log_summary(mode, summary, duration, success)
            
            # Send notifications if configured
            if not success:
                self._send_notifications(report)
            
            return FrameworkResult(
                mode=mode,
                selection=selection,
                summary=summary,
                report=report,
                success=success,
                duration=duration,
                recommendations=report.recommendations
            )
            
        except Exception as e:
            self.logger.error(f"❌ Framework execution failed: {str(e)}", exc_info=True)
            
            # Create error result
            error_summary = ExecutionSummary(
                total_tests=0, passed=0, failed=0, skipped=0, errors=1, flaky=0,
                total_duration=0.0, start_time=start_time, end_time=time.time(),
                worker_count=0, results=[]
            )
            
            error_report = self.reporter.generate_report(error_summary, execution_id)
            
            return FrameworkResult(
                mode=mode,  
                selection=TestSelection([], f"Error: {str(e)}", 0.0, 0.0),
                summary=error_summary,
                report=error_report,
                success=False,
                duration=time.time() - start_time,
                recommendations=[f"Framework error occurred: {str(e)}"]
            )
    
    def _determine_success(self, mode: FrameworkMode, summary: ExecutionSummary) -> bool:
        """Determine if test execution was successful based on mode"""
        
        # Mode-specific success criteria
        if mode == FrameworkMode.PRE_COMMIT:
            # Pre-commit: All critical tests must pass
            return summary.failed == 0 and summary.errors == 0
        
        elif mode == FrameworkMode.PULL_REQUEST:
            # PR: 95% success rate required
            return summary.success_rate >= 0.95
        
        elif mode == FrameworkMode.NIGHTLY:
            # Nightly: 90% success rate acceptable
            return summary.success_rate >= 0.90
        
        elif mode == FrameworkMode.RELEASE:
            # Release: 98% success rate required
            return summary.success_rate >= 0.98
        
        elif mode == FrameworkMode.FLAKY_DETECTION:
            # Flaky detection: Success if analysis completes
            return True
        
        else:
            # Custom: 90% success rate
            return summary.success_rate >= 0.90
    
    def _log_summary(self, mode: FrameworkMode, summary: ExecutionSummary, 
                    duration: float, success: bool):
        """Log execution summary"""
        
        status_emoji = "✅" if success else "❌"
        
        self.logger.info(f"\n{status_emoji} {mode.value.upper()} REGRESSION TEST SUMMARY")
        self.logger.info(f"📊 Tests: {summary.total_tests} total")
        self.logger.info(f"✅ Passed: {summary.passed}")
        self.logger.info(f"❌ Failed: {summary.failed}")
        self.logger.info(f"⏭️  Skipped: {summary.skipped}")
        self.logger.info(f"💥 Errors: {summary.errors}")
        self.logger.info(f"🔄 Flaky: {summary.flaky}")
        self.logger.info(f"📈 Success Rate: {summary.success_rate:.1%}")
        self.logger.info(f"⏱️  Duration: {duration:.1f}s")
        self.logger.info(f"👥 Workers: {summary.worker_count}")
        
        if not success:
            self.logger.error("❌ Regression tests FAILED")
        else:
            self.logger.info("✅ Regression tests PASSED")
    
    def _send_notifications(self, report: RegressionReport):
        """Send notifications for failed test runs"""
        
        try:
            # Slack notification
            if self.config.slack_webhook:
                self._send_slack_notification(report)
            
            # Email notification (placeholder)
            if self.config.email_recipients:
                self._send_email_notification(report)
                
        except Exception as e:
            self.logger.error(f"Failed to send notifications: {str(e)}")
    
    def _send_slack_notification(self, report: RegressionReport):
        """Send Slack notification"""
        import json
        import urllib.request
        
        message = {
            "text": f"🔴 Regression Tests Failed - {report.execution_id}",
            "attachments": [
                {
                    "color": "danger",
                    "fields": [
                        {"title": "Success Rate", "value": f"{report.summary.success_rate:.1%}", "short": True},
                        {"title": "Failed Tests", "value": str(report.summary.failed), "short": True},
                        {"title": "Duration", "value": f"{report.summary.total_duration/60:.1f}m", "short": True},
                        {"title": "Flaky Tests", "value": str(len(report.flaky_tests)), "short": True}
                    ]
                }
            ]
        }
        
        req = urllib.request.Request(
            self.config.slack_webhook,
            data=json.dumps(message).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        urllib.request.urlopen(req)
    
    def _send_email_notification(self, report: RegressionReport):
        """Send email notification (placeholder)"""
        # TODO: Implement email notification
        self.logger.info(f"Would send email to: {self.config.email_recipients}")
    
    def cleanup(self):
        """Cleanup framework resources"""
        self.runner.shutdown()
        self.selector.save_test_history()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
