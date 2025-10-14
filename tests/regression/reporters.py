"""
Regression Test Reporter
Comprehensive reporting and analytics for regression test results
"""

import json
import time
import statistics
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from .config import RegressionTestConfig
from .runners import ExecutionSummary, TestResult, TestStatus


@dataclass
class TestTrend:
    """Test performance trend data"""
    test_name: str
    durations: List[float]
    success_rates: List[float]
    dates: List[str]
    
    @property
    def avg_duration(self) -> float:
        return statistics.mean(self.durations) if self.durations else 0.0
    
    @property
    def duration_trend(self) -> str:
        if len(self.durations) < 2:
            return "stable"
        
        recent = statistics.mean(self.durations[-3:])
        older = statistics.mean(self.durations[:-3] if len(self.durations) > 3 else self.durations[:1])
        
        if recent > older * 1.2:
            return "increasing"
        elif recent < older * 0.8:
            return "decreasing"
        else:
            return "stable"
    
    @property
    def stability(self) -> str:
        if not self.success_rates:
            return "unknown"
        
        avg_success = statistics.mean(self.success_rates)
        
        if avg_success >= 0.95:
            return "stable"
        elif avg_success >= 0.8:
            return "flaky"
        else:
            return "unstable"


@dataclass
class RegressionReport:
    """Comprehensive regression test report"""
    execution_id: str
    timestamp: datetime
    summary: ExecutionSummary
    test_trends: List[TestTrend]
    flaky_tests: List[str]
    slow_tests: List[str]
    failed_tests: List[TestResult]
    coverage_data: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, float]] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class RegressionReporter:
    """Generate comprehensive regression test reports"""
    
    def __init__(self, config: RegressionTestConfig):
        self.config = config
        self.history_file = config.project_root / ".regression_history.json"
        self.history = self._load_history()
    
    def _load_history(self) -> Dict[str, Any]:
        """Load historical test data"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"executions": [], "trends": {}}
    
    def _save_history(self):
        """Save historical test data"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except IOError:
            pass
    
    def generate_report(self, summary: ExecutionSummary, 
                       execution_id: Optional[str] = None) -> RegressionReport:
        """Generate comprehensive regression report"""
        
        if execution_id is None:
            execution_id = f"exec_{int(time.time())}"
        
        # Update history with current execution
        self._update_history(summary, execution_id)
        
        # Generate test trends
        test_trends = self._calculate_test_trends()
        
        # Identify problematic tests
        flaky_tests = self._identify_flaky_tests(summary)
        slow_tests = self._identify_slow_tests(summary)
        failed_tests = [r for r in summary.results if r.status == TestStatus.FAILED]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(summary, test_trends, flaky_tests, slow_tests)
        
        report = RegressionReport(
            execution_id=execution_id,
            timestamp=datetime.now(),
            summary=summary,
            test_trends=test_trends,
            flaky_tests=flaky_tests,
            slow_tests=slow_tests,
            failed_tests=failed_tests,
            recommendations=recommendations
        )
        
        # Generate output files
        self._generate_output_files(report)
        
        return report
    
    def _update_history(self, summary: ExecutionSummary, execution_id: str):
        """Update historical data with current execution"""
        
        execution_data = {
            "id": execution_id,
            "timestamp": datetime.now().isoformat(),
            "total_tests": summary.total_tests,
            "passed": summary.passed,
            "failed": summary.failed,
            "duration": summary.total_duration,
            "success_rate": summary.success_rate,
            "results": [r.to_dict() for r in summary.results]
        }
        
        self.history["executions"].append(execution_data)
        
        # Keep only last 100 executions
        if len(self.history["executions"]) > 100:
            self.history["executions"] = self.history["executions"][-100:]
        
        # Update test trends
        for result in summary.results:
            test_path = result.test_file
            
            if test_path not in self.history["trends"]:
                self.history["trends"][test_path] = {
                    "durations": [],
                    "success_rates": [],
                    "dates": []
                }
            
            trend_data = self.history["trends"][test_path]
            trend_data["durations"].append(result.duration)
            trend_data["success_rates"].append(1.0 if result.status == TestStatus.PASSED else 0.0)
            trend_data["dates"].append(datetime.now().isoformat())
            
            # Keep only last 50 data points per test
            for key in ["durations", "success_rates", "dates"]:
                if len(trend_data[key]) > 50:
                    trend_data[key] = trend_data[key][-50:]
        
        self._save_history()
    
    def _calculate_test_trends(self) -> List[TestTrend]:
        """Calculate test performance trends"""
        trends = []
        
        for test_path, trend_data in self.history["trends"].items():
            if len(trend_data["durations"]) >= 3:  # Need at least 3 data points
                trend = TestTrend(
                    test_name=test_path,
                    durations=trend_data["durations"],
                    success_rates=trend_data["success_rates"],
                    dates=trend_data["dates"]
                )
                trends.append(trend)
        
        return trends
    
    def _identify_flaky_tests(self, summary: ExecutionSummary) -> List[str]:
        """Identify tests that are flaky based on history"""
        flaky_tests = []
        
        for test_path, trend_data in self.history["trends"].items():
            if len(trend_data["success_rates"]) >= 5:
                recent_success_rates = trend_data["success_rates"][-10:]  # Last 10 runs
                avg_success = statistics.mean(recent_success_rates)
                
                # Test is flaky if success rate is between 20% and 80%
                if 0.2 <= avg_success <= 0.8:
                    flaky_tests.append(test_path)
        
        return flaky_tests
    
    def _identify_slow_tests(self, summary: ExecutionSummary) -> List[str]:
        """Identify tests that are slow"""
        slow_tests = []
        
        if not summary.results:
            return slow_tests
        
        # Calculate percentiles
        durations = [r.duration for r in summary.results if r.duration > 0]
        if durations:
            p90_duration = statistics.quantiles(durations, n=10)[8]  # 90th percentile
            
            for result in summary.results:
                if result.duration > p90_duration and result.duration > 60:  # Slow if > 1 minute and in top 10%
                    slow_tests.append(result.test_file)
        
        return slow_tests
    
    def _generate_recommendations(self, summary: ExecutionSummary, trends: List[TestTrend], 
                                flaky_tests: List[str], slow_tests: List[str]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Success rate recommendations
        if summary.success_rate < 0.9:
            recommendations.append(
                f"Success rate is {summary.success_rate:.1%}. Consider investigating failed tests."
            )
        
        # Duration recommendations
        if summary.total_duration > 1800:  # 30 minutes
            recommendations.append(
                f"Test suite took {summary.total_duration/60:.1f} minutes. Consider parallelization or test optimization."
            )
        
        # Flaky test recommendations
        if flaky_tests:
            recommendations.append(
                f"Found {len(flaky_tests)} flaky tests. Consider fixing or quarantining them."
            )
        
        # Slow test recommendations
        if slow_tests:
            recommendations.append(
                f"Found {len(slow_tests)} slow tests. Consider optimization or moving to nightly suite."
            )
        
        # Test trend recommendations
        increasing_duration_tests = [t for t in trends if t.duration_trend == "increasing"]
        if increasing_duration_tests:
            recommendations.append(
                f"Found {len(increasing_duration_tests)} tests with increasing duration trend. Review for performance regressions."
            )
        
        # Coverage recommendations (if available)
        if hasattr(self, 'coverage_data') and self.coverage_data:
            coverage = self.coverage_data.get('total_coverage', 0)
            if coverage < self.config.reporting.coverage_threshold:
                recommendations.append(
                    f"Code coverage is {coverage:.1f}%, below target of {self.config.reporting.coverage_threshold:.1f}%."
                )
        
        return recommendations
    
    def _generate_output_files(self, report: RegressionReport):
        """Generate output files in various formats"""
        
        output_dir = self.config.reporting.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = f"regression_report_{report.execution_id}"
        
        # JSON report
        if "json" in self.config.reporting.formats:
            self._generate_json_report(report, output_dir / f"{base_name}.json")
        
        # HTML report
        if "html" in self.config.reporting.formats:
            self._generate_html_report(report, output_dir / f"{base_name}.html")
        
        # JUnit XML
        if "junit" in self.config.reporting.formats:
            self._generate_junit_report(report, output_dir / f"{base_name}.xml")
        
        # CSV summary
        if "csv" in self.config.reporting.formats:
            self._generate_csv_report(report, output_dir / f"{base_name}.csv")
    
    def _generate_json_report(self, report: RegressionReport, output_path: Path):
        """Generate JSON report"""
        try:
            report_data = {
                "execution_id": report.execution_id,
                "timestamp": report.timestamp.isoformat(),
                "summary": {
                    "total_tests": report.summary.total_tests,
                    "passed": report.summary.passed,
                    "failed": report.summary.failed,
                    "skipped": report.summary.skipped,
                    "errors": report.summary.errors,
                    "success_rate": report.summary.success_rate,
                    "total_duration": report.summary.total_duration
                },
                "flaky_tests": report.flaky_tests,
                "slow_tests": report.slow_tests,
                "failed_tests": [r.to_dict() for r in report.failed_tests],
                "recommendations": report.recommendations,
                "trends": [
                    {
                        "test_name": t.test_name,
                        "avg_duration": t.avg_duration,
                        "duration_trend": t.duration_trend,
                        "stability": t.stability
                    }
                    for t in report.test_trends
                ]
            }
            
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2)
                
        except IOError:
            pass
    
    def _generate_html_report(self, report: RegressionReport, output_path: Path):
        """Generate HTML report"""
        try:
            html_content = self._create_html_template(report)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
        except IOError:
            pass
    
    def _create_html_template(self, report: RegressionReport) -> str:
        """Create HTML report template"""
        
        # Calculate metrics
        success_rate_color = "green" if report.summary.success_rate >= 0.9 else "orange" if report.summary.success_rate >= 0.7 else "red"
        duration_color = "green" if report.summary.total_duration < 600 else "orange" if report.summary.total_duration < 1800 else "red"
        
        # Failed tests table
        failed_tests_html = ""
        if report.failed_tests:
            failed_tests_html = "<h3>Failed Tests</h3><table class='failed-tests'><tr><th>Test</th><th>Error</th><th>Duration</th></tr>"
            for test in report.failed_tests[:10]:  # Show first 10
                failed_tests_html += f"<tr><td>{Path(test.test_file).name}</td><td>{test.error[:100]}...</td><td>{test.duration:.1f}s</td></tr>"
            failed_tests_html += "</table>"
        
        # Recommendations
        recommendations_html = ""
        if report.recommendations:
            recommendations_html = "<h3>Recommendations</h3><ul>"
            for rec in report.recommendations:
                recommendations_html += f"<li>{rec}</li>"
            recommendations_html += "</ul>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Regression Test Report - {report.execution_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .metrics {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric {{ text-align: center; padding: 15px; background: white; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .metric-value {{ font-size: 2em; font-weight: bold; }}
                .green {{ color: #4CAF50; }}
                .orange {{ color: #FF9800; }}
                .red {{ color: #F44336; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .failed-tests {{ max-width: 100%; }}
                .failed-tests td {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Regression Test Report</h1>
                <p><strong>Execution ID:</strong> {report.execution_id}</p>
                <p><strong>Timestamp:</strong> {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value {success_rate_color}">{report.summary.success_rate:.1%}</div>
                    <div>Success Rate</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{report.summary.total_tests}</div>
                    <div>Total Tests</div>
                </div>
                <div class="metric">
                    <div class="metric-value {duration_color}">{report.summary.total_duration/60:.1f}m</div>
                    <div>Duration</div>
                </div>
                <div class="metric">
                    <div class="metric-value {'red' if report.flaky_tests else 'green'}">{len(report.flaky_tests)}</div>
                    <div>Flaky Tests</div>
                </div>
            </div>
            
            {failed_tests_html}
            
            {recommendations_html}
            
            <h3>Test Results Breakdown</h3>
            <table>
                <tr>
                    <th>Status</th>
                    <th>Count</th>
                    <th>Percentage</th>
                </tr>
                <tr>
                    <td>Passed</td>
                    <td>{report.summary.passed}</td>
                    <td>{report.summary.passed/report.summary.total_tests*100:.1f}%</td>
                </tr>
                <tr>
                    <td>Failed</td>
                    <td>{report.summary.failed}</td>
                    <td>{report.summary.failed/report.summary.total_tests*100:.1f}%</td>
                </tr>
                <tr>
                    <td>Skipped</td>
                    <td>{report.summary.skipped}</td>
                    <td>{report.summary.skipped/report.summary.total_tests*100:.1f}%</td>
                </tr>
                <tr>
                    <td>Errors</td>
                    <td>{report.summary.errors}</td>
                    <td>{report.summary.errors/report.summary.total_tests*100:.1f}%</td>
                </tr>
            </table>
            
            <p><em>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
        </body>
        </html>
        """
    
    def _generate_junit_report(self, report: RegressionReport, output_path: Path):
        """Generate JUnit XML report"""
        try:
            root = ET.Element("testsuites")
            root.set("name", "RegressionTests")
            root.set("tests", str(report.summary.total_tests))
            root.set("failures", str(report.summary.failed))
            root.set("errors", str(report.summary.errors))
            root.set("time", str(report.summary.total_duration))
            
            testsuite = ET.SubElement(root, "testsuite")
            testsuite.set("name", "RegressionTestSuite")
            testsuite.set("tests", str(report.summary.total_tests))
            testsuite.set("failures", str(report.summary.failed))
            testsuite.set("errors", str(report.summary.errors))
            testsuite.set("time", str(report.summary.total_duration))
            
            for result in report.summary.results:
                testcase = ET.SubElement(testsuite, "testcase")
                testcase.set("classname", Path(result.test_file).stem)
                testcase.set("name", Path(result.test_file).name)
                testcase.set("time", str(result.duration))
                
                if result.status == TestStatus.FAILED:
                    failure = ET.SubElement(testcase, "failure")
                    failure.set("message", "Test failed")
                    failure.text = result.error
                elif result.status == TestStatus.ERROR:
                    error = ET.SubElement(testcase, "error")
                    error.set("message", "Test error")
                    error.text = result.error
                elif result.status == TestStatus.SKIPPED:
                    skipped = ET.SubElement(testcase, "skipped")
                    skipped.set("message", "Test skipped")
            
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
        except Exception:
            pass
    
    def _generate_csv_report(self, report: RegressionReport, output_path: Path):
        """Generate CSV summary report"""
        try:
            import csv
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Test File', 'Status', 'Duration', 'Worker', 'Error'])
                
                for result in report.summary.results:
                    writer.writerow([
                        result.test_file,
                        result.status.value,
                        result.duration,
                        result.worker_id or '',
                        result.error[:100] if result.error else ''
                    ])
                    
        except ImportError:
            pass  # csv module not available
        except IOError:
            pass
