"""
GDPR Compliance Testing Suite

Tests for General Data Protection Regulation (GDPR) compliance
in the AI Nutritionist application handling personal data.
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


class GDPRComplianceTester:
    """GDPR compliance testing and validation."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results_dir = Path("tests/security/reports/compliance")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # GDPR data subject rights
        self.data_subject_rights = [
            "right_to_information",
            "right_of_access",
            "right_to_rectification",
            "right_to_erasure",
            "right_to_restrict_processing",
            "right_to_data_portability",
            "right_to_object",
            "rights_in_automated_decision_making"
        ]
    
    def test_lawful_basis_for_processing(self) -> Dict[str, Any]:
        """Test lawful basis for data processing (Article 6)."""
        results = {
            "test_type": "lawful_basis_processing",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "violations": [],
            "status": "compliant"
        }
        
        # Test 1: Consent mechanisms
        consent_test = self._test_consent_mechanisms()
        results["tests"].append(consent_test)
        if not consent_test["compliant"]:
            results["violations"].append({
                "article": "Article 6 & 7 - Consent",
                "description": "Valid consent must be freely given, specific, informed, and unambiguous",
                "severity": "HIGH"
            })
            results["status"] = "non_compliant"
        
        # Test 2: Privacy policy and transparency
        privacy_test = self._test_privacy_transparency()
        results["tests"].append(privacy_test)
        if not privacy_test["compliant"]:
            results["violations"].append({
                "article": "Article 12-14 - Transparency",
                "description": "Privacy information must be provided in clear and plain language",
                "severity": "MEDIUM"
            })
            results["status"] = "non_compliant"
        
        return results
    
    def _test_consent_mechanisms(self) -> Dict[str, Any]:
        """Test consent collection and management."""
        test_result = {
            "test_name": "consent_mechanisms",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test 1: Registration process consent
            registration_response = self.session.post(
                f"{self.base_url}/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "TestPassword123!",
                    "name": "Test User"
                }
            )
            
            if registration_response.status_code == 200:
                # Check if consent is required during registration
                registration_data = registration_response.json()
                if "consent_required" not in registration_data:
                    test_result["findings"].append("No consent mechanism in registration process")
                    test_result["compliant"] = False
            
            # Test 2: Consent management endpoints
            consent_endpoints = [
                "/privacy/consent",
                "/user/consent-preferences",
                "/privacy/manage-consent"
            ]
            
            for endpoint in consent_endpoints:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 404:
                    test_result["findings"].append(f"No consent management endpoint: {endpoint}")
            
            # Test 3: Granular consent options
            consent_response = self.session.get(f"{self.base_url}/privacy/consent")
            if consent_response.status_code == 200:
                consent_data = consent_response.json()
                
                # Check for granular consent options
                required_consent_types = [
                    "essential_cookies",
                    "analytics_cookies",
                    "marketing_communications",
                    "data_processing",
                    "third_party_sharing"
                ]
                
                for consent_type in required_consent_types:
                    if consent_type not in consent_data:
                        test_result["findings"].append(f"Missing consent option: {consent_type}")
        
        except Exception as e:
            test_result["compliant"] = False
            test_result["findings"].append(f"Error testing consent mechanisms: {e}")
        
        return test_result
    
    def _test_privacy_transparency(self) -> Dict[str, Any]:
        """Test privacy policy and transparency requirements."""
        test_result = {
            "test_name": "privacy_transparency",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test 1: Privacy policy accessibility
            privacy_response = self.session.get(f"{self.base_url}/privacy-policy")
            
            if privacy_response.status_code != 200:
                test_result["compliant"] = False
                test_result["findings"].append("Privacy policy not accessible")
            else:
                privacy_content = privacy_response.text.lower()
                
                # Check for required GDPR information
                required_sections = [
                    "data controller", "lawful basis", "data retention",
                    "data subject rights", "contact information", "dpo"
                ]
                
                for section in required_sections:
                    if section not in privacy_content:
                        test_result["findings"].append(f"Privacy policy missing: {section}")
            
            # Test 2: Cookie policy
            cookie_response = self.session.get(f"{self.base_url}/cookie-policy")
            if cookie_response.status_code != 200:
                test_result["findings"].append("Cookie policy not accessible")
            
            # Test 3: Data processing information
            processing_response = self.session.get(f"{self.base_url}/data-processing")
            if processing_response.status_code != 200:
                test_result["findings"].append("Data processing information not accessible")
        
        except Exception as e:
            test_result["compliant"] = False
            test_result["findings"].append(f"Error testing privacy transparency: {e}")
        
        return test_result
    
    def test_data_subject_rights(self) -> Dict[str, Any]:
        """Test data subject rights implementation (Articles 15-22)."""
        results = {
            "test_type": "data_subject_rights",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "violations": [],
            "status": "compliant"
        }
        
        # Test each data subject right
        for right in self.data_subject_rights:
            right_test = self._test_individual_right(right)
            results["tests"].append(right_test)
            
            if not right_test["compliant"]:
                results["violations"].append({
                    "article": f"Article {self._get_article_number(right)}",
                    "description": f"Data subject {right.replace('_', ' ')} not properly implemented",
                    "severity": "HIGH"
                })
                results["status"] = "non_compliant"
        
        return results
    
    def _test_individual_right(self, right: str) -> Dict[str, Any]:
        """Test individual data subject right."""
        test_result = {
            "test_name": right,
            "compliant": True,
            "findings": []
        }
        
        try:
            if right == "right_of_access":
                # Test data access request
                response = self.session.get(f"{self.base_url}/privacy/data-export")
                if response.status_code == 404:
                    test_result["compliant"] = False
                    test_result["findings"].append("No data access/export endpoint")
                
            elif right == "right_to_erasure":
                # Test data deletion request
                response = self.session.delete(f"{self.base_url}/privacy/delete-account")
                if response.status_code == 404:
                    test_result["compliant"] = False
                    test_result["findings"].append("No data deletion endpoint")
                
            elif right == "right_to_rectification":
                # Test data correction mechanisms
                response = self.session.get(f"{self.base_url}/user/profile/edit")
                if response.status_code == 404:
                    test_result["findings"].append("No data rectification mechanism")
                
            elif right == "right_to_data_portability":
                # Test data portability
                response = self.session.get(f"{self.base_url}/privacy/data-export?format=json")
                if response.status_code == 404:
                    test_result["compliant"] = False
                    test_result["findings"].append("No data portability endpoint")
                
            elif right == "right_to_object":
                # Test objection to processing
                response = self.session.post(f"{self.base_url}/privacy/object-processing")
                if response.status_code == 404:
                    test_result["compliant"] = False
                    test_result["findings"].append("No processing objection mechanism")
                
            elif right == "right_to_restrict_processing":
                # Test processing restriction
                response = self.session.post(f"{self.base_url}/privacy/restrict-processing")
                if response.status_code == 404:
                    test_result["compliant"] = False
                    test_result["findings"].append("No processing restriction mechanism")
                    
            elif right == "rights_in_automated_decision_making":
                # Test automated decision-making rights
                response = self.session.get(f"{self.base_url}/privacy/automated-decisions")
                if response.status_code == 404:
                    test_result["findings"].append("No automated decision-making information")
        
        except Exception as e:
            test_result["compliant"] = False
            test_result["findings"].append(f"Error testing {right}: {e}")
        
        return test_result
    
    def _get_article_number(self, right: str) -> str:
        """Get GDPR article number for data subject right."""
        article_mapping = {
            "right_to_information": "13-14",
            "right_of_access": "15",
            "right_to_rectification": "16",
            "right_to_erasure": "17",
            "right_to_restrict_processing": "18",
            "right_to_data_portability": "20",
            "right_to_object": "21",
            "rights_in_automated_decision_making": "22"
        }
        return article_mapping.get(right, "Unknown")
    
    def test_data_protection_by_design(self) -> Dict[str, Any]:
        """Test data protection by design and by default (Article 25)."""
        results = {
            "test_type": "data_protection_by_design",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "violations": [],
            "status": "compliant"
        }
        
        # Test 1: Data minimization
        minimization_test = self._test_data_minimization()
        results["tests"].append(minimization_test)
        if not minimization_test["compliant"]:
            results["violations"].append({
                "article": "Article 5(1)(c) - Data Minimization",
                "description": "Personal data should be adequate, relevant and limited to what is necessary",
                "severity": "MEDIUM"
            })
            results["status"] = "non_compliant"
        
        # Test 2: Privacy by default settings
        privacy_default_test = self._test_privacy_by_default()
        results["tests"].append(privacy_default_test)
        if not privacy_default_test["compliant"]:
            results["violations"].append({
                "article": "Article 25(2) - Privacy by Default",
                "description": "Privacy-friendly settings should be default",
                "severity": "MEDIUM"
            })
            results["status"] = "non_compliant"
        
        return results
    
    def _test_data_minimization(self) -> Dict[str, Any]:
        """Test data minimization principle."""
        test_result = {
            "test_name": "data_minimization",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test registration form
            response = self.session.get(f"{self.base_url}/auth/register")
            if response.status_code == 200:
                # Check if unnecessary fields are required
                form_data = response.text.lower()
                
                unnecessary_fields = [
                    "social_security", "passport", "driver_license",
                    "mother_maiden_name", "full_address", "phone_number"
                ]
                
                for field in unnecessary_fields:
                    if field in form_data and "required" in form_data:
                        test_result["findings"].append(f"Unnecessary required field: {field}")
            
            # Test user profile data collection
            profile_response = self.session.get(f"{self.base_url}/user/profile")
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                # Check for excessive data collection
                if len(profile_data) > 20:  # Arbitrary threshold
                    test_result["findings"].append("Potentially excessive data collection in user profile")
        
        except Exception as e:
            test_result["findings"].append(f"Error testing data minimization: {e}")
        
        return test_result
    
    def _test_privacy_by_default(self) -> Dict[str, Any]:
        """Test privacy by default settings."""
        test_result = {
            "test_name": "privacy_by_default",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Test default privacy settings for new users
            settings_response = self.session.get(f"{self.base_url}/user/privacy-settings")
            if settings_response.status_code == 200:
                settings = settings_response.json()
                
                # Check that privacy-friendly options are default
                privacy_settings = [
                    "data_sharing_enabled",
                    "marketing_emails_enabled",
                    "analytics_tracking_enabled",
                    "third_party_data_sharing"
                ]
                
                for setting in privacy_settings:
                    if settings.get(setting, True):  # Default should be False
                        test_result["findings"].append(f"Non-privacy-friendly default: {setting}")
                        test_result["compliant"] = False
        
        except Exception as e:
            test_result["findings"].append(f"Error testing privacy by default: {e}")
        
        return test_result
    
    def test_data_breach_procedures(self) -> Dict[str, Any]:
        """Test data breach notification procedures (Articles 33-34)."""
        results = {
            "test_type": "data_breach_procedures",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "violations": [],
            "status": "compliant"
        }
        
        # Test breach detection mechanisms
        breach_detection_test = self._test_breach_detection()
        results["tests"].append(breach_detection_test)
        if not breach_detection_test["compliant"]:
            results["violations"].append({
                "article": "Article 33 - Breach Notification",
                "description": "Breach detection and notification procedures must be implemented",
                "severity": "HIGH"
            })
            results["status"] = "non_compliant"
        
        # Test breach notification endpoints
        notification_test = self._test_breach_notification()
        results["tests"].append(notification_test)
        if not notification_test["compliant"]:
            results["violations"].append({
                "article": "Article 34 - Data Subject Notification",
                "description": "Data subjects must be notified of high-risk breaches",
                "severity": "HIGH"
            })
            results["status"] = "non_compliant"
        
        return results
    
    def _test_breach_detection(self) -> Dict[str, Any]:
        """Test breach detection mechanisms."""
        test_result = {
            "test_name": "breach_detection",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Check for security monitoring endpoints
            monitoring_endpoints = [
                "/admin/security-alerts",
                "/admin/breach-detection",
                "/security/incidents"
            ]
            
            endpoint_found = False
            for endpoint in monitoring_endpoints:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code != 404:
                    endpoint_found = True
                    break
            
            if not endpoint_found:
                test_result["compliant"] = False
                test_result["findings"].append("No breach detection monitoring endpoints found")
            
            # Check for incident response procedures documentation
            incident_response = self.session.get(f"{self.base_url}/security/incident-response")
            if incident_response.status_code == 404:
                test_result["findings"].append("No incident response procedures documentation")
        
        except Exception as e:
            test_result["findings"].append(f"Error testing breach detection: {e}")
        
        return test_result
    
    def _test_breach_notification(self) -> Dict[str, Any]:
        """Test breach notification mechanisms."""
        test_result = {
            "test_name": "breach_notification",
            "compliant": True,
            "findings": []
        }
        
        try:
            # Check for breach notification endpoints
            notification_response = self.session.get(f"{self.base_url}/privacy/breach-notifications")
            if notification_response.status_code == 404:
                test_result["compliant"] = False
                test_result["findings"].append("No breach notification endpoint")
            
            # Check for DPA contact information
            dpa_response = self.session.get(f"{self.base_url}/privacy/dpa-contact")
            if dpa_response.status_code == 404:
                test_result["findings"].append("No Data Protection Authority contact information")
        
        except Exception as e:
            test_result["findings"].append(f"Error testing breach notification: {e}")
        
        return test_result
    
    def generate_gdpr_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive GDPR compliance report."""
        report = {
            "compliance_framework": "GDPR",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {},
            "overall_compliance": "compliant",
            "violations": [],
            "recommendations": []
        }
        
        # Run all GDPR tests
        test_methods = [
            ("lawful_basis_processing", self.test_lawful_basis_for_processing),
            ("data_subject_rights", self.test_data_subject_rights),
            ("data_protection_by_design", self.test_data_protection_by_design),
            ("data_breach_procedures", self.test_data_breach_procedures)
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
        report["recommendations"] = self._generate_gdpr_recommendations(report)
        
        # Save report
        report_path = self.results_dir / f"gdpr_compliance_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        report["report_path"] = str(report_path)
        return report
    
    def _generate_gdpr_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate GDPR compliance recommendations."""
        recommendations = []
        
        if report["overall_compliance"] == "non_compliant":
            recommendations.append("CRITICAL: Address all GDPR violations before processing EU personal data")
        
        violations = report.get("violations", [])
        
        # Category-specific recommendations
        if any("consent" in v.get("description", "").lower() for v in violations):
            recommendations.append("Implement compliant consent mechanisms with granular options")
        
        if any("data subject rights" in v.get("description", "").lower() for v in violations):
            recommendations.append("Implement all data subject rights with automated fulfillment where possible")
        
        if any("transparency" in v.get("description", "").lower() for v in violations):
            recommendations.append("Update privacy policy and ensure transparency in data processing")
        
        if any("breach" in v.get("description", "").lower() for v in violations):
            recommendations.append("Establish robust data breach detection and notification procedures")
        
        # General recommendations
        recommendations.extend([
            "Conduct regular GDPR compliance assessments",
            "Implement Data Protection Impact Assessments (DPIAs) for high-risk processing",
            "Appoint a Data Protection Officer (DPO) if required",
            "Maintain records of processing activities",
            "Implement privacy by design and by default principles",
            "Establish legal basis for all data processing activities",
            "Regular staff training on GDPR requirements"
        ])
        
        return recommendations


# Test Classes
class TestGDPRCompliance:
    """GDPR compliance test cases."""
    
    @pytest.fixture
    def gdpr_tester(self):
        """GDPR compliance tester fixture."""
        return GDPRComplianceTester()
    
    def test_lawful_basis_compliance(self, gdpr_tester):
        """Test lawful basis for processing compliance."""
        results = gdpr_tester.test_lawful_basis_for_processing()
        
        assert results["test_type"] == "lawful_basis_processing"
        
        # Fail if violations found
        violations = results["violations"]
        high_violations = [v for v in violations if v.get("severity") in ["HIGH", "CRITICAL"]]
        
        if high_violations:
            pytest.fail(f"High-severity GDPR violations found: {len(high_violations)}")
    
    def test_data_subject_rights_compliance(self, gdpr_tester):
        """Test data subject rights compliance."""
        results = gdpr_tester.test_data_subject_rights()
        
        assert results["test_type"] == "data_subject_rights"
        
        if results["status"] == "non_compliant":
            violations = [v["description"] for v in results["violations"]]
            print(f"DATA SUBJECT RIGHTS VIOLATIONS: {violations}")
    
    def test_data_protection_by_design_compliance(self, gdpr_tester):
        """Test data protection by design compliance."""
        results = gdpr_tester.test_data_protection_by_design()
        
        assert results["test_type"] == "data_protection_by_design"
        
        if results["status"] == "non_compliant":
            print("WARNING: Data protection by design issues found")
    
    def test_comprehensive_gdpr_compliance(self, gdpr_tester):
        """Test comprehensive GDPR compliance."""
        report = gdpr_tester.generate_gdpr_compliance_report()
        
        assert "compliance_framework" in report
        assert report["compliance_framework"] == "GDPR"
        
        # Verify report file
        assert Path(report["report_path"]).exists()
        
        # Compliance gate
        if report["overall_compliance"] == "non_compliant":
            violations_summary = []
            for violation in report["violations"]:
                violations_summary.append(f"{violation['severity']}: {violation['description']}")
            
            pytest.fail(f"GDPR compliance violations found: {'; '.join(violations_summary)}")
        
        print(f"\n=== GDPR COMPLIANCE SUMMARY ===")
        print(f"Overall Compliance: {report['overall_compliance']}")
        print(f"Total Violations: {len(report['violations'])}")
        print(f"Report: {report['report_path']}")


if __name__ == "__main__":
    tester = GDPRComplianceTester()
    report = tester.generate_gdpr_compliance_report()
    print(json.dumps(report, indent=2))
