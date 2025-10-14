#!/usr/bin/env python3
"""
Comprehensive security report generator for CI/CD pipeline.
Aggregates security scan results and generates dashboard.
"""

import json
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def load_json_report(file_path: str) -> Dict[str, Any]:
    """Load JSON report file."""
    if not Path(file_path).exists():
        return {}
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def analyze_dependency_security(dependency_dir: str) -> Dict[str, Any]:
    """Analyze dependency security scan results."""
    safety_report = load_json_report(os.path.join(dependency_dir, 'safety-report.json'))
    pip_audit_report = load_json_report(os.path.join(dependency_dir, 'pip-audit-report.json'))
    yarn_audit_report = load_json_report(os.path.join(dependency_dir, 'yarn-audit-report.json'))
    
    issues = []
    
    # Process Safety report
    if safety_report and 'vulnerabilities' in safety_report:
        for vuln in safety_report['vulnerabilities']:
            issues.append({
                'type': 'dependency',
                'severity': vuln.get('severity', 'unknown').lower(),
                'package': vuln.get('package_name', 'unknown'),
                'vulnerability': vuln.get('vulnerability_id', 'unknown'),
                'description': vuln.get('advisory', 'No description'),
                'source': 'safety'
            })
    
    # Process pip-audit report
    if pip_audit_report and 'vulnerabilities' in pip_audit_report:
        for vuln in pip_audit_report['vulnerabilities']:
            issues.append({
                'type': 'dependency',
                'severity': vuln.get('severity', 'unknown').lower(),
                'package': vuln.get('package', 'unknown'),
                'vulnerability': vuln.get('id', 'unknown'),
                'description': vuln.get('description', 'No description'),
                'source': 'pip-audit'
            })
    
    # Process Yarn audit report
    if yarn_audit_report and 'advisories' in yarn_audit_report:
        for advisory_id, advisory in yarn_audit_report['advisories'].items():
            issues.append({
                'type': 'dependency',
                'severity': advisory.get('severity', 'unknown').lower(),
                'package': advisory.get('module_name', 'unknown'),
                'vulnerability': advisory_id,
                'description': advisory.get('title', 'No description'),
                'source': 'yarn-audit'
            })
    
    return {
        'total_issues': len(issues),
        'issues': issues,
        'severity_counts': count_by_severity(issues)
    }


def analyze_code_security(code_dir: str) -> Dict[str, Any]:
    """Analyze code security scan results."""
    bandit_report = load_json_report(os.path.join(code_dir, 'bandit-report.json'))
    eslint_report = load_json_report(os.path.join(code_dir, 'eslint-security-report.json'))
    
    issues = []
    
    # Process Bandit report
    if bandit_report and 'results' in bandit_report:
        for result in bandit_report['results']:
            issues.append({
                'type': 'code',
                'severity': result.get('issue_severity', 'unknown').lower(),
                'file': result.get('filename', 'unknown'),
                'line': result.get('line_number', 0),
                'test': result.get('test_name', 'unknown'),
                'description': result.get('issue_text', 'No description'),
                'source': 'bandit'
            })
    
    # Process ESLint security report
    if isinstance(eslint_report, list):
        for file_result in eslint_report:
            for message in file_result.get('messages', []):
                if message.get('ruleId', '').startswith('security/'):
                    severity = 'high' if message.get('severity') == 2 else 'medium'
                    issues.append({
                        'type': 'code',
                        'severity': severity,
                        'file': file_result.get('filePath', 'unknown'),
                        'line': message.get('line', 0),
                        'rule': message.get('ruleId', 'unknown'),
                        'description': message.get('message', 'No description'),
                        'source': 'eslint-security'
                    })
    
    return {
        'total_issues': len(issues),
        'issues': issues,
        'severity_counts': count_by_severity(issues)
    }


def analyze_container_security(container_dir: str) -> Dict[str, Any]:
    """Analyze container security scan results."""
    trivy_report = load_json_report(os.path.join(container_dir, 'trivy-container-report.json'))
    hadolint_report = load_json_report(os.path.join(container_dir, 'hadolint-report.json'))
    
    issues = []
    
    # Process Trivy report
    if trivy_report and 'Results' in trivy_report:
        for result in trivy_report['Results']:
            vulnerabilities = result.get('Vulnerabilities', [])
            for vuln in vulnerabilities:
                issues.append({
                    'type': 'container',
                    'severity': vuln.get('Severity', 'unknown').lower(),
                    'package': vuln.get('PkgName', 'unknown'),
                    'vulnerability': vuln.get('VulnerabilityID', 'unknown'),
                    'description': vuln.get('Title', 'No description'),
                    'source': 'trivy'
                })
    
    # Process Hadolint report
    if isinstance(hadolint_report, list):
        for issue in hadolint_report:
            severity_map = {'error': 'high', 'warning': 'medium', 'info': 'low'}
            severity = severity_map.get(issue.get('level', 'info'), 'low')
            
            issues.append({
                'type': 'container',
                'severity': severity,
                'file': 'Dockerfile',
                'line': issue.get('line', 0),
                'rule': issue.get('code', 'unknown'),
                'description': issue.get('message', 'No description'),
                'source': 'hadolint'
            })
    
    return {
        'total_issues': len(issues),
        'issues': issues,
        'severity_counts': count_by_severity(issues)
    }


def count_by_severity(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count issues by severity level."""
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    
    for issue in issues:
        severity = issue.get('severity', 'low')
        if severity in severity_counts:
            severity_counts[severity] += 1
        else:
            severity_counts['low'] += 1
    
    return severity_counts


def generate_security_dashboard(
    dependency_analysis: Dict[str, Any],
    code_analysis: Dict[str, Any],
    container_analysis: Dict[str, Any],
    infrastructure_analysis: Dict[str, Any],
    compliance_analysis: Dict[str, Any],
    output_file: str
):
    """Generate comprehensive security dashboard HTML."""
    
    total_issues = (dependency_analysis['total_issues'] + 
                   code_analysis['total_issues'] + 
                   container_analysis['total_issues'])
    
    # Aggregate severity counts
    total_severity = {
        'critical': (dependency_analysis['severity_counts']['critical'] + 
                    code_analysis['severity_counts']['critical'] + 
                    container_analysis['severity_counts']['critical']),
        'high': (dependency_analysis['severity_counts']['high'] + 
                code_analysis['severity_counts']['high'] + 
                container_analysis['severity_counts']['high']),
        'medium': (dependency_analysis['severity_counts']['medium'] + 
                  code_analysis['severity_counts']['medium'] + 
                  container_analysis['severity_counts']['medium']),
        'low': (dependency_analysis['severity_counts']['low'] + 
               code_analysis['severity_counts']['low'] + 
               container_analysis['severity_counts']['low'])
    }
    
    # Determine overall security status
    if total_severity['critical'] > 0:
        security_status = "🔴 CRITICAL"
        status_class = "danger"
    elif total_severity['high'] > 0:
        security_status = "🟠 HIGH RISK"
        status_class = "warning"
    elif total_severity['medium'] > 5:
        security_status = "🟡 MEDIUM RISK"
        status_class = "warning"
    else:
        security_status = "🟢 SECURE"
        status_class = "success"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Nutritionist - Security Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }}
        .header {{ background: #fff; padding: 30px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .status-badge {{ display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; }}
        .success {{ background: #d4edda; color: #155724; }}
        .warning {{ background: #fff3cd; color: #856404; }}
        .danger {{ background: #f8d7da; color: #721c24; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric {{ background: #fff; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .metric h3 {{ margin: 0 0 10px 0; color: #333; }}
        .metric .value {{ font-size: 2.5em; font-weight: bold; margin: 15px 0; }}
        .critical {{ color: #dc3545; }}
        .high {{ color: #fd7e14; }}
        .medium {{ color: #ffc107; }}
        .low {{ color: #20c997; }}
        .security-section {{ background: #fff; padding: 25px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .scan-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .scan-category {{ padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; }}
        .issue-list {{ max-height: 300px; overflow-y: auto; }}
        .issue {{ padding: 10px; margin: 5px 0; border-radius: 6px; border-left: 4px solid; }}
        .issue-critical {{ background: #f8d7da; border-color: #dc3545; }}
        .issue-high {{ background: #fff3cd; border-color: #fd7e14; }}
        .issue-medium {{ background: #fff3cd; border-color: #ffc107; }}
        .issue-low {{ background: #d1ecf1; border-color: #20c997; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ AI Nutritionist Security Dashboard</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <div class="status-badge {status_class}">{security_status}</div>
    </div>
    
    <div class="metrics">
        <div class="metric">
            <h3>Total Issues</h3>
            <div class="value">{total_issues}</div>
        </div>
        <div class="metric">
            <h3>Critical</h3>
            <div class="value critical">{total_severity['critical']}</div>
        </div>
        <div class="metric">
            <h3>High</h3>
            <div class="value high">{total_severity['high']}</div>
        </div>
        <div class="metric">
            <h3>Medium</h3>
            <div class="value medium">{total_severity['medium']}</div>
        </div>
        <div class="metric">
            <h3>Low</h3>
            <div class="value low">{total_severity['low']}</div>
        </div>
    </div>
    
    <div class="security-section">
        <h2>📊 Security Scan Results</h2>
        <div class="scan-grid">
            <div class="scan-category">
                <h3>🔗 Dependencies</h3>
                <p><strong>Issues:</strong> {dependency_analysis['total_issues']}</p>
                <p><strong>Critical:</strong> {dependency_analysis['severity_counts']['critical']}</p>
                <p><strong>High:</strong> {dependency_analysis['severity_counts']['high']}</p>
                <p><strong>Medium:</strong> {dependency_analysis['severity_counts']['medium']}</p>
            </div>
            <div class="scan-category">
                <h3>💻 Code Analysis</h3>
                <p><strong>Issues:</strong> {code_analysis['total_issues']}</p>
                <p><strong>Critical:</strong> {code_analysis['severity_counts']['critical']}</p>
                <p><strong>High:</strong> {code_analysis['severity_counts']['high']}</p>
                <p><strong>Medium:</strong> {code_analysis['severity_counts']['medium']}</p>
            </div>
            <div class="scan-category">
                <h3>🐳 Container Security</h3>
                <p><strong>Issues:</strong> {container_analysis['total_issues']}</p>
                <p><strong>Critical:</strong> {container_analysis['severity_counts']['critical']}</p>
                <p><strong>High:</strong> {container_analysis['severity_counts']['high']}</p>
                <p><strong>Medium:</strong> {container_analysis['severity_counts']['medium']}</p>
            </div>
        </div>
    </div>
    
    <div class="security-section">
        <h2>🎯 Action Items</h2>
        <ul>
    """
    
    if total_severity['critical'] > 0:
        html_content += f"<li>🔴 <strong>URGENT:</strong> Address {total_severity['critical']} critical security issue(s) immediately.</li>"
    
    if total_severity['high'] > 0:
        html_content += f"<li>🟠 <strong>HIGH PRIORITY:</strong> Fix {total_severity['high']} high-severity issue(s) within 24 hours.</li>"
    
    if total_severity['medium'] > 5:
        html_content += f"<li>🟡 <strong>MODERATE:</strong> Plan to address {total_severity['medium']} medium-severity issues.</li>"
    
    if total_issues == 0:
        html_content += "<li>✅ <strong>EXCELLENT:</strong> No security issues detected. Continue monitoring.</li>"
    
    html_content += """
        </ul>
    </div>
    
    <div class="security-section">
        <h2>📋 Recommendations</h2>
        <ul>
            <li>🔄 Run security scans regularly (daily recommended)</li>
            <li>📦 Keep dependencies updated to latest secure versions</li>
            <li>🔒 Implement security headers and HTTPS everywhere</li>
            <li>👥 Conduct regular security code reviews</li>
            <li>🎯 Follow OWASP security guidelines</li>
            <li>📊 Monitor security metrics and trends</li>
        </ul>
    </div>
</body>
</html>
    """
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Security dashboard generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate comprehensive security report')
    parser.add_argument('--dependency-results', help='Dependency scan results directory')
    parser.add_argument('--code-results', help='Code security results directory')
    parser.add_argument('--container-results', help='Container security results directory')
    parser.add_argument('--infrastructure-results', help='Infrastructure security results directory')
    parser.add_argument('--compliance-results', help='Compliance results directory')
    parser.add_argument('--output', required=True, help='Output HTML file')
    
    args = parser.parse_args()
    
    # Analyze each category
    dependency_analysis = analyze_dependency_security(args.dependency_results or '')
    code_analysis = analyze_code_security(args.code_results or '')
    container_analysis = analyze_container_security(args.container_results or '')
    infrastructure_analysis = {'total_issues': 0, 'issues': [], 'severity_counts': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}}
    compliance_analysis = {'total_issues': 0, 'issues': [], 'severity_counts': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}}
    
    # Generate security metrics
    total_critical = (dependency_analysis['severity_counts']['critical'] + 
                     code_analysis['severity_counts']['critical'] + 
                     container_analysis['severity_counts']['critical'])
    
    total_high = (dependency_analysis['severity_counts']['high'] + 
                 code_analysis['severity_counts']['high'] + 
                 container_analysis['severity_counts']['high'])
    
    total_medium = (dependency_analysis['severity_counts']['medium'] + 
                   code_analysis['severity_counts']['medium'] + 
                   container_analysis['severity_counts']['medium'])
    
    total_low = (dependency_analysis['severity_counts']['low'] + 
                code_analysis['severity_counts']['low'] + 
                container_analysis['severity_counts']['low'])
    
    metrics = {
        'critical': total_critical,
        'high': total_high,
        'medium': total_medium,
        'low': total_low,
        'total': total_critical + total_high + total_medium + total_low,
        'scan_timestamp': datetime.now().isoformat(),
        'categories': {
            'dependencies': dependency_analysis['severity_counts'],
            'code': code_analysis['severity_counts'],
            'container': container_analysis['severity_counts']
        }
    }
    
    # Save metrics
    metrics_file = 'security-metrics.json'
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    # Generate dashboard
    generate_security_dashboard(
        dependency_analysis,
        code_analysis,
        container_analysis,
        infrastructure_analysis,
        compliance_analysis,
        args.output
    )


if __name__ == '__main__':
    main()
