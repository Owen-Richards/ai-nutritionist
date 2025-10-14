"""
Security Automation Suite

Automated security testing, secret scanning, and CI/CD security gates
for the AI Nutritionist application.
"""

import os
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pytest
import requests
import yaml


class SecurityAutomation:
    """Comprehensive security automation toolkit."""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or ".")
        self.results_dir = Path("tests/security/reports/automation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Common secret patterns
        self.secret_patterns = {
            "aws_access_key": r"AKIA[0-9A-Z]{16}",
            "aws_secret_key": r"[0-9a-zA-Z/+=]{40}",
            "github_token": r"ghp_[0-9a-zA-Z]{36}",
            "jwt_token": r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",
            "api_key": r"[aA][pP][iI]_?[kK][eE][yY].*['\"][0-9a-zA-Z]{32,45}['\"]",
            "private_key": r"-----BEGIN PRIVATE KEY-----",
            "database_url": r"(mongodb|mysql|postgresql)://[^\s]+",
            "email_password": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^\s]+",
            "slack_token": r"xox[baprs]-([0-9a-zA-Z]{10,48})?",
            "stripe_key": r"sk_live_[0-9a-zA-Z]{24}",
            "twilio_auth": r"SK[a-z0-9]{32}",
            "openai_key": r"sk-[a-zA-Z0-9]{48}"
        }
    
    def scan_secrets(self) -> Dict[str, Any]:
        """Scan for hardcoded secrets in codebase."""
        results = {
            "scan_type": "secret_scanning",
            "timestamp": datetime.utcnow().isoformat(),
            "files_scanned": 0,
            "secrets_found": [],
            "status": "clean"
        }
        
        # File patterns to scan
        scan_patterns = [
            "**/*.py", "**/*.js", "**/*.ts", "**/*.yaml", "**/*.yml",
            "**/*.json", "**/*.env", "**/*.config", "**/*.ini",
            "**/*.tf", "**/*.tfvars", "**/*.sh", "**/*.bat"
        ]
        
        # Files to exclude
        exclude_patterns = [
            "**/node_modules/**", "**/.git/**", "**/venv/**", "**/__pycache__/**",
            "**/dist/**", "**/build/**", "**/target/**", "**/.pytest_cache/**",
            "**/test_*", "**/tests/**", "**/spec/**"
        ]
        
        files_to_scan = []
        for pattern in scan_patterns:
            files_to_scan.extend(self.project_root.glob(pattern))
        
        # Filter out exclusions
        filtered_files = []
        for file_path in files_to_scan:
            if not any(file_path.match(exclude) for exclude in exclude_patterns):
                filtered_files.append(file_path)
        
        results["files_scanned"] = len(filtered_files)
        
        for file_path in filtered_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Scan for each secret pattern
                    for secret_type, pattern in self.secret_patterns.items():
                        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                        
                        for match in matches:
                            # Get line number
                            line_number = content[:match.start()].count('\n') + 1
                            
                            # Get surrounding context
                            lines = content.split('\n')
                            start_line = max(0, line_number - 3)
                            end_line = min(len(lines), line_number + 2)
                            context = '\n'.join(lines[start_line:end_line])
                            
                            secret_finding = {
                                "type": secret_type,
                                "file": str(file_path.relative_to(self.project_root)),
                                "line": line_number,
                                "match": match.group()[:50] + "..." if len(match.group()) > 50 else match.group(),
                                "context": context,
                                "severity": self._get_secret_severity(secret_type),
                                "confidence": self._calculate_confidence(match.group(), secret_type)
                            }
                            
                            results["secrets_found"].append(secret_finding)
                            results["status"] = "secrets_detected"
                            
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return results
    
    def _get_secret_severity(self, secret_type: str) -> str:
        """Get severity level for secret type."""
        high_severity = ["aws_access_key", "aws_secret_key", "private_key", "database_url", "stripe_key"]
        medium_severity = ["github_token", "api_key", "slack_token", "twilio_auth", "openai_key"]
        
        if secret_type in high_severity:
            return "HIGH"
        elif secret_type in medium_severity:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_confidence(self, match: str, secret_type: str) -> str:
        """Calculate confidence level for secret detection."""
        # Simple heuristics for confidence
        if secret_type in ["aws_access_key", "github_token"] and len(match) == 36:
            return "HIGH"
        elif secret_type == "private_key" and "BEGIN PRIVATE KEY" in match:
            return "HIGH"
        elif len(match) > 32 and any(c.isdigit() for c in match) and any(c.isalpha() for c in match):
            return "MEDIUM"
        else:
            return "LOW"
    
    def run_security_linting(self) -> Dict[str, Any]:
        """Run security-focused linting tools."""
        results = {
            "scan_type": "security_linting",
            "timestamp": datetime.utcnow().isoformat(),
            "tools": {},
            "total_issues": 0,
            "status": "clean"
        }
        
        # Run Bandit for Python security issues
        bandit_results = self._run_bandit()
        results["tools"]["bandit"] = bandit_results
        results["total_issues"] += bandit_results.get("issue_count", 0)
        
        # Run ESLint security plugin for JavaScript/TypeScript
        eslint_results = self._run_eslint_security()
        results["tools"]["eslint_security"] = eslint_results
        results["total_issues"] += eslint_results.get("issue_count", 0)
        
        # Run custom security checks
        custom_results = self._run_custom_security_checks()
        results["tools"]["custom_checks"] = custom_results
        results["total_issues"] += custom_results.get("issue_count", 0)
        
        if results["total_issues"] > 0:
            results["status"] = "issues_found"
        
        return results
    
    def _run_bandit(self) -> Dict[str, Any]:
        """Run Bandit security linter for Python."""
        try:
            result = subprocess.run([
                "python", "-m", "bandit",
                "-r", str(self.project_root / "src"),
                "-f", "json"
            ], capture_output=True, text=True, timeout=300)
            
            if result.stdout:
                bandit_data = json.loads(result.stdout)
                issues = bandit_data.get("results", [])
                
                return {
                    "tool": "bandit",
                    "status": "completed",
                    "issue_count": len(issues),
                    "issues": issues,
                    "metrics": bandit_data.get("metrics", {})
                }
            else:
                return {
                    "tool": "bandit",
                    "status": "no_issues",
                    "issue_count": 0
                }
                
        except Exception as e:
            return {
                "tool": "bandit",
                "status": "error",
                "error": str(e),
                "issue_count": 0
            }
    
    def _run_eslint_security(self) -> Dict[str, Any]:
        """Run ESLint with security plugin."""
        try:
            # Check if eslint and security plugin are available
            package_json_path = self.project_root / "package.json"
            if not package_json_path.exists():
                return {
                    "tool": "eslint_security",
                    "status": "not_applicable",
                    "issue_count": 0
                }
            
            result = subprocess.run([
                "npx", "eslint",
                "--ext", ".js,.ts,.jsx,.tsx",
                str(self.project_root / "src"),
                "--format", "json"
            ], capture_output=True, text=True, timeout=300)
            
            if result.stdout:
                eslint_data = json.loads(result.stdout)
                
                # Filter for security-related issues
                security_issues = []
                for file_result in eslint_data:
                    for message in file_result.get("messages", []):
                        rule_id = message.get("ruleId", "")
                        if any(keyword in rule_id.lower() for keyword in 
                               ["security", "xss", "injection", "csrf", "auth"]):
                            security_issues.append({
                                "file": file_result["filePath"],
                                "line": message["line"],
                                "column": message["column"],
                                "message": message["message"],
                                "rule": rule_id,
                                "severity": message["severity"]
                            })
                
                return {
                    "tool": "eslint_security",
                    "status": "completed",
                    "issue_count": len(security_issues),
                    "issues": security_issues
                }
            else:
                return {
                    "tool": "eslint_security",
                    "status": "no_issues",
                    "issue_count": 0
                }
                
        except Exception as e:
            return {
                "tool": "eslint_security",
                "status": "error",
                "error": str(e),
                "issue_count": 0
            }
    
    def _run_custom_security_checks(self) -> Dict[str, Any]:
        """Run custom security checks."""
        issues = []
        
        try:
            # Check 1: Debug mode in production
            config_files = list(self.project_root.glob("**/settings.py")) + \
                          list(self.project_root.glob("**/config.py")) + \
                          list(self.project_root.glob("**/.env*"))
            
            for config_file in config_files:
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                        if re.search(r"DEBUG\s*=\s*True", content, re.IGNORECASE):
                            issues.append({
                                "type": "debug_mode_enabled",
                                "file": str(config_file.relative_to(self.project_root)),
                                "description": "Debug mode enabled in configuration",
                                "severity": "HIGH"
                            })
                except:
                    continue
            
            # Check 2: Insecure random number generation
            python_files = list(self.project_root.glob("**/*.py"))
            for py_file in python_files[:50]:  # Limit to avoid timeout
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        if re.search(r"import random\b", content) and \
                           re.search(r"random\.(random|randint|choice)", content):
                            issues.append({
                                "type": "insecure_random",
                                "file": str(py_file.relative_to(self.project_root)),
                                "description": "Using insecure random number generation",
                                "severity": "MEDIUM"
                            })
                except:
                    continue
            
            # Check 3: SQL injection patterns
            for py_file in python_files[:50]:
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        # Look for string formatting in SQL-like contexts
                        if re.search(r"(SELECT|INSERT|UPDATE|DELETE).*%[sd]", content, re.IGNORECASE):
                            issues.append({
                                "type": "potential_sql_injection",
                                "file": str(py_file.relative_to(self.project_root)),
                                "description": "Potential SQL injection via string formatting",
                                "severity": "HIGH"
                            })
                except:
                    continue
            
            # Check 4: Hardcoded passwords
            for py_file in python_files[:50]:
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                        if re.search(r"password\s*=\s*['\"][^'\"]+['\"]", content, re.IGNORECASE):
                            issues.append({
                                "type": "hardcoded_password",
                                "file": str(py_file.relative_to(self.project_root)),
                                "description": "Potential hardcoded password",
                                "severity": "HIGH"
                            })
                except:
                    continue
            
            return {
                "tool": "custom_security_checks",
                "status": "completed",
                "issue_count": len(issues),
                "issues": issues
            }
            
        except Exception as e:
            return {
                "tool": "custom_security_checks",
                "status": "error",
                "error": str(e),
                "issue_count": 0
            }
    
    def create_security_pipeline(self) -> Dict[str, Any]:
        """Create security pipeline configuration for CI/CD."""
        pipeline_config = {
            "name": "Security Pipeline",
            "description": "Automated security testing pipeline",
            "stages": [
                {
                    "name": "Secret Scanning",
                    "commands": [
                        "python -m pytest tests/security/automation/test_security_automation.py::TestSecurityAutomation::test_secret_scanning -v"
                    ],
                    "fail_on_error": True
                },
                {
                    "name": "Dependency Vulnerability Scan",
                    "commands": [
                        "python -m safety check --json",
                        "python -m pytest tests/security/vulnerability_scanning/test_dependency_vulnerabilities.py -v"
                    ],
                    "fail_on_error": True
                },
                {
                    "name": "Static Code Analysis",
                    "commands": [
                        "python -m bandit -r src/ -f json",
                        "python -m pytest tests/security/automation/test_security_automation.py::TestSecurityAutomation::test_security_linting -v"
                    ],
                    "fail_on_error": False  # Warnings, not failures
                },
                {
                    "name": "OWASP ZAP Scan",
                    "commands": [
                        "python -m pytest tests/security/vulnerability_scanning/test_owasp_zap_scanning.py::TestMockZAPScanning -v"
                    ],
                    "fail_on_error": True
                },
                {
                    "name": "Compliance Testing",
                    "commands": [
                        "python -m pytest tests/security/compliance/ -v"
                    ],
                    "fail_on_error": True
                }
            ],
            "security_gates": {
                "critical_vulnerabilities": 0,
                "high_vulnerabilities": 3,
                "secrets_found": 0,
                "compliance_violations": 0
            }
        }
        
        # Generate GitHub Actions workflow
        github_workflow = self._generate_github_actions_workflow(pipeline_config)
        
        # Generate GitLab CI configuration
        gitlab_ci = self._generate_gitlab_ci_config(pipeline_config)
        
        # Save configurations
        workflows_dir = self.project_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        with open(workflows_dir / "security.yml", 'w') as f:
            f.write(github_workflow)
        
        with open(self.project_root / ".gitlab-ci-security.yml", 'w') as f:
            f.write(gitlab_ci)
        
        return {
            "pipeline_config": pipeline_config,
            "github_workflow_path": str(workflows_dir / "security.yml"),
            "gitlab_ci_path": str(self.project_root / ".gitlab-ci-security.yml"),
            "status": "created"
        }
    
    def _generate_github_actions_workflow(self, config: Dict[str, Any]) -> str:
        """Generate GitHub Actions workflow for security testing."""
        workflow = f"""name: {config['name']}

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
"""
        
        for stage in config['stages']:
            workflow += f"""    - name: {stage['name']}
      run: |
"""
            for command in stage['commands']:
                workflow += f"        {command}\n"
            
            if stage.get('fail_on_error', True):
                workflow += "      continue-on-error: false\n"
            else:
                workflow += "      continue-on-error: true\n"
            workflow += "\n"
        
        workflow += """    - name: Upload Security Reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: security-reports
        path: tests/security/reports/
"""
        
        return workflow
    
    def _generate_gitlab_ci_config(self, config: Dict[str, Any]) -> str:
        """Generate GitLab CI configuration for security testing."""
        gitlab_ci = f"""# {config['description']}

stages:
"""
        
        for stage in config['stages']:
            stage_name = stage['name'].lower().replace(' ', '_')
            gitlab_ci += f"  - {stage_name}\n"
        
        gitlab_ci += """
variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/
    - venv/

before_script:
  - python -m venv venv
  - source venv/bin/activate
  - pip install --upgrade pip
  - pip install -r requirements.txt
  - pip install -r requirements-dev.txt

"""
        
        for stage in config['stages']:
            stage_name = stage['name'].lower().replace(' ', '_')
            gitlab_ci += f"""{stage_name}:
  stage: {stage_name}
  script:
"""
            for command in stage['commands']:
                gitlab_ci += f"    - {command}\n"
            
            gitlab_ci += "  artifacts:\n"
            gitlab_ci += "    reports:\n"
            gitlab_ci += "      junit: tests/security/reports/*.xml\n"
            gitlab_ci += "    paths:\n"
            gitlab_ci += "      - tests/security/reports/\n"
            gitlab_ci += "    expire_in: 1 week\n"
            
            if not stage.get('fail_on_error', True):
                gitlab_ci += "  allow_failure: true\n"
            
            gitlab_ci += "\n"
        
        return gitlab_ci
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security automation report."""
        report = {
            "report_type": "security_automation",
            "timestamp": datetime.utcnow().isoformat(),
            "scans": {},
            "summary": {
                "secrets_found": 0,
                "security_issues": 0,
                "high_severity_issues": 0,
                "medium_severity_issues": 0,
                "low_severity_issues": 0
            },
            "recommendations": []
        }
        
        # Run secret scanning
        secret_results = self.scan_secrets()
        report["scans"]["secret_scanning"] = secret_results
        report["summary"]["secrets_found"] = len(secret_results["secrets_found"])
        
        # Count secret severities
        for secret in secret_results["secrets_found"]:
            severity = secret.get("severity", "LOW")
            if severity == "HIGH":
                report["summary"]["high_severity_issues"] += 1
            elif severity == "MEDIUM":
                report["summary"]["medium_severity_issues"] += 1
            else:
                report["summary"]["low_severity_issues"] += 1
        
        # Run security linting
        linting_results = self.run_security_linting()
        report["scans"]["security_linting"] = linting_results
        report["summary"]["security_issues"] = linting_results["total_issues"]
        
        # Count linting issues by severity
        for tool_name, tool_results in linting_results.get("tools", {}).items():
            for issue in tool_results.get("issues", []):
                severity = issue.get("severity", "LOW")
                if isinstance(severity, int):
                    severity = "HIGH" if severity >= 2 else "MEDIUM" if severity == 1 else "LOW"
                
                if severity == "HIGH":
                    report["summary"]["high_severity_issues"] += 1
                elif severity == "MEDIUM":
                    report["summary"]["medium_severity_issues"] += 1
                else:
                    report["summary"]["low_severity_issues"] += 1
        
        # Generate recommendations
        report["recommendations"] = self._generate_security_recommendations(report)
        
        # Create CI/CD pipeline
        pipeline_results = self.create_security_pipeline()
        report["pipeline"] = pipeline_results
        
        # Save report
        report_path = self.results_dir / f"security_automation_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        report["report_path"] = str(report_path)
        return report
    
    def _generate_security_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate security automation recommendations."""
        recommendations = []
        
        summary = report["summary"]
        
        if summary["secrets_found"] > 0:
            recommendations.append(f"CRITICAL: Remove {summary['secrets_found']} hardcoded secrets from codebase")
        
        if summary["high_severity_issues"] > 0:
            recommendations.append(f"HIGH PRIORITY: Fix {summary['high_severity_issues']} high-severity security issues")
        
        # Scan-specific recommendations
        scans = report.get("scans", {})
        
        if scans.get("secret_scanning", {}).get("status") == "secrets_detected":
            recommendations.append("Implement pre-commit hooks to prevent secret commits")
            recommendations.append("Use environment variables and secret management systems")
        
        if scans.get("security_linting", {}).get("total_issues", 0) > 10:
            recommendations.append("Integrate security linting into development workflow")
        
        # General recommendations
        recommendations.extend([
            "Set up automated security scanning in CI/CD pipeline",
            "Regular security training for development team",
            "Implement security code review practices",
            "Use static analysis tools in IDE/editor",
            "Regular dependency updates and vulnerability patching"
        ])
        
        return recommendations


# Test Classes
class TestSecurityAutomation:
    """Security automation test cases."""
    
    @pytest.fixture
    def security_automation(self):
        """Security automation fixture."""
        return SecurityAutomation()
    
    def test_secret_scanning(self, security_automation):
        """Test secret scanning functionality."""
        results = security_automation.scan_secrets()
        
        assert results["scan_type"] == "secret_scanning"
        assert "files_scanned" in results
        assert "secrets_found" in results
        
        # Fail if high-confidence secrets found
        high_confidence_secrets = [
            s for s in results["secrets_found"]
            if s.get("confidence") == "HIGH" and s.get("severity") in ["HIGH", "MEDIUM"]
        ]
        
        if high_confidence_secrets:
            pytest.fail(f"High-confidence secrets found: {len(high_confidence_secrets)}")
        
        # Print summary
        print(f"\nSecret Scan Results:")
        print(f"Files scanned: {results['files_scanned']}")
        print(f"Secrets found: {len(results['secrets_found'])}")
    
    def test_security_linting(self, security_automation):
        """Test security linting functionality."""
        results = security_automation.run_security_linting()
        
        assert results["scan_type"] == "security_linting"
        assert "tools" in results
        assert "total_issues" in results
        
        # Check individual tools
        for tool_name, tool_results in results["tools"].items():
            assert "tool" in tool_results
            assert "status" in tool_results
            
            if tool_results["status"] == "completed":
                print(f"\n{tool_name} found {tool_results.get('issue_count', 0)} issues")
        
        # Warn on high-severity issues
        high_severity_count = 0
        for tool_results in results["tools"].values():
            for issue in tool_results.get("issues", []):
                if issue.get("severity") == "HIGH":
                    high_severity_count += 1
        
        if high_severity_count > 5:
            print(f"WARNING: {high_severity_count} high-severity security issues found")
    
    def test_security_pipeline_creation(self, security_automation):
        """Test security pipeline creation."""
        results = security_automation.create_security_pipeline()
        
        assert "pipeline_config" in results
        assert "github_workflow_path" in results
        assert "gitlab_ci_path" in results
        
        # Verify files were created
        github_path = Path(results["github_workflow_path"])
        gitlab_path = Path(results["gitlab_ci_path"])
        
        assert github_path.exists()
        assert gitlab_path.exists()
        
        # Verify content
        with open(github_path, 'r') as f:
            github_content = f.read()
            assert "Security Pipeline" in github_content
            assert "secret-scanning" in github_content.lower()
        
        with open(gitlab_path, 'r') as f:
            gitlab_content = f.read()
            assert "security" in gitlab_content.lower()
    
    def test_comprehensive_security_automation(self, security_automation):
        """Test comprehensive security automation report."""
        report = security_automation.generate_security_report()
        
        assert "report_type" in report
        assert report["report_type"] == "security_automation"
        assert "scans" in report
        assert "summary" in report
        
        # Verify report file
        assert Path(report["report_path"]).exists()
        
        # Security gates
        summary = report["summary"]
        
        if summary["secrets_found"] > 0:
            print(f"WARNING: {summary['secrets_found']} secrets found in codebase")
        
        if summary["high_severity_issues"] > 10:
            pytest.fail(f"Too many high-severity security issues: {summary['high_severity_issues']}")
        
        # Print summary
        print(f"\n=== SECURITY AUTOMATION SUMMARY ===")
        print(f"Secrets Found: {summary['secrets_found']}")
        print(f"Security Issues: {summary['security_issues']}")
        print(f"High Severity: {summary['high_severity_issues']}")
        print(f"Medium Severity: {summary['medium_severity_issues']}")
        print(f"Low Severity: {summary['low_severity_issues']}")
        print(f"Report: {report['report_path']}")
    
    @pytest.mark.integration
    def test_security_gate_automation(self, security_automation):
        """Test security gates for CI/CD integration."""
        report = security_automation.generate_security_report()
        
        # Define security gates
        SECRETS_THRESHOLD = 0       # No secrets allowed
        HIGH_SEVERITY_THRESHOLD = 5 # Max 5 high-severity issues
        TOTAL_ISSUES_THRESHOLD = 50 # Max 50 total issues
        
        summary = report["summary"]
        
        failures = []
        
        if summary["secrets_found"] > SECRETS_THRESHOLD:
            failures.append(f"Secrets found: {summary['secrets_found']} > {SECRETS_THRESHOLD}")
        
        if summary["high_severity_issues"] > HIGH_SEVERITY_THRESHOLD:
            failures.append(f"High-severity issues: {summary['high_severity_issues']} > {HIGH_SEVERITY_THRESHOLD}")
        
        total_issues = summary["security_issues"] + summary["secrets_found"]
        if total_issues > TOTAL_ISSUES_THRESHOLD:
            failures.append(f"Total security issues: {total_issues} > {TOTAL_ISSUES_THRESHOLD}")
        
        if failures:
            pytest.fail(f"Security automation gate failures: {'; '.join(failures)}")


if __name__ == "__main__":
    automation = SecurityAutomation()
    report = automation.generate_security_report()
    print(json.dumps(report, indent=2))
