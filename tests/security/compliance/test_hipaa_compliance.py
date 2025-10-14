"""
HIPAA Compliance Testing Suite

Tests for Health Insurance Portability and Accountability Act (HIPAA) compliance
in the AI Nutritionist application handling health-related data.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import pytest
import requests
from unittest.mock import Mock, patch


class HIPAAComplianceTester:
    """HIPAA compliance testing and validation."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results_dir = Path("tests/security/reports/compliance")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # HIPAA-required security controls
        self.hipaa_requirements = {
            "access_control": {
                "unique_user_identification": False,
                "automatic_logoff": False,
                "encryption_decryption": False
            },
            "audit_controls": {
                "audit_logging": False,
                "audit_review": False,
                "audit_reporting": False
            },
            "integrity": {
                "data_integrity": False,
                "transmission_integrity": False
            },
            "person_authentication": {
                "user_authentication": False,
                "multi_factor_auth": False
            },
            "transmission_security": {
                "data_encryption_in_transit": False,
                "network_controls": False,
                "secure_protocols": False
            }
        }
    
    def test_phi_data_protection(self) -> Dict[str, Any]:
        """Test Protected Health Information (PHI) data protection."""
        results = {
            "test_type": "phi_data_protection",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "violations": [],
            "status": "compliant"
        }
        
        # Test 1: PHI data encryption at rest
        encryption_test = self._test_data_encryption_at_rest()
        results["tests"].append(encryption_test)
        if not encryption_test["compliant"]:
            results["violations"].append({
                "requirement": "§164.312(a)(2)(iv) - Encryption",
                "description": "PHI must be encrypted at rest",
                "severity": "HIGH"
            })
            results["status"] = "non_compliant"
        
        # Test 2: PHI data encryption in transit
        transit_test = self._test_data_encryption_in_transit()
        results["tests"].append(transit_test)
        if not transit_test["compliant"]:
            results["violations"].append({
                "requirement": "§164.312(e)(1) - Transmission Security",
                "description": "PHI must be encrypted during transmission",
                "severity": "CRITICAL"
            })
            results["status"] = "non_compliant"
        
        # Test 3: PHI access controls
        access_test = self._test_phi_access_controls()
        results["tests"].append(access_test)
        if not access_test["compliant"]:
            results["violations"].append({
                "requirement": "§164.312(a)(1) - Access Control",
                "description": "Access to PHI must be controlled and authenticated",
                "severity": "HIGH"
            })
            results["status"] = "non_compliant"
        
        # Test 4: Minimum necessary rule
        min_necessary_test = self._test_minimum_necessary_rule()
        results["tests"].append(min_necessary_test)
        if not min_necessary_test["compliant"]:
            results["violations"].append({
                "requirement": "§164.502(b) - Minimum Necessary",
                "description": "Only minimum necessary PHI should be disclosed",
                "severity": "MEDIUM"
            })
            results["status"] = "non_compliant"
        
        return results
    
    def _test_data_encryption_at_rest(self) -> Dict[str, Any]:
        """Test PHI data encryption at rest."""
        test_result = {
            "test_name": "data_encryption_at_rest",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Check database encryption configuration
            # This would typically involve checking AWS RDS encryption, DynamoDB encryption, etc.
            
            # Test 1: Check if sensitive endpoints return encrypted data
            response = self.session.get(f"{self.base_url}/user/health-data")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if data appears to be encrypted/hashed
                sensitive_fields = ["ssn", "medical_record_number", "health_conditions"]
                for field in sensitive_fields:
                    if field in data:
                        value = str(data[field])
                        # Simple check: encrypted data shouldn't contain obvious patterns
                        if len(value) > 0 and (
                            value.isdigit() or  # Plain SSN
                            value.count('-') > 0 or  # Formatted SSN
                            value.lower() in ["diabetes", "hypertension", "obesity"]  # Plain text conditions
                        ):
                            test_result["compliant"] = False
                            test_result["findings"].append(
                                f"Field '{field}' appears to contain unencrypted PHI"
                            )
            
            # Test 2: Check configuration files for encryption settings
            config_files = [
                "config/database.json",
                "infrastructure/terraform/dynamodb.tf",
                "infrastructure/terraform/rds.tf"
            ]
            
            for config_file in config_files:
                if Path(config_file).exists():
                    with open(config_file, 'r') as f:
                        content = f.read().lower()
                        if 'encrypt' not in content and 'kms' not in content:
                            test_result["findings"].append(
                                f"Encryption not configured in {config_file}"
                            )
                            test_result["compliant"] = False
            
        except Exception as e:
            test_result["compliant"] = False
            test_result["findings"].append(f"Error testing encryption: {e}")
        
        return test_result
    
    def _test_data_encryption_in_transit(self) -> Dict[str, Any]:
        """Test PHI data encryption in transit."""
        test_result = {
            "test_name": "data_encryption_in_transit",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test 1: Check HTTPS enforcement
            http_response = requests.get(
                self.base_url.replace('https://', 'http://'),
                allow_redirects=False,
                timeout=10
            )
            
            if http_response.status_code != 301 and http_response.status_code != 302:
                test_result["compliant"] = False
                test_result["findings"].append("HTTP not redirected to HTTPS")
            
            # Test 2: Check TLS version and cipher suites
            https_response = self.session.get(f"{self.base_url}/health")
            
            # Check security headers
            required_headers = [
                "strict-transport-security",
                "x-content-type-options",
                "x-frame-options",
                "x-xss-protection"
            ]
            
            for header in required_headers:
                if header not in [h.lower() for h in https_response.headers.keys()]:
                    test_result["compliant"] = False
                    test_result["findings"].append(f"Missing security header: {header}")
            
            # Test 3: Check for secure cookie attributes
            for cookie in https_response.cookies:
                if not cookie.secure:
                    test_result["compliant"] = False
                    test_result["findings"].append(f"Cookie '{cookie.name}' not marked as secure")
                
                if not hasattr(cookie, 'httponly') or not cookie.httponly:
                    test_result["findings"].append(f"Cookie '{cookie.name}' not marked as HttpOnly")
        
        except Exception as e:
            test_result["compliant"] = False
            test_result["findings"].append(f"Error testing transmission security: {e}")
        
        return test_result
    
    def _test_phi_access_controls(self) -> Dict[str, Any]:
        """Test PHI access controls."""
        test_result = {
            "test_name": "phi_access_controls",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test 1: Unauthenticated access to PHI endpoints
            phi_endpoints = [
                "/user/health-data",
                "/user/medical-history",
                "/user/nutrition-analysis",
                "/user/health-metrics",
                "/user/diet-restrictions"
            ]
            
            for endpoint in phi_endpoints:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    test_result["compliant"] = False
                    test_result["findings"].append(
                        f"PHI endpoint {endpoint} accessible without authentication"
                    )
            
            # Test 2: Check authentication mechanisms
            auth_response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": "test", "password": "weak"}
            )
            
            if auth_response.status_code == 200:
                # Check if weak passwords are accepted
                test_result["findings"].append("Weak password accepted - strengthen password policy")
            
            # Test 3: Check for role-based access control
            # This would require setting up test users with different roles
            
        except Exception as e:
            test_result["compliant"] = False
            test_result["findings"].append(f"Error testing access controls: {e}")
        
        return test_result
    
    def _test_minimum_necessary_rule(self) -> Dict[str, Any]:
        """Test minimum necessary rule compliance."""
        test_result = {
            "test_name": "minimum_necessary_rule",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test API responses for excessive PHI disclosure
            response = self.session.get(f"{self.base_url}/user/profile")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for unnecessary PHI fields
                unnecessary_fields = [
                    "ssn", "full_medical_history", "insurance_details",
                    "emergency_contacts", "next_of_kin"
                ]
                
                for field in unnecessary_fields:
                    if field in data:
                        test_result["compliant"] = False
                        test_result["findings"].append(
                            f"Unnecessary PHI field '{field}' disclosed in user profile"
                        )
                
                # Check if medical data is included in general endpoints
                medical_indicators = [
                    "diagnosis", "medication", "treatment", "procedure",
                    "condition", "symptom", "allergy"
                ]
                
                response_text = json.dumps(data).lower()
                for indicator in medical_indicators:
                    if indicator in response_text:
                        test_result["findings"].append(
                            f"Medical information ('{indicator}') included in general profile endpoint"
                        )
        
        except Exception as e:
            test_result["compliant"] = False
            test_result["findings"].append(f"Error testing minimum necessary rule: {e}")
        
        return test_result
    
    def test_audit_controls(self) -> Dict[str, Any]:
        """Test HIPAA audit control requirements."""
        results = {
            "test_type": "audit_controls",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "violations": [],
            "status": "compliant"
        }
        
        # Test 1: Audit logging implementation
        audit_logging_test = self._test_audit_logging()
        results["tests"].append(audit_logging_test)
        if not audit_logging_test["compliant"]:
            results["violations"].append({
                "requirement": "§164.312(b) - Audit Controls",
                "description": "Audit controls must log PHI access and modifications",
                "severity": "HIGH"
            })
            results["status"] = "non_compliant"
        
        # Test 2: Audit log integrity
        log_integrity_test = self._test_audit_log_integrity()
        results["tests"].append(log_integrity_test)
        if not log_integrity_test["compliant"]:
            results["violations"].append({
                "requirement": "§164.312(c)(1) - Integrity",
                "description": "Audit logs must be protected from alteration",
                "severity": "HIGH"
            })
            results["status"] = "non_compliant"
        
        return results
    
    def _test_audit_logging(self) -> Dict[str, Any]:
        """Test audit logging implementation."""
        test_result = {
            "test_name": "audit_logging",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test if PHI access is logged
            response = self.session.get(f"{self.base_url}/user/health-data")
            
            # Check if audit log endpoint exists
            audit_response = self.session.get(f"{self.base_url}/admin/audit-logs")
            
            if audit_response.status_code == 404:
                test_result["compliant"] = False
                test_result["findings"].append("No audit logging endpoint found")
            elif audit_response.status_code == 200:
                logs = audit_response.json()
                
                # Check for required audit fields
                required_fields = [
                    "timestamp", "user_id", "action", "resource",
                    "ip_address", "user_agent"
                ]
                
                if logs and isinstance(logs, list) and logs[0]:
                    log_entry = logs[0]
                    for field in required_fields:
                        if field not in log_entry:
                            test_result["findings"].append(
                                f"Audit log missing required field: {field}"
                            )
            
            # Check log retention
            # This would typically involve checking CloudWatch, ELK stack, etc.
            
        except Exception as e:
            test_result["compliant"] = False
            test_result["findings"].append(f"Error testing audit logging: {e}")
        
        return test_result
    
    def _test_audit_log_integrity(self) -> Dict[str, Any]:
        """Test audit log integrity protection."""
        test_result = {
            "test_name": "audit_log_integrity",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test if logs can be modified or deleted
            response = self.session.delete(f"{self.base_url}/admin/audit-logs/1")
            
            if response.status_code == 200:
                test_result["compliant"] = False
                test_result["findings"].append("Audit logs can be deleted")
            
            # Test if logs can be modified
            modify_response = self.session.put(
                f"{self.base_url}/admin/audit-logs/1",
                json={"action": "modified_action"}
            )
            
            if modify_response.status_code == 200:
                test_result["compliant"] = False
                test_result["findings"].append("Audit logs can be modified")
        
        except Exception as e:
            test_result["findings"].append(f"Error testing log integrity: {e}")
        
        return test_result
    
    def test_business_associate_agreements(self) -> Dict[str, Any]:
        """Test Business Associate Agreement (BAA) compliance."""
        results = {
            "test_type": "business_associate_agreements",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "violations": [],
            "status": "compliant"
        }
        
        # Test third-party service configurations
        third_party_test = self._test_third_party_services()
        results["tests"].append(third_party_test)
        if not third_party_test["compliant"]:
            results["violations"].append({
                "requirement": "§164.502(e) - Business Associate Requirements",
                "description": "All third-party services handling PHI must have BAAs",
                "severity": "HIGH"
            })
            results["status"] = "non_compliant"
        
        return results
    
    def _test_third_party_services(self) -> Dict[str, Any]:
        """Test third-party service BAA compliance."""
        test_result = {
            "test_name": "third_party_services",
            "compliant": True,
            "findings": []
        }
        
        # Check common third-party services that might handle PHI
        services_to_check = [
            "aws", "openai", "anthropic", "sendgrid", "twilio",
            "stripe", "segment", "mixpanel", "datadog"
        ]
        
        try:
            # Check configuration files for third-party service usage
            config_files = [
                "requirements.txt",
                "package.json",
                "src/config/settings.py",
                "infrastructure/terraform/main.tf"
            ]
            
            for config_file in config_files:
                if Path(config_file).exists():
                    with open(config_file, 'r') as f:
                        content = f.read().lower()
                        
                        for service in services_to_check:
                            if service in content:
                                test_result["findings"].append(
                                    f"Third-party service '{service}' detected - ensure BAA is in place"
                                )
            
            # Check environment variables for API keys
            env_vars = os.environ
            for var_name, var_value in env_vars.items():
                if any(service.upper() in var_name.upper() for service in services_to_check):
                    test_result["findings"].append(
                        f"Third-party service API key detected: {var_name} - ensure BAA compliance"
                    )
        
        except Exception as e:
            test_result["findings"].append(f"Error checking third-party services: {e}")
        
        return test_result
    
    def generate_hipaa_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive HIPAA compliance report."""
        report = {
            "compliance_framework": "HIPAA",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {},
            "overall_compliance": "compliant",
            "violations": [],
            "recommendations": []
        }
        
        # Run all HIPAA tests
        test_methods = [
            ("phi_data_protection", self.test_phi_data_protection),
            ("audit_controls", self.test_audit_controls),
            ("business_associate_agreements", self.test_business_associate_agreements)
        ]
        
        for test_name, test_method in test_methods:
            try:
                test_result = test_method()
                report["tests"][test_name] = test_result
                
                if test_result["status"] == "non_compliant":
                    report["overall_compliance"] = "non_compliant"
                    report["violations"].extend(test_result["violations"])
                    
            except Exception as e:
                report["tests"][test_name] = {
                    "error": str(e),
                    "status": "failed"
                }
                report["overall_compliance"] = "non_compliant"
        
        # Generate recommendations
        report["recommendations"] = self._generate_hipaa_recommendations(report)
        
        # Save report
        report_path = self.results_dir / f"hipaa_compliance_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        report["report_path"] = str(report_path)
        return report
    
    def _generate_hipaa_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate HIPAA compliance recommendations."""
        recommendations = []
        
        if report["overall_compliance"] == "non_compliant":
            recommendations.append("CRITICAL: Address all HIPAA violations before handling PHI")
        
        violations = report.get("violations", [])
        
        # Group recommendations by category
        if any("encryption" in v.get("description", "").lower() for v in violations):
            recommendations.append("Implement comprehensive encryption for PHI at rest and in transit")
        
        if any("audit" in v.get("description", "").lower() for v in violations):
            recommendations.append("Implement comprehensive audit logging for all PHI access")
        
        if any("access" in v.get("description", "").lower() for v in violations):
            recommendations.append("Strengthen access controls and authentication mechanisms")
        
        if any("business associate" in v.get("description", "").lower() for v in violations):
            recommendations.append("Ensure all third-party services have appropriate BAAs")
        
        # General recommendations
        recommendations.extend([
            "Conduct regular HIPAA compliance assessments",
            "Implement staff training on HIPAA requirements",
            "Establish incident response procedures for PHI breaches",
            "Regular review and update of privacy policies",
            "Implement risk assessment procedures"
        ])
        
        return recommendations


# Test Classes
class TestHIPAACompliance:
    """HIPAA compliance test cases."""
    
    @pytest.fixture
    def hipaa_tester(self):
        """HIPAA compliance tester fixture."""
        return HIPAAComplianceTester()
    
    def test_phi_data_protection_compliance(self, hipaa_tester):
        """Test PHI data protection compliance."""
        results = hipaa_tester.test_phi_data_protection()
        
        assert results["test_type"] == "phi_data_protection"
        
        # Fail if HIPAA violations found
        violations = results["violations"]
        critical_violations = [v for v in violations if v.get("severity") == "CRITICAL"]
        
        if critical_violations:
            pytest.fail(f"CRITICAL HIPAA violations found: {len(critical_violations)}")
        
        high_violations = [v for v in violations if v.get("severity") == "HIGH"]
        if high_violations:
            print(f"WARNING: {len(high_violations)} high-severity HIPAA violations found")
    
    def test_audit_controls_compliance(self, hipaa_tester):
        """Test audit controls compliance."""
        results = hipaa_tester.test_audit_controls()
        
        assert results["test_type"] == "audit_controls"
        
        if results["status"] == "non_compliant":
            violations = [v["description"] for v in results["violations"]]
            print(f"AUDIT CONTROL VIOLATIONS: {violations}")
    
    def test_business_associate_compliance(self, hipaa_tester):
        """Test business associate agreement compliance."""
        results = hipaa_tester.test_business_associate_agreements()
        
        assert results["test_type"] == "business_associate_agreements"
        
        # Check for third-party service issues
        if results["status"] == "non_compliant":
            print("WARNING: Business Associate Agreement issues found")
    
    def test_comprehensive_hipaa_compliance(self, hipaa_tester):
        """Test comprehensive HIPAA compliance."""
        report = hipaa_tester.generate_hipaa_compliance_report()
        
        assert "compliance_framework" in report
        assert report["compliance_framework"] == "HIPAA"
        
        # Verify report file
        assert Path(report["report_path"]).exists()
        
        # Compliance gate
        if report["overall_compliance"] == "non_compliant":
            violations_summary = []
            for violation in report["violations"]:
                violations_summary.append(f"{violation['severity']}: {violation['description']}")
            
            pytest.fail(f"HIPAA compliance violations found: {'; '.join(violations_summary)}")
        
        print(f"\n=== HIPAA COMPLIANCE SUMMARY ===")
        print(f"Overall Compliance: {report['overall_compliance']}")
        print(f"Total Violations: {len(report['violations'])}")
        print(f"Report: {report['report_path']}")


if __name__ == "__main__":
    tester = HIPAAComplianceTester()
    report = tester.generate_hipaa_compliance_report()
    print(json.dumps(report, indent=2))
