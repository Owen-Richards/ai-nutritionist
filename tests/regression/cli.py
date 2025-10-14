"""
Regression Testing CLI
Command-line interface for the regression testing framework
"""

import sys
import json
import argparse
import time
from pathlib import Path
from typing import Optional, List

from .framework import RegressionTestFramework, FrameworkMode
from .config import RegressionTestConfig
from .continuous import ContinuousTestingOrchestrator, PreCommitHook
from .maintenance import TestAnalytics, TestRefactoring, TestDataManager


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    
    parser = argparse.ArgumentParser(
        description="AI Nutritionist Regression Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run pre-commit tests
  python -m tests.regression.cli pre-commit
  
  # Run pull request tests
  python -m tests.regression.cli pull-request --max-duration 1800
  
  # Run nightly regression tests
  python -m tests.regression.cli nightly --output report.json
  
  # Detect flaky tests
  python -m tests.regression.cli flaky-detection --runs-per-test 10
  
  # Install git hooks
  python -m tests.regression.cli install-hooks
  
  # Analyze test metrics
  python -m tests.regression.cli analyze --top-flaky 10
        """
    )
    
    parser.add_argument(
        '--config', 
        type=Path,
        help='Path to regression test configuration file'
    )
    
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path.cwd(),
        help='Project root directory (default: current directory)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Pre-commit command
    pre_commit_parser = subparsers.add_parser(
        'pre-commit',
        help='Run pre-commit regression tests'
    )
    pre_commit_parser.add_argument(
        '--max-duration',
        type=int,
        default=300,
        help='Maximum duration in seconds (default: 300)'
    )
    pre_commit_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for results'
    )
    pre_commit_parser.set_defaults(func=run_pre_commit)
    
    # Pull request command
    pr_parser = subparsers.add_parser(
        'pull-request',
        help='Run pull request regression tests'  
    )
    pr_parser.add_argument(
        '--max-duration',
        type=int,
        default=1800,
        help='Maximum duration in seconds (default: 1800)'
    )
    pr_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for results'
    )
    pr_parser.set_defaults(func=run_pull_request)
    
    # Nightly command
    nightly_parser = subparsers.add_parser(
        'nightly',
        help='Run nightly regression tests'
    )
    nightly_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for results'
    )
    nightly_parser.set_defaults(func=run_nightly)
    
    # Release command
    release_parser = subparsers.add_parser(
        'release',
        help='Run release regression tests'
    )
    release_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for results'
    )
    release_parser.set_defaults(func=run_release)
    
    # Flaky detection command
    flaky_parser = subparsers.add_parser(
        'flaky-detection',
        help='Run flaky test detection'
    )
    flaky_parser.add_argument(
        '--runs-per-test',
        type=int,
        default=10,
        help='Number of runs per test (default: 10)'
    )
    flaky_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for results'
    )
    flaky_parser.set_defaults(func=run_flaky_detection)
    
    # Custom command
    custom_parser = subparsers.add_parser(
        'custom',
        help='Run custom test selection'
    )
    custom_parser.add_argument(
        'patterns',
        nargs='+',
        help='Test file patterns to run'
    )
    custom_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for results'
    )
    custom_parser.set_defaults(func=run_custom)
    
    # CI command
    ci_parser = subparsers.add_parser(
        'ci',
        help='Run CI-appropriate tests'
    )
    ci_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for results'
    )
    ci_parser.set_defaults(func=run_ci)
    
    # Install hooks command
    install_parser = subparsers.add_parser(
        'install-hooks',
        help='Install git hooks for continuous testing'
    )
    install_parser.set_defaults(func=install_hooks)
    
    # Setup CI command
    setup_ci_parser = subparsers.add_parser(
        'setup-ci',
        help='Setup CI/CD integration'
    )
    setup_ci_parser.add_argument(
        '--provider',
        choices=['github', 'jenkins', 'auto'],
        default='auto',
        help='CI provider to setup (default: auto-detect)'
    )
    setup_ci_parser.set_defaults(func=setup_ci)
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze test metrics and provide recommendations'
    )
    analyze_parser.add_argument(
        '--top-flaky',
        type=int,
        default=10,
        help='Number of top flaky tests to show (default: 10)'
    )
    analyze_parser.add_argument(
        '--top-slow',
        type=int,
        default=10,
        help='Number of slowest tests to show (default: 10)'
    )
    analyze_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for analysis results'
    )
    analyze_parser.set_defaults(func=analyze_tests)
    
    # Maintenance command
    maintenance_parser = subparsers.add_parser(
        'maintenance',
        help='Test maintenance and refactoring recommendations'
    )
    maintenance_parser.add_argument(
        '--check-duplicates',
        action='store_true',
        help='Check for duplicate tests'
    )
    maintenance_parser.add_argument(
        '--check-organization',
        action='store_true',
        help='Check test organization'
    )
    maintenance_parser.add_argument(
        '--check-fixtures',
        action='store_true',
        help='Check fixture usage'
    )
    maintenance_parser.add_argument(
        '--output',
        type=Path,
        help='Output file for maintenance results'
    )
    maintenance_parser.set_defaults(func=run_maintenance)
    
    return parser


def load_config(args) -> RegressionTestConfig:
    """Load configuration from args"""
    
    if args.config and args.config.exists():
        # Load from JSON config file
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        
        config = RegressionTestConfig(**config_data)
    else:
        # Use default config with overrides
        config = RegressionTestConfig.from_environment()
    
    # Override project root if specified
    if args.project_root:
        config.project_root = args.project_root
    
    # Override CI mode if in CI environment
    import os
    if os.getenv('CI') or os.getenv('GITHUB_ACTIONS') or os.getenv('JENKINS_URL'):
        config.ci_mode = True
    
    return config


def run_pre_commit(args) -> int:
    """Run pre-commit tests"""
    config = load_config(args)
    
    with RegressionTestFramework(config) as framework:
        result = framework.run_pre_commit_tests(args.max_duration)
        
        # Output results
        if args.output:
            save_result(result, args.output)
        
        print_result_summary(result)
        
        return 0 if result.success else 1


def run_pull_request(args) -> int:
    """Run pull request tests"""
    config = load_config(args)
    
    with RegressionTestFramework(config) as framework:
        result = framework.run_pull_request_tests(args.max_duration)
        
        if args.output:
            save_result(result, args.output)
        
        print_result_summary(result)
        
        return 0 if result.success else 1


def run_nightly(args) -> int:
    """Run nightly tests"""
    config = load_config(args)
    
    with RegressionTestFramework(config) as framework:
        result = framework.run_nightly_tests()
        
        if args.output:
            save_result(result, args.output)
        
        print_result_summary(result)
        
        return 0 if result.success else 1


def run_release(args) -> int:
    """Run release tests"""
    config = load_config(args)
    
    with RegressionTestFramework(config) as framework:
        result = framework.run_release_tests()
        
        if args.output:
            save_result(result, args.output)
        
        print_result_summary(result)
        
        return 0 if result.success else 1


def run_flaky_detection(args) -> int:
    """Run flaky test detection"""
    config = load_config(args)
    
    with RegressionTestFramework(config) as framework:
        result = framework.run_flaky_detection(args.runs_per_test)
        
        if args.output:
            save_result(result, args.output)
        
        print_result_summary(result)
        print_flaky_analysis(result)
        
        return 0 if result.success else 1


def run_custom(args) -> int:
    """Run custom test selection"""
    config = load_config(args)
    
    with RegressionTestFramework(config) as framework:
        result = framework.run_custom_tests(args.patterns)
        
        if args.output:
            save_result(result, args.output)
        
        print_result_summary(result)
        
        return 0 if result.success else 1


def run_ci(args) -> int:
    """Run CI-appropriate tests"""
    config = load_config(args)
    
    orchestrator = ContinuousTestingOrchestrator(config)
    result = orchestrator.run_ci_appropriate_tests()
    
    if args.output:
        save_result(result, args.output)
    
    print_result_summary(result)
    
    return 0 if result.success else 1


def install_hooks(args) -> int:
    """Install git hooks"""
    config = load_config(args)
    
    orchestrator = ContinuousTestingOrchestrator(config)
    orchestrator.install_hooks()
    
    return 0


def setup_ci(args) -> int:
    """Setup CI/CD integration"""
    config = load_config(args)
    
    orchestrator = ContinuousTestingOrchestrator(config)
    orchestrator.setup_ci_integration(args.provider)
    
    return 0


def analyze_tests(args) -> int:
    """Analyze test metrics"""
    config = load_config(args)
    
    analytics = TestAnalytics(config)
    
    print("🔍 Analyzing test metrics...")
    print()
    
    # Top flaky tests
    flaky_tests = analytics.get_top_flaky_tests(args.top_flaky)
    if flaky_tests:
        print(f"🔄 Top {len(flaky_tests)} Flaky Tests:")
        for i, test in enumerate(flaky_tests, 1):
            print(f"  {i}. {Path(test.test_path).name}")
            print(f"     Flakiness: {test.flakiness_score:.2f}, Success Rate: {test.success_rate:.1%}")
        print()
    
    # Slowest tests
    slow_tests = analytics.get_slowest_tests(args.top_slow)
    if slow_tests:
        print(f"🐌 Top {len(slow_tests)} Slowest Tests:")
        for i, test in enumerate(slow_tests, 1):
            print(f"  {i}. {Path(test.test_path).name}")
            print(f"     Average Duration: {test.avg_duration:.1f}s")
        print()
    
    # Maintenance recommendations
    recommendations = analytics.get_maintenance_recommendations()
    if recommendations:
        print(f"🔧 Maintenance Recommendations ({len(recommendations)}):")
        for rec in recommendations[:10]:  # Show top 10
            print(f"  • {rec.severity.upper()}: {rec.description}")
            print(f"    Action: {rec.recommended_action}")
        print()
    
    # Save analysis results
    if args.output:
        analysis_data = {
            "timestamp": time.time(),
            "flaky_tests": [
                {
                    "test_path": t.test_path,
                    "flakiness_score": t.flakiness_score,
                    "success_rate": t.success_rate,
                    "avg_duration": t.avg_duration
                }
                for t in flaky_tests
            ],
            "slow_tests": [
                {
                    "test_path": t.test_path,
                    "avg_duration": t.avg_duration,
                    "success_rate": t.success_rate
                }
                for t in slow_tests
            ],
            "recommendations": [
                {
                    "test_path": r.test_path,
                    "issue_type": r.issue_type,
                    "severity": r.severity,
                    "description": r.description,
                    "recommended_action": r.recommended_action
                }
                for r in recommendations
            ]
        }
        
        with open(args.output, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        print(f"📊 Analysis results saved to {args.output}")
    
    return 0


def run_maintenance(args) -> int:
    """Run test maintenance analysis"""
    config = load_config(args)
    
    refactoring = TestRefactoring(config)
    data_manager = TestDataManager(config)
    
    maintenance_results = {}
    
    if args.check_duplicates:
        print("🔍 Checking for duplicate tests...")
        duplicates = refactoring.identify_duplicate_tests()
        if duplicates:
            print(f"Found {len(duplicates)} groups of potentially duplicate tests:")
            for signature, tests in list(duplicates.items())[:5]:  # Show first 5
                print(f"  • {len(tests)} similar tests:")
                for test in tests:
                    print(f"    - {Path(test).name}")
        else:
            print("  ✅ No duplicate tests found")
        maintenance_results["duplicates"] = duplicates
        print()
    
    if args.check_organization:
        print("📁 Checking test organization...")
        suggestions = refactoring.suggest_test_organization()
        for category, tests in suggestions.items():
            if tests:
                print(f"  {category.replace('_', ' ').title()}: {len(tests)} tests")
        maintenance_results["organization"] = suggestions
        print()
    
    if args.check_fixtures:
        print("🧪 Checking test fixtures...")
        test_data = data_manager.audit_test_data()
        recommendations = data_manager.generate_fixture_recommendations()
        
        print(f"  Fixture files: {len(test_data.fixture_files)}")
        print(f"  Tests using mocks: {len(test_data.mock_objects)}")
        print(f"  Tests using databases: {len(test_data.test_databases)}")
        print(f"  Tests needing cleanup: {len(test_data.cleanup_needed)}")
        
        if recommendations:
            print("  Recommendations:")
            for rec in recommendations:
                print(f"    • {rec}")
        
        maintenance_results["fixtures"] = {
            "audit": test_data.__dict__,
            "recommendations": recommendations
        }
        print()
    
    # Save maintenance results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(maintenance_results, f, indent=2, default=str)
        
        print(f"🔧 Maintenance results saved to {args.output}")
    
    return 0


def save_result(result, output_path: Path):
    """Save test result to file"""
    
    result_data = {
        "execution_id": result.report.execution_id,
        "timestamp": result.report.timestamp.isoformat(),
        "mode": result.mode.value,
        "success": result.success,
        "duration": result.duration,
        "summary": {
            "total_tests": result.summary.total_tests,
            "passed": result.summary.passed,
            "failed": result.summary.failed,
            "skipped": result.summary.skipped,
            "errors": result.summary.errors,
            "success_rate": result.summary.success_rate,
            "total_duration": result.summary.total_duration
        },
        "selection": {
            "reason": result.selection.reason,
            "confidence": result.selection.confidence,
            "estimated_duration": result.selection.estimated_duration,
            "selected_count": len(result.selection.selected_tests)
        },
        "recommendations": result.recommendations
    }
    
    with open(output_path, 'w') as f:
        json.dump(result_data, f, indent=2)


def print_result_summary(result):
    """Print result summary to console"""
    
    status_emoji = "✅" if result.success else "❌"
    
    print()
    print(f"{status_emoji} {result.mode.value.upper()} REGRESSION TEST RESULTS")
    print("=" * 50)
    print(f"Success: {'YES' if result.success else 'NO'}")
    print(f"Duration: {result.duration:.1f}s")
    print(f"Tests: {result.summary.total_tests}")
    print(f"Passed: {result.summary.passed}")
    print(f"Failed: {result.summary.failed}")
    print(f"Success Rate: {result.summary.success_rate:.1%}")
    
    if result.recommendations:
        print()
        print("💡 Recommendations:")
        for rec in result.recommendations:
            print(f"  • {rec}")
    
    print()


def print_flaky_analysis(result):
    """Print flaky test analysis"""
    
    if result.mode == FrameworkMode.FLAKY_DETECTION:
        print("🔄 Flaky Test Analysis:")
        print(f"  Tests analyzed: {result.summary.total_tests}")
        print(f"  Stable tests: {result.summary.passed}")
        print(f"  Flaky tests: {result.summary.flaky}")
        print(f"  Unstable tests: {result.summary.failed}")
        print()


if __name__ == '__main__':
    sys.exit(main())
