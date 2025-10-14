"""
Penetration Testing Suite

Comprehensive penetration testing for the AI Nutritionist application:
- Authentication bypass attempts
- Authorization testing
- Injection attacks (SQL, NoSQL, Command, LDAP)
- Session management vulnerabilities
- Business logic flaws
- API security testing
"""

import os
import json
import time
import asyncio
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
import jwt
import hashlib
import base64
import urllib.parse


class PenetrationTester:
    """Comprehensive penetration testing suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results_dir = Path("tests/security/reports/penetration")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.test_results = []
        
        # Common payloads for injection testing
        self.sql_payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "' UNION SELECT NULL--",
            "'; DROP TABLE users; --",
            "' OR 'a'='a",
            "admin'--",
            "admin' /*",
            "' OR 1=1#",
            "' AND 1=1--",
            "' WAITFOR DELAY '00:00:10'--"
        ]
        
        self.nosql_payloads = [
            {"$ne": None},
            {"$gt": ""},
            {"$regex": ".*"},
            {"$where": "1==1"},
            {"$or": [{"username": "admin"}, {"username": "user"}]},
            {"username": {"$exists": True}},
            {"password": {"$regex": "^admin"}},
        ]
        
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>"
        ]
        
        self.command_injection_payloads = [
            "; ls -la",
            "| whoami",
            "& dir",
            "`id`",
            "$(whoami)",
            "; cat /etc/passwd",
            "| type C:\\Windows\\System32\\drivers\\etc\\hosts",
            "&& net user",
            "; ps aux",
            "| env"
        ]
    
    def test_authentication_bypass(self) -> Dict[str, Any]:
        """Test various authentication bypass techniques."""
        results = {
            "test_type": "authentication_bypass",
            "timestamp": datetime.utcnow().isoformat(),
            "attempts": [],
            "vulnerabilities_found": [],
            "status": "secure"
        }
        
        # Test 1: SQL injection in login
        login_sqli_tests = [
            {"username": payload, "password": "password"} 
            for payload in self.sql_payloads
        ]
        
        for test_data in login_sqli_tests:
            try:
                response = self.session.post(
                    f"{self.base_url}/auth/login",
                    json=test_data,
                    timeout=10
                )
                
                attempt = {
                    "method": "sql_injection_login",
                    "payload": test_data,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "success": False
                }
                
                # Check for successful bypass
                if response.status_code == 200:
                    response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    if 'token' in response_data or 'access_token' in response_data:
                        attempt["success"] = True
                        results["vulnerabilities_found"].append({
                            "type": "sql_injection_authentication_bypass",
                            "severity": "CRITICAL",
                            "payload": test_data,
                            "description": "SQL injection allows authentication bypass"
                        })
                        results["status"] = "vulnerable"
                
                results["attempts"].append(attempt)
                
            except Exception as e:
                results["attempts"].append({
                    "method": "sql_injection_login",
                    "payload": test_data,
                    "error": str(e)
                })
        
        # Test 2: NoSQL injection in login
        nosql_tests = [
            {"username": "admin", "password": payload}
            for payload in self.nosql_payloads
        ]
        
        for test_data in nosql_tests:
            try:
                response = self.session.post(
                    f"{self.base_url}/auth/login",
                    json=test_data,
                    timeout=10
                )
                
                attempt = {
                    "method": "nosql_injection_login",
                    "payload": test_data,
                    "status_code": response.status_code,
                    "success": False
                }
                
                if response.status_code == 200:
                    response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    if 'token' in response_data or 'access_token' in response_data:
                        attempt["success"] = True
                        results["vulnerabilities_found"].append({
                            "type": "nosql_injection_authentication_bypass",
                            "severity": "CRITICAL",
                            "payload": test_data,
                            "description": "NoSQL injection allows authentication bypass"
                        })
                        results["status"] = "vulnerable"
                
                results["attempts"].append(attempt)
                
            except Exception as e:
                results["attempts"].append({
                    "method": "nosql_injection_login",
                    "payload": test_data,
                    "error": str(e)
                })
        
        # Test 3: JWT manipulation
        jwt_bypass_results = self._test_jwt_manipulation()
        results["attempts"].extend(jwt_bypass_results["attempts"])
        results["vulnerabilities_found"].extend(jwt_bypass_results["vulnerabilities"])
        if jwt_bypass_results["vulnerabilities"]:
            results["status"] = "vulnerable"
        
        return results
    
    def _test_jwt_manipulation(self) -> Dict[str, Any]:
        """Test JWT token manipulation vulnerabilities."""
        results = {
            "attempts": [],
            "vulnerabilities": []
        }
        
        # Try to get a valid token first
        try:
            login_response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": "test@example.com", "password": "testpassword"}
            )
            
            if login_response.status_code != 200:
                return results
            
            token_data = login_response.json()
            if 'token' not in token_data and 'access_token' not in token_data:
                return results
                
            original_token = token_data.get('token') or token_data.get('access_token')
            
            # Test 1: Algorithm confusion (HS256 to none)
            try:
                decoded = jwt.decode(original_token, options={"verify_signature": False})
                decoded['alg'] = 'none'
                
                # Create unsigned token
                unsigned_token = jwt.encode(decoded, "", algorithm="none")
                
                # Test with unsigned token
                response = self.session.get(
                    f"{self.base_url}/user/profile",
                    headers={"Authorization": f"Bearer {unsigned_token}"}
                )
                
                attempt = {
                    "method": "jwt_algorithm_confusion",
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
                
                if response.status_code == 200:
                    results["vulnerabilities"].append({
                        "type": "jwt_algorithm_confusion",
                        "severity": "HIGH",
                        "description": "JWT accepts 'none' algorithm, allowing signature bypass"
                    })
                
                results["attempts"].append(attempt)
                
            except Exception as e:
                results["attempts"].append({
                    "method": "jwt_algorithm_confusion",
                    "error": str(e)
                })
            
            # Test 2: JWT payload manipulation
            try:
                decoded = jwt.decode(original_token, options={"verify_signature": False})
                
                # Try to escalate privileges
                decoded['role'] = 'admin'
                decoded['is_admin'] = True
                decoded['permissions'] = ['admin', 'user', 'super_user']
                
                # Re-encode without proper signature
                manipulated_token = jwt.encode(decoded, "weak_secret", algorithm="HS256")
                
                response = self.session.get(
                    f"{self.base_url}/admin/users",
                    headers={"Authorization": f"Bearer {manipulated_token}"}
                )
                
                attempt = {
                    "method": "jwt_payload_manipulation",
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
                
                if response.status_code == 200:
                    results["vulnerabilities"].append({
                        "type": "jwt_payload_manipulation",
                        "severity": "CRITICAL",
                        "description": "JWT payload can be manipulated to escalate privileges"
                    })
                
                results["attempts"].append(attempt)
                
            except Exception as e:
                results["attempts"].append({
                    "method": "jwt_payload_manipulation",
                    "error": str(e)
                })
                
        except Exception as e:
            results["attempts"].append({
                "method": "jwt_testing_setup",
                "error": str(e)
            })
        
        return results
    
    def test_authorization_flaws(self) -> Dict[str, Any]:
        """Test authorization vulnerabilities (IDOR, privilege escalation)."""
        results = {
            "test_type": "authorization_testing",
            "timestamp": datetime.utcnow().isoformat(),
            "attempts": [],
            "vulnerabilities_found": [],
            "status": "secure"
        }
        
        # Test 1: Insecure Direct Object References (IDOR)
        idor_tests = [
            "/user/profile/1",
            "/user/profile/2",
            "/user/profile/admin",
            "/meal-plans/1",
            "/meal-plans/999",
            "/nutrition-data/user/1",
            "/nutrition-data/user/2",
            "/admin/users/1",
            "/admin/users/all"
        ]
        
        for endpoint in idor_tests:
            try:
                # Test without authentication
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                attempt = {
                    "method": "idor_no_auth",
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
                
                if response.status_code == 200:
                    results["vulnerabilities_found"].append({
                        "type": "insecure_direct_object_reference",
                        "severity": "HIGH",
                        "endpoint": endpoint,
                        "description": f"Endpoint {endpoint} accessible without authentication"
                    })
                    results["status"] = "vulnerable"
                
                results["attempts"].append(attempt)
                
                # Test with low-privilege token (if available)
                # This would require setting up test users with different privilege levels
                
            except Exception as e:
                results["attempts"].append({
                    "method": "idor_no_auth",
                    "endpoint": endpoint,
                    "error": str(e)
                })
        
        # Test 2: Horizontal privilege escalation
        user_specific_endpoints = [
            "/user/meal-plans",
            "/user/nutrition-history",
            "/user/preferences",
            "/user/subscriptions"
        ]
        
        for endpoint in user_specific_endpoints:
            try:
                # Test with different user IDs in headers/params
                test_user_ids = ["1", "2", "admin", "999", "../admin", "../../admin"]
                
                for user_id in test_user_ids:
                    response = self.session.get(
                        f"{self.base_url}{endpoint}",
                        params={"user_id": user_id}
                    )
                    
                    attempt = {
                        "method": "horizontal_privilege_escalation",
                        "endpoint": endpoint,
                        "test_user_id": user_id,
                        "status_code": response.status_code,
                        "success": response.status_code == 200
                    }
                    
                    if response.status_code == 200 and user_id in ["admin", "../admin", "../../admin"]:
                        results["vulnerabilities_found"].append({
                            "type": "horizontal_privilege_escalation",
                            "severity": "HIGH",
                            "endpoint": endpoint,
                            "description": f"Can access other users' data via {endpoint}"
                        })
                        results["status"] = "vulnerable"
                    
                    results["attempts"].append(attempt)
                    
            except Exception as e:
                results["attempts"].append({
                    "method": "horizontal_privilege_escalation",
                    "endpoint": endpoint,
                    "error": str(e)
                })
        
        return results
    
    def test_injection_attacks(self) -> Dict[str, Any]:
        """Test various injection attack vectors."""
        results = {
            "test_type": "injection_attacks",
            "timestamp": datetime.utcnow().isoformat(),
            "sql_injection": [],
            "nosql_injection": [],
            "command_injection": [],
            "xss_injection": [],
            "vulnerabilities_found": [],
            "status": "secure"
        }
        
        # Test endpoints that might be vulnerable
        test_endpoints = [
            ("/search", "GET", "q"),
            ("/user/profile", "PUT", "name"),
            ("/meal-plans", "POST", "dietary_restrictions"),
            ("/nutrition/search", "GET", "food_name"),
            ("/feedback", "POST", "message"),
            ("/user/preferences", "PUT", "preferences")
        ]
        
        for endpoint, method, param in test_endpoints:
            # SQL Injection tests
            for payload in self.sql_payloads:
                try:
                    if method == "GET":
                        response = self.session.get(
                            f"{self.base_url}{endpoint}",
                            params={param: payload},
                            timeout=10
                        )
                    else:
                        response = self.session.request(
                            method,
                            f"{self.base_url}{endpoint}",
                            json={param: payload},
                            timeout=10
                        )
                    
                    attempt = {
                        "endpoint": endpoint,
                        "method": method,
                        "param": param,
                        "payload": payload,
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds(),
                        "error_detected": False
                    }
                    
                    # Check for SQL error messages
                    response_text = response.text.lower()
                    sql_errors = [
                        "sql syntax", "mysql", "postgresql", "sqlite", "oracle",
                        "syntax error", "unterminated quoted string",
                        "invalid input syntax", "column", "table"
                    ]
                    
                    if any(error in response_text for error in sql_errors):
                        attempt["error_detected"] = True
                        results["vulnerabilities_found"].append({
                            "type": "sql_injection",
                            "severity": "CRITICAL",
                            "endpoint": endpoint,
                            "payload": payload,
                            "description": "SQL error messages detected, possible injection point"
                        })
                        results["status"] = "vulnerable"
                    
                    # Check for time-based SQL injection
                    if response.elapsed.total_seconds() > 8:  # WAITFOR DELAY payload
                        attempt["time_delay_detected"] = True
                        results["vulnerabilities_found"].append({
                            "type": "time_based_sql_injection",
                            "severity": "CRITICAL",
                            "endpoint": endpoint,
                            "payload": payload,
                            "description": "Time delay detected, possible blind SQL injection"
                        })
                        results["status"] = "vulnerable"
                    
                    results["sql_injection"].append(attempt)
                    
                except Exception as e:
                    results["sql_injection"].append({
                        "endpoint": endpoint,
                        "payload": payload,
                        "error": str(e)
                    })
            
            # XSS tests
            for payload in self.xss_payloads[:5]:  # Limit XSS tests
                try:
                    if method == "GET":
                        response = self.session.get(
                            f"{self.base_url}{endpoint}",
                            params={param: payload},
                            timeout=10
                        )
                    else:
                        response = self.session.request(
                            method,
                            f"{self.base_url}{endpoint}",
                            json={param: payload},
                            timeout=10
                        )
                    
                    attempt = {
                        "endpoint": endpoint,
                        "method": method,
                        "param": param,
                        "payload": payload,
                        "status_code": response.status_code,
                        "reflected": False
                    }
                    
                    # Check if payload is reflected in response
                    if payload in response.text:
                        attempt["reflected"] = True
                        results["vulnerabilities_found"].append({
                            "type": "reflected_xss",
                            "severity": "HIGH",
                            "endpoint": endpoint,
                            "payload": payload,
                            "description": "XSS payload reflected in response"
                        })
                        results["status"] = "vulnerable"
                    
                    results["xss_injection"].append(attempt)
                    
                except Exception as e:
                    results["xss_injection"].append({
                        "endpoint": endpoint,
                        "payload": payload,
                        "error": str(e)
                    })
            
            # Command injection tests (for specific endpoints that might execute commands)
            if endpoint in ["/admin/system", "/tools/export", "/debug"]:
                for payload in self.command_injection_payloads[:3]:  # Limit command injection tests
                    try:
                        if method == "GET":
                            response = self.session.get(
                                f"{self.base_url}{endpoint}",
                                params={param: payload},
                                timeout=15
                            )
                        else:
                            response = self.session.request(
                                method,
                                f"{self.base_url}{endpoint}",
                                json={param: payload},
                                timeout=15
                            )
                        
                        attempt = {
                            "endpoint": endpoint,
                            "method": method,
                            "param": param,
                            "payload": payload,
                            "status_code": response.status_code,
                            "command_executed": False
                        }
                        
                        # Check for command execution indicators
                        response_text = response.text.lower()
                        command_indicators = [
                            "root:", "administrator", "c:\\", "/bin", "/usr",
                            "uid=", "gid=", "groups=", "windows", "linux"
                        ]
                        
                        if any(indicator in response_text for indicator in command_indicators):
                            attempt["command_executed"] = True
                            results["vulnerabilities_found"].append({
                                "type": "command_injection",
                                "severity": "CRITICAL",
                                "endpoint": endpoint,
                                "payload": payload,
                                "description": "Command execution indicators detected"
                            })
                            results["status"] = "vulnerable"
                        
                        results["command_injection"].append(attempt)
                        
                    except Exception as e:
                        results["command_injection"].append({
                            "endpoint": endpoint,
                            "payload": payload,
                            "error": str(e)
                        })
        
        return results
    
    def test_session_management(self) -> Dict[str, Any]:
        """Test session management vulnerabilities."""
        results = {
            "test_type": "session_management",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "vulnerabilities_found": [],
            "status": "secure"
        }
        
        # Test 1: Session fixation
        try:
            # Get session before login
            pre_login_response = self.session.get(f"{self.base_url}/")
            pre_login_cookies = self.session.cookies.get_dict()
            
            # Login
            login_response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": "test@example.com", "password": "testpassword"}
            )
            
            # Get session after login
            post_login_cookies = self.session.cookies.get_dict()
            
            session_changed = pre_login_cookies != post_login_cookies
            
            test_result = {
                "test": "session_fixation",
                "session_changed_on_login": session_changed,
                "pre_login_cookies": len(pre_login_cookies),
                "post_login_cookies": len(post_login_cookies)
            }
            
            if not session_changed and pre_login_cookies:
                results["vulnerabilities_found"].append({
                    "type": "session_fixation",
                    "severity": "MEDIUM",
                    "description": "Session ID not changed after authentication"
                })
                results["status"] = "vulnerable"
            
            results["tests"].append(test_result)
            
        except Exception as e:
            results["tests"].append({
                "test": "session_fixation",
                "error": str(e)
            })
        
        # Test 2: Session timeout
        try:
            # This would require longer-running tests
            # For now, just check if session timeout is configured
            response = self.session.get(f"{self.base_url}/user/profile")
            
            # Check for session timeout headers
            timeout_headers = [
                "session-timeout", "x-session-timeout",
                "cache-control", "expires"
            ]
            
            has_timeout_config = any(
                header in response.headers 
                for header in timeout_headers
            )
            
            results["tests"].append({
                "test": "session_timeout_configuration",
                "timeout_headers_present": has_timeout_config,
                "headers": dict(response.headers)
            })
            
            if not has_timeout_config:
                results["vulnerabilities_found"].append({
                    "type": "missing_session_timeout",
                    "severity": "LOW",
                    "description": "No session timeout configuration detected"
                })
        
        except Exception as e:
            results["tests"].append({
                "test": "session_timeout_configuration",
                "error": str(e)
            })
        
        return results
    
    def generate_penetration_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive penetration test report."""
        report = {
            "test_suite": "penetration_testing",
            "timestamp": datetime.utcnow().isoformat(),
            "target": self.base_url,
            "tests": {},
            "summary": {
                "total_vulnerabilities": 0,
                "critical_vulnerabilities": 0,
                "high_vulnerabilities": 0,
                "medium_vulnerabilities": 0,
                "low_vulnerabilities": 0
            },
            "recommendations": []
        }
        
        # Run all penetration tests
        test_methods = [
            ("authentication_bypass", self.test_authentication_bypass),
            ("authorization_flaws", self.test_authorization_flaws),
            ("injection_attacks", self.test_injection_attacks),
            ("session_management", self.test_session_management)
        ]
        
        for test_name, test_method in test_methods:
            try:
                test_result = test_method()
                report["tests"][test_name] = test_result
                
                # Count vulnerabilities
                vulnerabilities = test_result.get("vulnerabilities_found", [])
                report["summary"]["total_vulnerabilities"] += len(vulnerabilities)
                
                for vuln in vulnerabilities:
                    severity = vuln.get("severity", "").upper()
                    if severity == "CRITICAL":
                        report["summary"]["critical_vulnerabilities"] += 1
                    elif severity == "HIGH":
                        report["summary"]["high_vulnerabilities"] += 1
                    elif severity == "MEDIUM":
                        report["summary"]["medium_vulnerabilities"] += 1
                    elif severity == "LOW":
                        report["summary"]["low_vulnerabilities"] += 1
                        
            except Exception as e:
                report["tests"][test_name] = {
                    "error": str(e),
                    "status": "failed"
                }
        
        # Generate recommendations
        report["recommendations"] = self._generate_pentest_recommendations(report)
        
        # Save report
        report_path = self.results_dir / f"penetration_test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        report["report_path"] = str(report_path)
        return report
    
    def _generate_pentest_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate penetration testing recommendations."""
        recommendations = []
        
        summary = report["summary"]
        
        if summary["critical_vulnerabilities"] > 0:
            recommendations.append("CRITICAL: Fix all critical vulnerabilities immediately before production deployment")
        
        if summary["high_vulnerabilities"] > 0:
            recommendations.append("HIGH PRIORITY: Address all high-severity vulnerabilities")
        
        # Test-specific recommendations
        tests = report.get("tests", {})
        
        auth_test = tests.get("authentication_bypass", {})
        if auth_test.get("status") == "vulnerable":
            recommendations.append("Implement stronger authentication controls and input validation")
        
        authz_test = tests.get("authorization_flaws", {})
        if authz_test.get("status") == "vulnerable":
            recommendations.append("Review and strengthen authorization checks for all endpoints")
        
        injection_test = tests.get("injection_attacks", {})
        if injection_test.get("status") == "vulnerable":
            recommendations.append("Implement comprehensive input validation and parameterized queries")
        
        session_test = tests.get("session_management", {})
        if session_test.get("status") == "vulnerable":
            recommendations.append("Strengthen session management controls")
        
        if summary["total_vulnerabilities"] == 0:
            recommendations.append("Good security posture - continue regular penetration testing")
        
        return recommendations


# Test Classes
class TestPenetrationTesting:
    """Penetration testing test cases."""
    
    @pytest.fixture
    def pen_tester(self):
        """Penetration tester fixture."""
        return PenetrationTester()
    
    def test_authentication_bypass_attempts(self, pen_tester):
        """Test authentication bypass vulnerabilities."""
        results = pen_tester.test_authentication_bypass()
        
        assert results["test_type"] == "authentication_bypass"
        assert "attempts" in results
        assert "vulnerabilities_found" in results
        
        # Fail if critical authentication bypasses found
        critical_bypasses = [
            v for v in results["vulnerabilities_found"]
            if v.get("severity") == "CRITICAL"
        ]
        
        if critical_bypasses:
            pytest.fail(f"CRITICAL: Authentication bypass vulnerabilities found: {len(critical_bypasses)}")
    
    def test_authorization_flaws(self, pen_tester):
        """Test authorization vulnerabilities."""
        results = pen_tester.test_authorization_flaws()
        
        assert results["test_type"] == "authorization_testing"
        
        # Check for high-severity authorization issues
        high_severity_issues = [
            v for v in results["vulnerabilities_found"]
            if v.get("severity") in ["CRITICAL", "HIGH"]
        ]
        
        if high_severity_issues:
            print(f"WARNING: {len(high_severity_issues)} high-severity authorization issues found")
    
    def test_injection_vulnerabilities(self, pen_tester):
        """Test injection attack vulnerabilities."""
        results = pen_tester.test_injection_attacks()
        
        assert results["test_type"] == "injection_attacks"
        
        # Fail on critical injection vulnerabilities
        critical_injections = [
            v for v in results["vulnerabilities_found"]
            if v.get("severity") == "CRITICAL"
        ]
        
        if critical_injections:
            pytest.fail(f"CRITICAL: Injection vulnerabilities found: {len(critical_injections)}")
    
    def test_session_management_flaws(self, pen_tester):
        """Test session management vulnerabilities."""
        results = pen_tester.test_session_management()
        
        assert results["test_type"] == "session_management"
        
        # Check for session management issues
        session_issues = results["vulnerabilities_found"]
        high_severity_session_issues = [
            v for v in session_issues
            if v.get("severity") in ["CRITICAL", "HIGH"]
        ]
        
        if high_severity_session_issues:
            print(f"WARNING: {len(high_severity_session_issues)} session management issues found")
    
    def test_comprehensive_penetration_test(self, pen_tester):
        """Run comprehensive penetration test suite."""
        report = pen_tester.generate_penetration_test_report()
        
        assert "test_suite" in report
        assert "summary" in report
        assert "tests" in report
        assert "recommendations" in report
        
        # Verify report file
        assert Path(report["report_path"]).exists()
        
        # Security gates
        summary = report["summary"]
        
        if summary["critical_vulnerabilities"] > 0:
            pytest.fail(f"CRITICAL: {summary['critical_vulnerabilities']} critical vulnerabilities found")
        
        if summary["high_vulnerabilities"] > 3:
            pytest.fail(f"Too many high-severity vulnerabilities: {summary['high_vulnerabilities']}")
        
        # Print summary
        print(f"\n=== PENETRATION TEST SUMMARY ===")
        print(f"Target: {report['target']}")
        print(f"Total Vulnerabilities: {summary['total_vulnerabilities']}")
        print(f"Critical: {summary['critical_vulnerabilities']}")
        print(f"High: {summary['high_vulnerabilities']}")
        print(f"Medium: {summary['medium_vulnerabilities']}")
        print(f"Low: {summary['low_vulnerabilities']}")
        print(f"Report: {report['report_path']}")
    
    @pytest.mark.integration
    def test_security_gate_penetration(self, pen_tester):
        """Security gate for penetration testing in CI/CD."""
        report = pen_tester.generate_penetration_test_report()
        
        # Define security gates
        CRITICAL_THRESHOLD = 0
        HIGH_THRESHOLD = 2
        TOTAL_THRESHOLD = 10
        
        summary = report["summary"]
        
        failures = []
        
        if summary["critical_vulnerabilities"] > CRITICAL_THRESHOLD:
            failures.append(f"Critical vulnerabilities: {summary['critical_vulnerabilities']} > {CRITICAL_THRESHOLD}")
        
        if summary["high_vulnerabilities"] > HIGH_THRESHOLD:
            failures.append(f"High-severity vulnerabilities: {summary['high_vulnerabilities']} > {HIGH_THRESHOLD}")
        
        if summary["total_vulnerabilities"] > TOTAL_THRESHOLD:
            failures.append(f"Total vulnerabilities: {summary['total_vulnerabilities']} > {TOTAL_THRESHOLD}")
        
        if failures:
            pytest.fail(f"Penetration testing security gate failures: {'; '.join(failures)}")


if __name__ == "__main__":
    tester = PenetrationTester()
    report = tester.generate_penetration_test_report()
    print(json.dumps(report, indent=2))
