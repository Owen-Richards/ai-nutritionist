#!/usr/bin/env python3
"""
Test report generator for CI/CD pipeline.
Combines multiple test result files into a comprehensive report.
"""

import xml.etree.ElementTree as ET
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def parse_junit_xml(file_path: str) -> Dict[str, Any]:
    """Parse JUnit XML test results."""
    if not Path(file_path).exists():
        return {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0, 'time': 0}
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Handle both testsuite and testsuites root elements
        if root.tag == 'testsuites':
            testsuite = root.find('testsuite')
            if testsuite is not None:
                root = testsuite
        
        return {
            'tests': int(root.get('tests', 0)),
            'failures': int(root.get('failures', 0)),
            'errors': int(root.get('errors', 0)),
            'skipped': int(root.get('skipped', 0)),
            'time': float(root.get('time', 0))
        }
    except Exception as e:
        print(f"⚠️ Error parsing {file_path}: {e}")
        return {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0, 'time': 0}


def generate_html_report(
    unit_results: Dict[str, Any],
    integration_results: Dict[str, Any],
    e2e_results: Dict[str, Any],
    regression_results: Dict[str, Any],
    output_file: str
):
    """Generate comprehensive HTML test report."""
    
    total_tests = (unit_results['tests'] + integration_results['tests'] + 
                   e2e_results['tests'] + regression_results['tests'])
    total_failures = (unit_results['failures'] + integration_results['failures'] + 
                     e2e_results['failures'] + regression_results['failures'])
    total_errors = (unit_results['errors'] + integration_results['errors'] + 
                   e2e_results['errors'] + regression_results['errors'])
    total_time = (unit_results['time'] + integration_results['time'] + 
                 e2e_results['time'] + regression_results['time'])
    
    success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Nutritionist - Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary {{ display: flex; gap: 20px; margin-bottom: 30px; }}
        .metric {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
        .metric h3 {{ margin: 0; color: #333; }}
        .metric .value {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        .test-section {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .test-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .test-category {{ padding: 15px; border-radius: 8px; }}
        .category-unit {{ background: #e3f2fd; }}
        .category-integration {{ background: #f3e5f5; }}
        .category-e2e {{ background: #e8f5e8; }}
        .category-regression {{ background: #fff3e0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 AI Nutritionist Test Report</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <div class="value">{total_tests}</div>
        </div>
        <div class="metric">
            <h3>Success Rate</h3>
            <div class="value {'success' if success_rate >= 90 else 'warning' if success_rate >= 75 else 'danger'}">{success_rate:.1f}%</div>
        </div>
        <div class="metric">
            <h3>Total Time</h3>
            <div class="value">{total_time:.1f}s</div>
        </div>
        <div class="metric">
            <h3>Status</h3>
            <div class="value {'success' if total_failures + total_errors == 0 else 'danger'}">
                {'✅ PASS' if total_failures + total_errors == 0 else '❌ FAIL'}
            </div>
        </div>
    </div>
    
    <div class="test-section">
        <h2>📊 Test Categories</h2>
        <div class="test-grid">
            <div class="test-category category-unit">
                <h3>🔬 Unit Tests</h3>
                <p><strong>Tests:</strong> {unit_results['tests']}</p>
                <p><strong>Failures:</strong> {unit_results['failures']}</p>
                <p><strong>Errors:</strong> {unit_results['errors']}</p>
                <p><strong>Time:</strong> {unit_results['time']:.2f}s</p>
            </div>
            <div class="test-category category-integration">
                <h3>🔗 Integration Tests</h3>
                <p><strong>Tests:</strong> {integration_results['tests']}</p>
                <p><strong>Failures:</strong> {integration_results['failures']}</p>
                <p><strong>Errors:</strong> {integration_results['errors']}</p>
                <p><strong>Time:</strong> {integration_results['time']:.2f}s</p>
            </div>
            <div class="test-category category-e2e">
                <h3>🎯 End-to-End Tests</h3>
                <p><strong>Tests:</strong> {e2e_results['tests']}</p>
                <p><strong>Failures:</strong> {e2e_results['failures']}</p>
                <p><strong>Errors:</strong> {e2e_results['errors']}</p>
                <p><strong>Time:</strong> {e2e_results['time']:.2f}s</p>
            </div>
            <div class="test-category category-regression">
                <h3>🔄 Regression Tests</h3>
                <p><strong>Tests:</strong> {regression_results['tests']}</p>
                <p><strong>Failures:</strong> {regression_results['failures']}</p>
                <p><strong>Errors:</strong> {regression_results['errors']}</p>
                <p><strong>Time:</strong> {regression_results['time']:.2f}s</p>
            </div>
        </div>
    </div>
    
    <div class="test-section">
        <h2>📈 Recommendations</h2>
        <ul>
    """
    
    if success_rate < 80:
        html_content += "<li>🔴 Critical: Test success rate is below 80%. Immediate attention required.</li>"
    elif success_rate < 90:
        html_content += "<li>🟡 Warning: Test success rate is below 90%. Consider improving test stability.</li>"
    else:
        html_content += "<li>✅ Excellent: Test success rate is above 90%.</li>"
    
    if total_time > 300:  # 5 minutes
        html_content += "<li>⏰ Consider optimizing test execution time (current: {:.1f}s).</li>".format(total_time)
    
    if unit_results['tests'] == 0:
        html_content += "<li>⚠️ No unit tests found. Consider adding unit test coverage.</li>"
    
    html_content += """
        </ul>
    </div>
</body>
</html>
    """
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Test report generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate comprehensive test report')
    parser.add_argument('--unit-results', help='Unit test results XML file')
    parser.add_argument('--integration-results', help='Integration test results XML file')
    parser.add_argument('--e2e-results', help='E2E test results XML file')
    parser.add_argument('--regression-results', help='Regression test results XML file')
    parser.add_argument('--output', required=True, help='Output HTML file')
    
    args = parser.parse_args()
    
    # Parse test results
    unit_results = parse_junit_xml(args.unit_results) if args.unit_results else {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0, 'time': 0}
    integration_results = parse_junit_xml(args.integration_results) if args.integration_results else {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0, 'time': 0}
    e2e_results = parse_junit_xml(args.e2e_results) if args.e2e_results else {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0, 'time': 0}
    regression_results = parse_junit_xml(args.regression_results) if args.regression_results else {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0, 'time': 0}
    
    # Generate HTML report
    generate_html_report(
        unit_results,
        integration_results,
        e2e_results,
        regression_results,
        args.output
    )


if __name__ == '__main__':
    main()
