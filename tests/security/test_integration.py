"""
Security Testing Suite Integration Test

Simple integration test to validate the security testing framework
without external dependencies.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Add security tests to path
sys.path.append(str(Path(__file__).parent))

def test_basic_security_components():
    """Test basic security components without external dependencies."""
    print("🛡️  Testing Security Testing Suite Components")
    print("=" * 60)
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": {},
        "overall_status": "success"
    }
    
    # Test 1: Secret Pattern Detection
    print("1. Testing Secret Pattern Detection...")
    try:
        from automation.test_security_automation import SecurityAutomation
        automation = SecurityAutomation(".")
        
        # Test secret patterns
        test_string = "aws_access_key_id = AKIAIOSFODNN7EXAMPLE"
        patterns = automation.secret_patterns
        
        found_secrets = 0
        for secret_type, pattern in patterns.items():
            import re
            if re.search(pattern, test_string, re.IGNORECASE):
                found_secrets += 1
        
        results["tests"]["secret_detection"] = {
            "status": "passed",
            "patterns_tested": len(patterns),
            "secrets_detected": found_secrets
        }
        print(f"   ✅ Secret pattern detection: {len(patterns)} patterns loaded")
        
    except Exception as e:
        results["tests"]["secret_detection"] = {
            "status": "failed",
            "error": str(e)
        }
        print(f"   ❌ Secret pattern detection failed: {e}")
        results["overall_status"] = "failed"
    
    # Test 2: Vulnerability Scanning Components
    print("2. Testing Vulnerability Scanning Components...")
    try:
        from vulnerability_scanning.test_dependency_vulnerabilities import DependencyVulnerabilityScanner
        scanner = DependencyVulnerabilityScanner()
        
        # Test Docker analysis
        test_dockerfile_content = """FROM python:3.11
USER root
COPY . .
ADD http://example.com/file.tar.gz /app/
"""
        
        with open("test_dockerfile", "w") as f:
            f.write(test_dockerfile_content)
        
        issues = scanner._analyze_dockerfile(Path("test_dockerfile"))
        os.remove("test_dockerfile")
        
        results["tests"]["vulnerability_scanning"] = {
            "status": "passed",
            "dockerfile_issues_detected": len(issues)
        }
        print(f"   ✅ Vulnerability scanning: {len(issues)} Docker issues detected")
        
    except Exception as e:
        results["tests"]["vulnerability_scanning"] = {
            "status": "failed",
            "error": str(e)
        }
        print(f"   ❌ Vulnerability scanning failed: {e}")
        results["overall_status"] = "failed"
    
    # Test 3: Penetration Testing Components
    print("3. Testing Penetration Testing Components...")
    try:
        from penetration_testing.test_penetration_suite import PenetrationTester
        pen_tester = PenetrationTester("http://localhost:8000")
        
        # Test payload generation
        sql_payloads = pen_tester.sql_payloads
        xss_payloads = pen_tester.xss_payloads
        
        results["tests"]["penetration_testing"] = {
            "status": "passed",
            "sql_payloads": len(sql_payloads),
            "xss_payloads": len(xss_payloads)
        }
        print(f"   ✅ Penetration testing: {len(sql_payloads)} SQL + {len(xss_payloads)} XSS payloads loaded")
        
    except Exception as e:
        results["tests"]["penetration_testing"] = {
            "status": "failed",
            "error": str(e)
        }
        print(f"   ❌ Penetration testing failed: {e}")
        results["overall_status"] = "failed"
    
    # Test 4: Compliance Testing Components
    print("4. Testing Compliance Testing Components...")
    try:
        from compliance.test_hipaa_compliance import HIPAAComplianceTester
        from compliance.test_gdpr_compliance import GDPRComplianceTester
        
        hipaa_tester = HIPAAComplianceTester("http://localhost:8000")
        gdpr_tester = GDPRComplianceTester("http://localhost:8000")
        
        # Test configuration
        hipaa_requirements = hipaa_tester.hipaa_requirements
        gdpr_rights = gdpr_tester.data_subject_rights
        
        results["tests"]["compliance_testing"] = {
            "status": "passed",
            "hipaa_requirements": len(hipaa_requirements),
            "gdpr_rights": len(gdpr_rights)
        }
        print(f"   ✅ Compliance testing: HIPAA + GDPR frameworks loaded")
        
    except Exception as e:
        results["tests"]["compliance_testing"] = {
            "status": "failed",
            "error": str(e)
        }
        print(f"   ❌ Compliance testing failed: {e}")
        results["overall_status"] = "failed"
    
    # Test 5: Master Test Runner
    print("5. Testing Master Test Runner...")
    try:
        from run_comprehensive_security_tests import ComprehensiveSecurityTestSuite
        test_suite = ComprehensiveSecurityTestSuite()
        
        # Test configuration
        config = test_suite.test_config
        
        results["tests"]["master_runner"] = {
            "status": "passed",
            "test_categories": len(config),
            "enabled_tests": sum(1 for category in config.values() if category.get("enabled", False))
        }
        print(f"   ✅ Master test runner: {len(config)} test categories configured")
        
    except Exception as e:
        results["tests"]["master_runner"] = {
            "status": "failed",
            "error": str(e)
        }
        print(f"   ❌ Master test runner failed: {e}")
        results["overall_status"] = "failed"
    
    # Test 6: Report Generation
    print("6. Testing Report Generation...")
    try:
        reports_dir = Path("tests/security/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test report
        test_report = {
            "test_type": "integration_test",
            "timestamp": datetime.utcnow().isoformat(),
            "status": results["overall_status"],
            "summary": {
                "total_tests": len(results["tests"]),
                "passed_tests": len([t for t in results["tests"].values() if t["status"] == "passed"]),
                "failed_tests": len([t for t in results["tests"].values() if t["status"] == "failed"])
            }
        }
        
        report_path = reports_dir / "integration_test_report.json"
        with open(report_path, "w") as f:
            json.dump(test_report, f, indent=2)
        
        results["tests"]["report_generation"] = {
            "status": "passed",
            "report_path": str(report_path)
        }
        print(f"   ✅ Report generation: Test report created at {report_path}")
        
    except Exception as e:
        results["tests"]["report_generation"] = {
            "status": "failed",
            "error": str(e)
        }
        print(f"   ❌ Report generation failed: {e}")
        results["overall_status"] = "failed"
    
    # Print summary
    print("\n" + "=" * 60)
    print("🛡️  Security Testing Suite Integration Test Summary")
    print(f"   Overall Status: {results['overall_status'].upper()}")
    
    passed_tests = [name for name, test in results["tests"].items() if test["status"] == "passed"]
    failed_tests = [name for name, test in results["tests"].items() if test["status"] == "failed"]
    
    print(f"   Passed Tests: {len(passed_tests)}")
    for test_name in passed_tests:
        print(f"     ✅ {test_name}")
    
    if failed_tests:
        print(f"   Failed Tests: {len(failed_tests)}")
        for test_name in failed_tests:
            print(f"     ❌ {test_name}")
    
    print(f"\n📊 Test Results: {len(passed_tests)}/{len(results['tests'])} tests passed")
    
    if results["overall_status"] == "success":
        print("🎉 Security Testing Suite is ready for use!")
    else:
        print("⚠️  Some components need attention before full deployment")
    
    return results

if __name__ == "__main__":
    test_basic_security_components()
