"""
Comprehensive test configuration and runner for AI Nutritionist application.

This module provides:
- Test suite configuration and organization
- Coverage reporting and analysis
- Test execution orchestration
- Performance benchmarking
- Test result reporting
"""

import pytest
import sys
import os
from pathlib import Path
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Any
import coverage


class ComprehensiveTestRunner:
    """Orchestrate comprehensive test execution and reporting."""
    
    def __init__(self, project_root: str = None):
        """Initialize test runner with project configuration."""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.test_results = {}
        self.coverage_data = {}
        
    def run_all_tests(self, coverage_threshold: float = 90.0) -> Dict[str, Any]:
        """Run all test suites with comprehensive coverage reporting."""
        print("🚀 Starting Comprehensive Test Suite Execution")
        print("=" * 60)
        
        test_suites = [
            {
                'name': 'Unit Tests - Nutrition Domain',
                'path': 'tests/unit/test_nutrition_comprehensive.py',
                'category': 'unit'
            },
            {
                'name': 'Unit Tests - Meal Planning Domain', 
                'path': 'tests/unit/test_meal_planning_comprehensive.py',
                'category': 'unit'
            },
            {
                'name': 'Unit Tests - Business Domain',
                'path': 'tests/unit/test_business_comprehensive.py',
                'category': 'unit'
            },
            {
                'name': 'E2E Tests - Smoke Tests',
                'path': 'tests/e2e/test_smoke.py',
                'category': 'e2e_smoke'
            },
            {
                'name': 'E2E Tests - User Journeys',
                'path': 'tests/e2e/user_journeys/',
                'category': 'e2e_journeys'
            },
            {
                'name': 'E2E Tests - Multi Channel',
                'path': 'tests/e2e/channels/',
                'category': 'e2e_channels'
            },
            {
                'name': 'Unit Tests - Infrastructure Domain',
                'path': 'tests/unit/test_infrastructure_comprehensive.py',
                'category': 'unit'
            },
            {
                'name': 'Unit Tests - Messaging Domain',
                'path': 'tests/unit/test_messaging_comprehensive.py',
                'category': 'unit'
            },
            {
                'name': 'Unit Tests - Community & Personalization',
                'path': 'tests/unit/test_community_personalization_comprehensive.py',
                'category': 'unit'
            },
            {
                'name': 'Integration Tests - End-to-End Workflows',
                'path': 'tests/integration/test_comprehensive_integration.py',
                'category': 'integration'
            }
        ]
        
        # Initialize coverage
        cov = coverage.Coverage(source=['src'])
        cov.start()
        
        overall_results = {
            'execution_time': None,
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'coverage_percentage': 0.0,
            'suite_results': [],
            'coverage_report': {},
            'performance_metrics': {},
            'recommendations': []
        }
        
        start_time = datetime.now()
        
        try:
            for suite in test_suites:
                print(f"\n📋 Running: {suite['name']}")
                print("-" * 50)
                
                suite_result = self._run_test_suite(suite)
                overall_results['suite_results'].append(suite_result)
                
                # Aggregate results
                overall_results['total_tests'] += suite_result['total_tests']
                overall_results['passed_tests'] += suite_result['passed_tests']
                overall_results['failed_tests'] += suite_result['failed_tests']
                overall_results['skipped_tests'] += suite_result['skipped_tests']
                
                print(f"✅ {suite_result['passed_tests']}/{suite_result['total_tests']} tests passed")
                
                if suite_result['failed_tests'] > 0:
                    print(f"❌ {suite_result['failed_tests']} tests failed")
                    for failure in suite_result.get('failures', []):
                        print(f"   - {failure}")
        
        finally:
            # Stop coverage and generate report
            cov.stop()
            cov.save()
            
            # Generate coverage report
            coverage_report = self._generate_coverage_report(cov)
            overall_results['coverage_report'] = coverage_report
            overall_results['coverage_percentage'] = coverage_report.get('total_coverage', 0.0)
        
        end_time = datetime.now()
        overall_results['execution_time'] = (end_time - start_time).total_seconds()
        
        # Generate performance metrics
        overall_results['performance_metrics'] = self._calculate_performance_metrics(overall_results)
        
        # Generate recommendations
        overall_results['recommendations'] = self._generate_recommendations(
            overall_results, coverage_threshold
        )
        
        # Print final report
        self._print_final_report(overall_results, coverage_threshold)
        
        return overall_results
    
    def _run_test_suite(self, suite: Dict[str, str]) -> Dict[str, Any]:
        """Run individual test suite and collect results."""
        suite_path = self.project_root / suite['path']
        
        if not suite_path.exists():
            return {
                'name': suite['name'],
                'category': suite['category'],
                'status': 'skipped',
                'reason': 'Test file not found',
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'skipped_tests': 0,
                'execution_time': 0.0,
                'failures': []
            }
        
        start_time = datetime.now()
        
        try:
            # Run pytest with detailed output
            cmd = [
                sys.executable, '-m', 'pytest',
                str(suite_path),
                '-v',
                '--tb=short',
                '--no-header',
                '--quiet'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Parse pytest output
            test_results = self._parse_pytest_output(result.stdout, result.stderr)
            
            return {
                'name': suite['name'],
                'category': suite['category'],
                'status': 'completed',
                'total_tests': test_results['total'],
                'passed_tests': test_results['passed'],
                'failed_tests': test_results['failed'],
                'skipped_tests': test_results['skipped'],
                'execution_time': execution_time,
                'failures': test_results['failures'],
                'warnings': test_results.get('warnings', [])
            }
            
        except Exception as e:
            return {
                'name': suite['name'],
                'category': suite['category'],
                'status': 'error',
                'error': str(e),
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 1,  # Count as failed
                'skipped_tests': 0,
                'execution_time': 0.0,
                'failures': [f"Suite execution error: {str(e)}"]
            }
    
    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse pytest output to extract test results."""
        lines = stdout.split('\n') + stderr.split('\n')
        
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'failures': [],
            'warnings': []
        }
        
        for line in lines:
            line = line.strip()
            
            # Parse summary line (e.g., "5 passed, 1 failed in 2.34s")
            if 'passed' in line and 'failed' in line:
                parts = line.split(',')
                for part in parts:
                    part = part.strip()
                    if 'passed' in part:
                        results['passed'] = int(part.split()[0])
                    elif 'failed' in part:
                        results['failed'] = int(part.split()[0])
                    elif 'skipped' in part:
                        results['skipped'] = int(part.split()[0])
            
            # Collect failure information
            elif 'FAILED' in line:
                results['failures'].append(line)
            
            # Collect warnings
            elif 'WARNING' in line:
                results['warnings'].append(line)
        
        results['total'] = results['passed'] + results['failed'] + results['skipped']
        
        return results
    
    def _generate_coverage_report(self, cov: coverage.Coverage) -> Dict[str, Any]:
        """Generate comprehensive coverage report."""
        try:
            # Get coverage data
            coverage_data = cov.get_data()
            
            # Generate report
            report_data = {}
            total_statements = 0
            total_missing = 0
            
            # Analyze coverage by file
            for filename in coverage_data.measured_files():
                if 'src/' in filename:  # Only analyze source files
                    analysis = cov.analysis2(filename)
                    statements = len(analysis[1])
                    missing = len(analysis[3])
                    
                    if statements > 0:
                        file_coverage = ((statements - missing) / statements) * 100
                        
                        relative_path = filename.replace(str(self.project_root), '').lstrip('/')
                        report_data[relative_path] = {
                            'statements': statements,
                            'missing': missing,
                            'coverage': file_coverage
                        }
                        
                        total_statements += statements
                        total_missing += missing
            
            # Calculate overall coverage
            total_coverage = 0.0
            if total_statements > 0:
                total_coverage = ((total_statements - total_missing) / total_statements) * 100
            
            return {
                'total_coverage': total_coverage,
                'total_statements': total_statements,
                'total_missing': total_missing,
                'file_coverage': report_data
            }
            
        except Exception as e:
            return {
                'total_coverage': 0.0,
                'error': f"Coverage calculation failed: {str(e)}"
            }
    
    def _calculate_performance_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics from test results."""
        suite_results = results['suite_results']
        
        if not suite_results:
            return {}
        
        # Calculate average execution time per test
        total_execution_time = sum(suite['execution_time'] for suite in suite_results)
        total_tests = results['total_tests']
        
        avg_time_per_test = total_execution_time / total_tests if total_tests > 0 else 0
        
        # Find slowest test suites
        slowest_suites = sorted(
            suite_results,
            key=lambda x: x['execution_time'],
            reverse=True
        )[:3]
        
        # Calculate success rate
        success_rate = (results['passed_tests'] / results['total_tests'] * 100) if results['total_tests'] > 0 else 0
        
        return {
            'total_execution_time': total_execution_time,
            'average_time_per_test': avg_time_per_test,
            'success_rate': success_rate,
            'slowest_suites': [
                {'name': suite['name'], 'time': suite['execution_time']}
                for suite in slowest_suites
            ]
        }
    
    def _generate_recommendations(self, results: Dict[str, Any], coverage_threshold: float) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Coverage recommendations
        coverage_pct = results['coverage_percentage']
        if coverage_pct < coverage_threshold:
            gap = coverage_threshold - coverage_pct
            recommendations.append(
                f"📈 Increase test coverage by {gap:.1f}% to reach {coverage_threshold}% target"
            )
        
        # Failure recommendations
        if results['failed_tests'] > 0:
            recommendations.append(
                f"🔧 Fix {results['failed_tests']} failing tests for improved reliability"
            )
        
        # Performance recommendations
        performance = results.get('performance_metrics', {})
        avg_time = performance.get('average_time_per_test', 0)
        if avg_time > 1.0:
            recommendations.append(
                f"⚡ Optimize test performance - average test time is {avg_time:.2f}s (target: <1s)"
            )
        
        # Coverage gap analysis
        file_coverage = results.get('coverage_report', {}).get('file_coverage', {})
        low_coverage_files = [
            (file, data['coverage'])
            for file, data in file_coverage.items()
            if data['coverage'] < 80.0
        ]
        
        if low_coverage_files:
            recommendations.append(
                f"🎯 Focus on {len(low_coverage_files)} files with <80% coverage"
            )
        
        return recommendations
    
    def _print_final_report(self, results: Dict[str, Any], coverage_threshold: float):
        """Print comprehensive final test report."""
        print("\n" + "=" * 80)
        print("🏆 COMPREHENSIVE TEST EXECUTION REPORT")
        print("=" * 80)
        
        # Summary statistics
        print(f"\n📊 SUMMARY STATISTICS")
        print(f"   Total Tests:       {results['total_tests']}")
        print(f"   Passed:           {results['passed_tests']} ✅")
        print(f"   Failed:           {results['failed_tests']} ❌")
        print(f"   Skipped:          {results['skipped_tests']} ⏭️")
        print(f"   Success Rate:     {(results['passed_tests']/results['total_tests']*100):.1f}%")
        print(f"   Execution Time:   {results['execution_time']:.2f} seconds")
        
        # Coverage report
        print(f"\n📈 COVERAGE ANALYSIS")
        coverage_pct = results['coverage_percentage']
        coverage_status = "✅" if coverage_pct >= coverage_threshold else "❌"
        print(f"   Coverage:         {coverage_pct:.1f}% {coverage_status}")
        print(f"   Target:           {coverage_threshold}%")
        
        if coverage_pct >= coverage_threshold:
            print(f"   🎉 Coverage target achieved!")
        else:
            gap = coverage_threshold - coverage_pct
            print(f"   📋 Need {gap:.1f}% more coverage to reach target")
        
        # Performance metrics
        performance = results.get('performance_metrics', {})
        if performance:
            print(f"\n⚡ PERFORMANCE METRICS")
            print(f"   Avg Time/Test:    {performance.get('average_time_per_test', 0):.3f}s")
            print(f"   Success Rate:     {performance.get('success_rate', 0):.1f}%")
            
            slowest = performance.get('slowest_suites', [])
            if slowest:
                print(f"   Slowest Suites:")
                for suite in slowest[:3]:
                    print(f"     - {suite['name']}: {suite['time']:.2f}s")
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Final status
        print(f"\n🎯 FINAL STATUS")
        if results['failed_tests'] == 0 and coverage_pct >= coverage_threshold:
            print("   🎉 ALL TESTS PASSED WITH EXCELLENT COVERAGE!")
            print("   ✨ Production-ready quality achieved!")
        elif results['failed_tests'] == 0:
            print("   ✅ All tests passed, but coverage needs improvement")
        elif coverage_pct >= coverage_threshold:
            print("   📈 Excellent coverage, but some tests are failing")
        else:
            print("   🔧 Tests need fixes and coverage improvement required")
        
        print("=" * 80)


def create_pytest_config():
    """Create pytest configuration file."""
    config_content = """
# Pytest configuration for AI Nutritionist comprehensive test suite

[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-report=xml",
    "--cov-fail-under=90",
    "--tb=short"
]
testpaths = [
    "tests",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests", 
    "performance: Performance tests",
    "slow: Slow running tests",
    "asyncio: Async tests"
]
filterwarnings = [
    "ignore::UserWarning",
    "ignore::DeprecationWarning",
]
asyncio_mode = "auto"
"""
    
    with open("pyproject.toml", "a") as f:
        f.write(config_content)


def main():
    """Main entry point for comprehensive test execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run comprehensive AI Nutritionist test suite")
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=90.0,
        help="Code coverage threshold percentage (default: 90.0)"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate pytest configuration file"
    )
    
    args = parser.parse_args()
    
    if args.generate_config:
        create_pytest_config()
        print("✅ Pytest configuration generated in pyproject.toml")
        return
    
    # Run comprehensive test suite
    runner = ComprehensiveTestRunner(args.project_root)
    results = runner.run_all_tests(args.coverage_threshold)
    
    # Exit with appropriate code
    if results['failed_tests'] == 0 and results['coverage_percentage'] >= args.coverage_threshold:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    main()
