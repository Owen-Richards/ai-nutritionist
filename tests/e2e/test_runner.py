"""
E2E Test Runner and Configuration

Main entry point for running E2E tests with comprehensive
reporting and configuration management.
"""

import asyncio
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pytest

from .framework import E2ETestRunner, create_test_environment
from .user_journeys.test_critical_flows import (
    RegistrationToFirstMealPlanJourney,
    DailyMealTrackingJourney,
    PaymentSubscriptionFlowJourney,
    FamilyAccountSetupJourney,
    HealthDataSyncJourney
)
from .channels.test_multi_channel import (
    WhatsAppConversationFlow,
    SMSInteractionFlow,
    WebAppFlow,
    CrossChannelConsistencyTest,
    ChannelSpecificFeatureTest
)
from .performance.test_performance_scenarios import (
    LoadTestingScenarios,
    StressTestingScenarios,
    SpikeTestingScenarios,
    EnduranceTestingScenarios
)


class E2ETestSuite:
    """Main E2E test suite orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.environment = create_test_environment(config.get('environment', 'local'))
        self.test_runner = E2ETestRunner(self.environment)
        self.results: Dict[str, Any] = {}
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run the complete E2E test suite"""
        print(f"🚀 Starting E2E Test Suite - Environment: {self.environment.environment}")
        start_time = time.time()
        
        # Run different test categories
        results = {}
        
        if self.config.get('run_user_journeys', True):
            results['user_journeys'] = await self._run_user_journey_tests()
        
        if self.config.get('run_multi_channel', True):
            results['multi_channel'] = await self._run_multi_channel_tests()
        
        if self.config.get('run_performance', True):
            results['performance'] = await self._run_performance_tests()
        
        # Generate comprehensive report
        total_duration = time.time() - start_time
        final_report = self._generate_final_report(results, total_duration)
        
        # Save report
        await self._save_report(final_report)
        
        return final_report
    
    async def _run_user_journey_tests(self) -> Dict[str, Any]:
        """Run user journey tests"""
        print("\n📱 Running User Journey Tests...")
        
        journey_tests = [
            RegistrationToFirstMealPlanJourney,
            DailyMealTrackingJourney,
            PaymentSubscriptionFlowJourney,
            FamilyAccountSetupJourney,
            HealthDataSyncJourney
        ]
        
        return await self.test_runner.run_test_suite(journey_tests)
    
    async def _run_multi_channel_tests(self) -> Dict[str, Any]:
        """Run multi-channel tests"""
        print("\n💬 Running Multi-Channel Tests...")
        
        channel_tests = [
            WhatsAppConversationFlow,
            SMSInteractionFlow,
            WebAppFlow,
            CrossChannelConsistencyTest,
            ChannelSpecificFeatureTest
        ]
        
        return await self.test_runner.run_test_suite(channel_tests)
    
    async def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests"""
        print("\n⚡ Running Performance Tests...")
        
        performance_tests = [
            LoadTestingScenarios,
            StressTestingScenarios,
            SpikeTestingScenarios,
            EnduranceTestingScenarios
        ]
        
        return await self.test_runner.run_test_suite(performance_tests)
    
    def _generate_final_report(self, results: Dict[str, Any], duration: float) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for category, category_results in results.items():
            if 'summary' in category_results:
                summary = category_results['summary']
                total_tests += summary.get('total_tests', 0)
                total_passed += summary.get('passed', 0)
                total_failed += summary.get('failed', 0)
        
        return {
            'test_suite': 'AI Nutritionist E2E Tests',
            'environment': self.environment.environment,
            'execution_time': datetime.utcnow().isoformat(),
            'total_duration_seconds': duration,
            'total_duration_human': self._format_duration(duration),
            'overall_summary': {
                'total_tests': total_tests,
                'passed': total_passed,
                'failed': total_failed,
                'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0
            },
            'category_results': results,
            'recommendations': self._generate_recommendations(results),
            'next_actions': self._generate_next_actions(results)
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Analyze results and generate recommendations
        for category, category_results in results.items():
            if 'summary' in category_results:
                summary = category_results['summary']
                success_rate = summary.get('success_rate', 0)
                
                if success_rate < 80:
                    recommendations.append(
                        f"⚠️ {category.title()} tests have {success_rate:.1f}% success rate - needs attention"
                    )
                elif success_rate < 95:
                    recommendations.append(
                        f"⚡ {category.title()} tests could be improved (current: {success_rate:.1f}%)"
                    )
                else:
                    recommendations.append(
                        f"✅ {category.title()} tests performing well ({success_rate:.1f}%)"
                    )
        
        # Performance-specific recommendations
        if 'performance' in results:
            perf_results = results['performance']
            # Add performance analysis logic here
            
        return recommendations
    
    def _generate_next_actions(self, results: Dict[str, Any]) -> List[str]:
        """Generate next actions based on test results"""
        actions = []
        
        # Check for failures
        for category, category_results in results.items():
            if 'results' in category_results:
                failed_tests = [
                    r for r in category_results['results'] 
                    if r.get('status') == 'failed'
                ]
                
                if failed_tests:
                    actions.append(f"🔧 Fix {len(failed_tests)} failing tests in {category}")
        
        # Performance actions
        if 'performance' in results:
            actions.append("📊 Review performance metrics and optimize slow endpoints")
        
        # General actions
        actions.extend([
            "📈 Set up continuous E2E testing in CI/CD pipeline",
            "📱 Expand mobile device testing coverage",
            "🌐 Add cross-browser compatibility tests",
            "📋 Create automated test reporting dashboard"
        ])
        
        return actions
    
    async def _save_report(self, report: Dict[str, Any]) -> None:
        """Save test report to file"""
        timestamp = int(time.time())
        
        # Save JSON report
        json_file = f"e2e_test_report_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save HTML report
        html_file = f"e2e_test_report_{timestamp}.html"
        html_content = self._generate_html_report(report)
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"\n📊 Test reports saved:")
        print(f"   📄 JSON: {json_file}")
        print(f"   🌐 HTML: {html_file}")
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML test report"""
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Nutritionist E2E Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f8ff; padding: 20px; border-radius: 10px; }}
                .summary {{ background: #f9f9f9; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .success {{ color: #28a745; }}
                .warning {{ color: #ffc107; }}
                .error {{ color: #dc3545; }}
                .category {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .recommendations {{ background: #e8f5e8; padding: 15px; border-radius: 5px; }}
                .actions {{ background: #fff3cd; padding: 15px; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧠 AI Nutritionist E2E Test Report</h1>
                <p><strong>Environment:</strong> {report['environment']}</p>
                <p><strong>Execution Time:</strong> {report['execution_time']}</p>
                <p><strong>Duration:</strong> {report['total_duration_human']}</p>
            </div>
            
            <div class="summary">
                <h2>📊 Overall Summary</h2>
                <div class="metric">
                    <strong>Total Tests:</strong> {report['overall_summary']['total_tests']}
                </div>
                <div class="metric success">
                    <strong>Passed:</strong> {report['overall_summary']['passed']}
                </div>
                <div class="metric error">
                    <strong>Failed:</strong> {report['overall_summary']['failed']}
                </div>
                <div class="metric">
                    <strong>Success Rate:</strong> {report['overall_summary']['success_rate']:.1f}%
                </div>
            </div>
            
            <div class="recommendations">
                <h2>💡 Recommendations</h2>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in report['recommendations'])}
                </ul>
            </div>
            
            <div class="actions">
                <h2>🎯 Next Actions</h2>
                <ul>
                    {''.join(f'<li>{action}</li>' for action in report['next_actions'])}
                </ul>
            </div>
            
            <div>
                <h2>📋 Detailed Results</h2>
                {self._generate_category_html(report['category_results'])}
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_category_html(self, category_results: Dict[str, Any]) -> str:
        """Generate HTML for category results"""
        html = ""
        
        for category, results in category_results.items():
            if 'summary' in results:
                summary = results['summary']
                html += f"""
                <div class="category">
                    <h3>{category.title().replace('_', ' ')}</h3>
                    <p><strong>Tests:</strong> {summary.get('total_tests', 0)}</p>
                    <p><strong>Success Rate:</strong> {summary.get('success_rate', 0):.1f}%</p>
                    <p><strong>Duration:</strong> {summary.get('total_duration', 0):.1f}s</p>
                </div>
                """
        
        return html


def create_test_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Create test configuration from command line arguments"""
    return {
        'environment': args.environment,
        'run_user_journeys': args.user_journeys,
        'run_multi_channel': args.multi_channel,
        'run_performance': args.performance,
        'headless': args.headless,
        'parallel': args.parallel,
        'output_dir': args.output_dir
    }


def setup_directories(output_dir: str) -> None:
    """Setup test output directories"""
    dirs = [
        f"{output_dir}/screenshots",
        f"{output_dir}/logs",
        f"{output_dir}/reports",
        f"{output_dir}/artifacts"
    ]
    
    for directory in dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)


async def main():
    """Main entry point for E2E test execution"""
    parser = argparse.ArgumentParser(description='AI Nutritionist E2E Test Suite')
    
    parser.add_argument(
        '--environment', '-e',
        choices=['local', 'staging', 'production'],
        default='local',
        help='Test environment'
    )
    
    parser.add_argument(
        '--user-journeys',
        action='store_true',
        default=True,
        help='Run user journey tests'
    )
    
    parser.add_argument(
        '--multi-channel',
        action='store_true', 
        default=True,
        help='Run multi-channel tests'
    )
    
    parser.add_argument(
        '--performance',
        action='store_true',
        default=False,
        help='Run performance tests'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser tests in headless mode'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        default=False,
        help='Run tests in parallel'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='tests/e2e/output',
        help='Output directory for test results'
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_directories(args.output_dir)
    config = create_test_config(args)
    
    # Run tests
    test_suite = E2ETestSuite(config)
    report = await test_suite.run_all_tests()
    
    # Print summary
    print(f"\n🎉 E2E Test Suite Completed!")
    print(f"   ✅ Passed: {report['overall_summary']['passed']}")
    print(f"   ❌ Failed: {report['overall_summary']['failed']}")
    print(f"   📊 Success Rate: {report['overall_summary']['success_rate']:.1f}%")
    print(f"   ⏱️ Duration: {report['total_duration_human']}")
    
    # Exit with error code if tests failed
    if report['overall_summary']['failed'] > 0:
        exit(1)
    else:
        exit(0)


def run_with_pytest():
    """Run E2E tests using pytest"""
    pytest_args = [
        'tests/e2e/',
        '-v',
        '--tb=short',
        '--maxfail=5',
        f'--html=tests/e2e/output/pytest_report.html',
        '--self-contained-html'
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    asyncio.run(main())
