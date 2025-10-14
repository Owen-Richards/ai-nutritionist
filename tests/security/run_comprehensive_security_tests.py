"""
Comprehensive Security Test Suite Runner

Master test runner for all security testing components:
- Vulnerability scanning (OWASP ZAP, dependencies, containers, IaC)
- Penetration testing (authentication, authorization, injection, session management)
- Compliance testing (HIPAA, GDPR, PCI DSS, SOC 2)
- Security automation (secret scanning, security gates, CI/CD integration)
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import pytest

# Import all security test modules
sys.path.append(str(Path(__file__).parent))

from vulnerability_scanning.test_owasp_zap_scanning import OWASPZAPScanner, MockZAPScanner
from vulnerability_scanning.test_dependency_vulnerabilities import DependencyVulnerabilityScanner
from penetration_testing.test_penetration_suite import PenetrationTester
from compliance.test_hipaa_compliance import HIPAAComplianceTester
from compliance.test_gdpr_compliance import GDPRComplianceTester
from automation.test_security_automation import SecurityAutomation


class ComprehensiveSecurityTestSuite:
    """Master security test suite coordinator."""
    
    def __init__(self, base_url: str = "http://localhost:8000", project_root: Optional[str] = None):
        self.base_url = base_url
        self.project_root = Path(project_root or ".")
        self.results_dir = Path("tests/security/reports/comprehensive")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all test components
        self.vulnerability_scanner = DependencyVulnerabilityScanner()
        self.zap_scanner = MockZAPScanner()  # Use mock by default
        self.penetration_tester = PenetrationTester(base_url)
        self.hipaa_tester = HIPAAComplianceTester(base_url)
        self.gdpr_tester = GDPRComplianceTester(base_url)
        self.security_automation = SecurityAutomation(project_root)
        
        # Security test configuration
        self.test_config = {
            "vulnerability_scanning": {
                "enabled": True,
                "dependencies": True,
                "containers": True,
                "infrastructure": True,
                "owasp_zap": True
            },
            "penetration_testing": {
                "enabled": True,
                "authentication_bypass": True,
                "authorization_flaws": True,
                "injection_attacks": True,
                "session_management": True
            },
            "compliance_testing": {
                "enabled": True,
                "hipaa": True,
                "gdpr": True,
                "pci_dss": False,  # Not implemented yet
                "sox": False       # Not implemented yet
            },
            "security_automation": {
                "enabled": True,
                "secret_scanning": True,
                "security_linting": True,
                "ci_cd_integration": True
            }
        }
    
    def run_vulnerability_scanning(self) -> Dict[str, Any]:
        """Run comprehensive vulnerability scanning."""
        print("🔍 Running Vulnerability Scanning...")
        
        results = {
            "test_category": "vulnerability_scanning",
            "timestamp": datetime.utcnow().isoformat(),
            "scans": {},
            "summary": {
                "total_vulnerabilities": 0,
                "critical_vulnerabilities": 0,
                "high_vulnerabilities": 0,
                "medium_vulnerabilities": 0,
                "low_vulnerabilities": 0
            },
            "status": "completed"
        }
        
        try:
            # Dependency vulnerability scanning
            if self.test_config["vulnerability_scanning"]["dependencies"]:
                print("  📦 Scanning dependencies...")
                dep_results = self.vulnerability_scanner.generate_comprehensive_report()
                results["scans"]["dependencies"] = dep_results
                
                # Update summary
                summary = dep_results.get("summary", {})
                results["summary"]["total_vulnerabilities"] += summary.get("total_issues", 0)
                results["summary"]["high_vulnerabilities"] += summary.get("high_severity_issues", 0)
                results["summary"]["medium_vulnerabilities"] += summary.get("medium_severity_issues", 0)
                results["summary"]["low_vulnerabilities"] += summary.get("low_severity_issues", 0)
            
            # OWASP ZAP scanning
            if self.test_config["vulnerability_scanning"]["owasp_zap"]:
                print("  🕷️  Running OWASP ZAP scan...")
                zap_passive = self.zap_scanner.passive_scan(self.base_url)
                zap_active = self.zap_scanner.active_scan(self.base_url)
                
                results["scans"]["owasp_zap"] = {
                    "passive_scan": zap_passive,
                    "active_scan": zap_active
                }
                
                # Update summary from ZAP results
                for scan_result in [zap_passive, zap_active]:
                    results["summary"]["total_vulnerabilities"] += scan_result.get("alert_count", 0)
                    results["summary"]["high_vulnerabilities"] += scan_result.get("high_risk_count", 0)
                    results["summary"]["medium_vulnerabilities"] += scan_result.get("medium_risk_count", 0)
                    results["summary"]["low_vulnerabilities"] += scan_result.get("low_risk_count", 0)
            
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
        
        return results
    
    def run_penetration_testing(self) -> Dict[str, Any]:
        """Run comprehensive penetration testing."""
        print("🎯 Running Penetration Testing...")
        
        try:
            results = self.penetration_tester.generate_penetration_test_report()
            return results
        except Exception as e:
            return {
                "test_category": "penetration_testing",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def run_compliance_testing(self) -> Dict[str, Any]:
        """Run compliance testing."""
        print("📋 Running Compliance Testing...")
        
        results = {
            "test_category": "compliance_testing",
            "timestamp": datetime.utcnow().isoformat(),
            "frameworks": {},
            "overall_compliance": "compliant",
            "total_violations": 0,
            "status": "completed"
        }
        
        try:
            # HIPAA compliance testing
            if self.test_config["compliance_testing"]["hipaa"]:
                print("  🏥 Testing HIPAA compliance...")
                hipaa_results = self.hipaa_tester.generate_hipaa_compliance_report()
                results["frameworks"]["hipaa"] = hipaa_results
                
                if hipaa_results["overall_compliance"] == "non_compliant":
                    results["overall_compliance"] = "non_compliant"
                results["total_violations"] += len(hipaa_results.get("violations", []))
            
            # GDPR compliance testing
            if self.test_config["compliance_testing"]["gdpr"]:
                print("  🇪🇺 Testing GDPR compliance...")
                gdpr_results = self.gdpr_tester.generate_gdpr_compliance_report()
                results["frameworks"]["gdpr"] = gdpr_results
                
                if gdpr_results["overall_compliance"] == "non_compliant":
                    results["overall_compliance"] = "non_compliant"
                results["total_violations"] += len(gdpr_results.get("violations", []))
            
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
        
        return results
    
    def run_security_automation(self) -> Dict[str, Any]:
        """Run security automation tests."""
        print("🤖 Running Security Automation...")
        
        try:
            results = self.security_automation.generate_security_report()
            return results
        except Exception as e:
            return {
                "test_category": "security_automation",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def run_comprehensive_security_test(self) -> Dict[str, Any]:
        """Run complete security test suite."""
        print("🛡️  Starting Comprehensive Security Test Suite")
        print("=" * 60)
        
        master_report = {
            "test_suite": "comprehensive_security_testing",
            "timestamp": datetime.utcnow().isoformat(),
            "target": self.base_url,
            "project_root": str(self.project_root),
            "configuration": self.test_config,
            "test_results": {},
            "executive_summary": {
                "total_vulnerabilities": 0,
                "critical_issues": 0,
                "high_severity_issues": 0,
                "medium_severity_issues": 0,
                "low_severity_issues": 0,
                "compliance_violations": 0,
                "secrets_found": 0,
                "overall_security_posture": "unknown"
            },
            "recommendations": [],
            "status": "completed"
        }
        
        try:
            # Run vulnerability scanning
            if self.test_config["vulnerability_scanning"]["enabled"]:
                vuln_results = self.run_vulnerability_scanning()
                master_report["test_results"]["vulnerability_scanning"] = vuln_results
                
                # Update executive summary
                summary = vuln_results.get("summary", {})
                master_report["executive_summary"]["total_vulnerabilities"] += summary.get("total_vulnerabilities", 0)
                master_report["executive_summary"]["high_severity_issues"] += summary.get("high_vulnerabilities", 0)
                master_report["executive_summary"]["medium_severity_issues"] += summary.get("medium_vulnerabilities", 0)
                master_report["executive_summary"]["low_severity_issues"] += summary.get("low_vulnerabilities", 0)
            
            # Run penetration testing
            if self.test_config["penetration_testing"]["enabled"]:
                pentest_results = self.run_penetration_testing()
                master_report["test_results"]["penetration_testing"] = pentest_results
                
                # Update executive summary
                pentest_summary = pentest_results.get("summary", {})
                master_report["executive_summary"]["critical_issues"] += pentest_summary.get("critical_vulnerabilities", 0)
                master_report["executive_summary"]["high_severity_issues"] += pentest_summary.get("high_vulnerabilities", 0)
                master_report["executive_summary"]["medium_severity_issues"] += pentest_summary.get("medium_vulnerabilities", 0)
                master_report["executive_summary"]["low_severity_issues"] += pentest_summary.get("low_vulnerabilities", 0)
            
            # Run compliance testing
            if self.test_config["compliance_testing"]["enabled"]:
                compliance_results = self.run_compliance_testing()
                master_report["test_results"]["compliance_testing"] = compliance_results
                
                # Update executive summary
                master_report["executive_summary"]["compliance_violations"] += compliance_results.get("total_violations", 0)
            
            # Run security automation
            if self.test_config["security_automation"]["enabled"]:
                automation_results = self.run_security_automation()
                master_report["test_results"]["security_automation"] = automation_results
                
                # Update executive summary
                automation_summary = automation_results.get("summary", {})
                master_report["executive_summary"]["secrets_found"] += automation_summary.get("secrets_found", 0)
                master_report["executive_summary"]["high_severity_issues"] += automation_summary.get("high_severity_issues", 0)
                master_report["executive_summary"]["medium_severity_issues"] += automation_summary.get("medium_severity_issues", 0)
                master_report["executive_summary"]["low_severity_issues"] += automation_summary.get("low_severity_issues", 0)
            
            # Determine overall security posture
            master_report["executive_summary"]["overall_security_posture"] = self._calculate_security_posture(master_report)
            
            # Generate recommendations
            master_report["recommendations"] = self._generate_master_recommendations(master_report)
            
        except Exception as e:
            master_report["status"] = "error"
            master_report["error"] = str(e)
        
        # Save master report
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"comprehensive_security_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(master_report, f, indent=2)
        
        master_report["report_path"] = str(report_path)
        
        # Generate executive summary report
        executive_report_path = self._generate_executive_summary(master_report)
        master_report["executive_report_path"] = executive_report_path
        
        print("\\n" + "=" * 60)
        print("🛡️  Comprehensive Security Test Suite Completed")
        self._print_executive_summary(master_report)
        
        return master_report
    
    def _calculate_security_posture(self, report: Dict[str, Any]) -> str:
        """Calculate overall security posture."""
        summary = report["executive_summary"]
        
        # Critical issues = immediate failure
        if summary["critical_issues"] > 0:
            return "critical"
        
        # High-severity issues
        if summary["high_severity_issues"] > 10:
            return "poor"
        elif summary["high_severity_issues"] > 5:
            return "fair"
        
        # Secrets found = security risk
        if summary["secrets_found"] > 0:
            return "fair"
        
        # Compliance violations
        if summary["compliance_violations"] > 5:
            return "fair"
        
        # Total issues
        total_issues = (
            summary["high_severity_issues"] +
            summary["medium_severity_issues"] +
            summary["low_severity_issues"]
        )
        
        if total_issues == 0:
            return "excellent"
        elif total_issues <= 10:
            return "good"
        elif total_issues <= 25:
            return "fair"
        else:
            return "poor"
    
    def _generate_master_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate master security recommendations."""
        recommendations = []
        summary = report["executive_summary"]
        
        # Critical recommendations
        if summary["critical_issues"] > 0:
            recommendations.append(f"🚨 CRITICAL: Address {summary['critical_issues']} critical security issues immediately")
        
        if summary["secrets_found"] > 0:
            recommendations.append(f"🔐 URGENT: Remove {summary['secrets_found']} hardcoded secrets from codebase")
        
        if summary["high_severity_issues"] > 10:
            recommendations.append(f"⚠️ HIGH PRIORITY: Fix {summary['high_severity_issues']} high-severity vulnerabilities")
        
        # Compliance recommendations
        if summary["compliance_violations"] > 0:
            recommendations.append(f"📋 COMPLIANCE: Address {summary['compliance_violations']} compliance violations")
        
        # Test-specific recommendations
        test_results = report.get("test_results", {})
        
        if "vulnerability_scanning" in test_results:
            vuln_results = test_results["vulnerability_scanning"]
            if vuln_results.get("summary", {}).get("total_vulnerabilities", 0) > 0:
                recommendations.append("🔍 Update vulnerable dependencies and fix code security issues")
        
        if "penetration_testing" in test_results:
            pentest_results = test_results["penetration_testing"]
            if pentest_results.get("summary", {}).get("total_vulnerabilities", 0) > 0:
                recommendations.append("🎯 Strengthen authentication, authorization, and input validation")
        
        # General security recommendations
        recommendations.extend([
            "🤖 Implement automated security testing in CI/CD pipeline",
            "📚 Conduct regular security training for development team",
            "🔄 Establish regular security assessment schedule",
            "📖 Document security procedures and incident response plans",
            "🛡️ Implement security monitoring and logging",
            "🔐 Use secure coding practices and code review processes"
        ])
        
        return recommendations
    
    def _generate_executive_summary(self, report: Dict[str, Any]) -> str:
        """Generate executive summary report in HTML format."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        exec_report_path = self.results_dir / f"executive_security_summary_{timestamp}.html"
        
        summary = report["executive_summary"]
        posture = summary["overall_security_posture"]
        
        # Color coding for security posture
        posture_colors = {
            "excellent": "#4CAF50",
            "good": "#8BC34A",
            "fair": "#FF9800",
            "poor": "#F44336",
            "critical": "#D32F2F"
        }
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Assessment Executive Summary</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .posture {{ 
                    background-color: {posture_colors.get(posture, '#666')};
                    color: white;
                    padding: 10px 20px;
                    border-radius: 20px;
                    display: inline-block;
                    font-weight: bold;
                    text-transform: uppercase;
                }}
                .metrics {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric {{ text-align: center; padding: 15px; background-color: #f9f9f9; border-radius: 8px; }}
                .metric-value {{ font-size: 2em; font-weight: bold; color: #333; }}
                .metric-label {{ color: #666; margin-top: 5px; }}
                .critical {{ color: #D32F2F; }}
                .high {{ color: #F44336; }}
                .medium {{ color: #FF9800; }}
                .low {{ color: #4CAF50; }}
                .recommendations {{ background-color: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .recommendation {{ margin: 10px 0; padding: 10px; background-color: white; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🛡️ Security Assessment Executive Summary</h1>
                <p><strong>Assessment Date:</strong> {report['timestamp'][:10]}</p>
                <p><strong>Target Application:</strong> {report['target']}</p>
                <p><strong>Overall Security Posture:</strong> <span class="posture">{posture}</span></p>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value critical">{summary['critical_issues']}</div>
                    <div class="metric-label">Critical Issues</div>
                </div>
                <div class="metric">
                    <div class="metric-value high">{summary['high_severity_issues']}</div>
                    <div class="metric-label">High Severity</div>
                </div>
                <div class="metric">
                    <div class="metric-value medium">{summary['medium_severity_issues']}</div>
                    <div class="metric-label">Medium Severity</div>
                </div>
                <div class="metric">
                    <div class="metric-value low">{summary['low_severity_issues']}</div>
                    <div class="metric-label">Low Severity</div>
                </div>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value critical">{summary['secrets_found']}</div>
                    <div class="metric-label">Secrets Found</div>
                </div>
                <div class="metric">
                    <div class="metric-value high">{summary['compliance_violations']}</div>
                    <div class="metric-label">Compliance Violations</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary['total_vulnerabilities']}</div>
                    <div class="metric-label">Total Vulnerabilities</div>
                </div>
            </div>
            
            <div class="recommendations">
                <h2>🎯 Key Recommendations</h2>
        """
        
        for recommendation in report["recommendations"][:10]:  # Top 10 recommendations
            html_content += f'<div class="recommendation">{recommendation}</div>\n'
        
        html_content += f"""
            </div>
            
            <div>
                <h2>📊 Test Coverage</h2>
                <ul>
        """
        
        test_results = report.get("test_results", {})
        for test_category in test_results.keys():
            status = test_results[test_category].get("status", "unknown")
            html_content += f"<li><strong>{test_category.replace('_', ' ').title()}:</strong> {status}</li>\n"
        
        html_content += f"""
                </ul>
            </div>
            
            <div style="margin-top: 40px; padding: 20px; background-color: #f5f5f5; border-radius: 8px;">
                <p><strong>Full Report:</strong> {report.get('report_path', 'N/A')}</p>
                <p><strong>Generated:</strong> {report['timestamp']}</p>
            </div>
        </body>
        </html>
        """
        
        with open(exec_report_path, 'w') as f:
            f.write(html_content)
        
        return str(exec_report_path)
    
    def _print_executive_summary(self, report: Dict[str, Any]):
        """Print executive summary to console."""
        summary = report["executive_summary"]
        
        print(f"\\n📊 EXECUTIVE SUMMARY")
        print(f"   Overall Security Posture: {summary['overall_security_posture'].upper()}")
        print(f"   Critical Issues: {summary['critical_issues']}")
        print(f"   High Severity Issues: {summary['high_severity_issues']}")
        print(f"   Medium Severity Issues: {summary['medium_severity_issues']}")
        print(f"   Low Severity Issues: {summary['low_severity_issues']}")
        print(f"   Secrets Found: {summary['secrets_found']}")
        print(f"   Compliance Violations: {summary['compliance_violations']}")
        print(f"   Total Vulnerabilities: {summary['total_vulnerabilities']}")
        
        print(f"\\n📄 REPORTS")
        print(f"   Full Report: {report.get('report_path', 'N/A')}")
        print(f"   Executive Summary: {report.get('executive_report_path', 'N/A')}")
        
        if summary["critical_issues"] > 0 or summary["secrets_found"] > 0:
            print(f"\\n🚨 CRITICAL ACTION REQUIRED")
            print(f"   Address critical issues and remove secrets before production deployment!")


def main():
    """Command-line interface for security test suite."""
    parser = argparse.ArgumentParser(description="Comprehensive Security Test Suite")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for testing")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--output-dir", help="Output directory for reports")
    parser.add_argument("--test-type", choices=[
        "all", "vulnerability", "penetration", "compliance", "automation"
    ], default="all", help="Type of security tests to run")
    
    args = parser.parse_args()
    
    # Initialize test suite
    test_suite = ComprehensiveSecurityTestSuite(
        base_url=args.base_url,
        project_root=args.project_root
    )
    
    # Override output directory if specified
    if args.output_dir:
        test_suite.results_dir = Path(args.output_dir)
        test_suite.results_dir.mkdir(parents=True, exist_ok=True)
    
    # Load custom configuration if provided
    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            custom_config = json.load(f)
            test_suite.test_config.update(custom_config)
    
    # Run specified tests
    if args.test_type == "all":
        results = test_suite.run_comprehensive_security_test()
    elif args.test_type == "vulnerability":
        results = test_suite.run_vulnerability_scanning()
    elif args.test_type == "penetration":
        results = test_suite.run_penetration_testing()
    elif args.test_type == "compliance":
        results = test_suite.run_compliance_testing()
    elif args.test_type == "automation":
        results = test_suite.run_security_automation()
    
    # Exit with appropriate code
    if results.get("status") == "error":
        sys.exit(1)
    elif results.get("executive_summary", {}).get("critical_issues", 0) > 0:
        sys.exit(2)  # Critical security issues found
    elif results.get("executive_summary", {}).get("secrets_found", 0) > 0:
        sys.exit(3)  # Secrets found
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
