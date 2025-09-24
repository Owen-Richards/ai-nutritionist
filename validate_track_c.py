#!/usr/bin/env python3
"""
Track C - Widgets (iOS/Android) Validation Script

Comprehensive validation of all Track C components including:
- Widget API functionality
- ETag caching behavior
- Contract compliance
- Mobile widget templates
- Performance characteristics

Author: AI Nutritionist Development Team
Date: September 2025
"""

import asyncio
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)


class TrackCValidator:
    """Comprehensive validator for Track C implementation."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.start_time = None
    
    def log_result(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test result with formatting."""
        status = f"{Fore.GREEN}✅ PASS" if success else f"{Fore.RED}❌ FAIL"
        print(f"{status} {test_name}: {message}{Style.RESET_ALL}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def print_header(self, title: str):
        """Print formatted section header."""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{title}")
        print(f"{'='*60}{Style.RESET_ALL}")
    
    async def validate_domain_models(self):
        """Validate gamification domain models."""
        self.print_header("🎯 TRACK C COMPONENT 1: Domain Models")
        
        try:
            from src.models.gamification import (
                AdherenceRing, Streak, Challenge, GamificationSummary,
                AdherenceLevel, ChallengeType, ChallengeStatus,
                calculate_adherence_level, get_ring_color
            )
            
            # Test AdherenceRing validation
            try:
                ring = AdherenceRing(
                    percentage=85.5,
                    level=AdherenceLevel.HIGH,
                    trend="up",
                    days_tracked=7,
                    target_percentage=80.0,
                    ring_color="#39C0ED"
                )
                self.log_result("Domain Models", True, "AdherenceRing model validation working")
            except Exception as e:
                self.log_result("Domain Models", False, f"AdherenceRing validation failed: {e}")
            
            # Test helper functions
            level = calculate_adherence_level(85.5)
            color = get_ring_color(level)
            
            if level == AdherenceLevel.HIGH and color == "#39C0ED":
                self.log_result("Helper Functions", True, "Adherence level calculation and color mapping working")
            else:
                self.log_result("Helper Functions", False, "Adherence helper functions not working correctly")
                
        except ImportError as e:
            self.log_result("Domain Models", False, f"Import failed: {e}")
    
    async def validate_service_layer(self):
        """Validate gamification service layer."""
        self.print_header("⚙️ TRACK C COMPONENT 2: Service Layer")
        
        try:
            from src.services.gamification.service import GamificationService
            
            service = GamificationService()
            user_id = uuid4()
            
            # Test gamification summary generation
            summary = await service.get_gamification_summary(user_id)
            
            if summary.user_id == user_id:
                self.log_result("Service Layer", True, "GamificationService summary generation working")
            else:
                self.log_result("Service Layer", False, "GamificationService not returning correct user_id")
            
            # Test cache headers generation
            cache_headers = await service.get_cache_headers(summary)
            required_headers = ["ETag", "Cache-Control", "Expires", "Last-Modified"]
            
            if all(header in cache_headers for header in required_headers):
                self.log_result("Cache Headers", True, "Cache headers generation working")
            else:
                missing = [h for h in required_headers if h not in cache_headers]
                self.log_result("Cache Headers", False, f"Missing cache headers: {missing}")
                
        except Exception as e:
            self.log_result("Service Layer", False, f"Service layer validation failed: {e}")
    
    async def validate_api_endpoints(self):
        """Validate gamification API endpoints."""
        self.print_header("🌐 TRACK C COMPONENT 3: Widget API")
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.base_url}/v1/gamification/health")
            
            if response.status_code == 200:
                health_data = response.json()
                if "status" in health_data and health_data["status"] == "healthy":
                    self.log_result("Health Endpoint", True, "Health check endpoint working")
                else:
                    self.log_result("Health Endpoint", False, "Health endpoint not returning healthy status")
            else:
                self.log_result("Health Endpoint", False, f"Health endpoint returned {response.status_code}")
            
            # Test widget contract endpoint
            response = requests.get(f"{self.base_url}/v1/gamification/contract")
            
            if response.status_code == 200:
                contract_data = response.json()
                required_fields = ["schema_version", "required_fields", "cache_requirements"]
                
                if all(field in contract_data for field in required_fields):
                    self.log_result("Contract Endpoint", True, "Widget contract endpoint working")
                else:
                    missing = [f for f in required_fields if f not in contract_data]
                    self.log_result("Contract Endpoint", False, f"Missing contract fields: {missing}")
            else:
                self.log_result("Contract Endpoint", False, f"Contract endpoint returned {response.status_code}")
            
            # Test gamification summary endpoint
            user_id = str(uuid4())
            response = requests.get(f"{self.base_url}/v1/gamification/summary?user_id={user_id}")
            
            if response.status_code == 200:
                summary_data = response.json()
                required_fields = ["user_id", "adherence_ring", "current_streak", "widget_deep_link"]
                
                if all(field in summary_data for field in required_fields):
                    self.log_result("Summary Endpoint", True, "Gamification summary endpoint working")
                    
                    # Validate adherence ring structure
                    ring = summary_data["adherence_ring"]
                    ring_fields = ["percentage", "level", "trend", "ring_color"]
                    
                    if all(field in ring for field in ring_fields):
                        self.log_result("Ring Structure", True, "Adherence ring structure valid")
                    else:
                        missing = [f for f in ring_fields if f not in ring]
                        self.log_result("Ring Structure", False, f"Missing ring fields: {missing}")
                else:
                    missing = [f for f in required_fields if f not in summary_data]
                    self.log_result("Summary Endpoint", False, f"Missing summary fields: {missing}")
            else:
                self.log_result("Summary Endpoint", False, f"Summary endpoint returned {response.status_code}")
                
        except Exception as e:
            self.log_result("API Endpoints", False, f"API validation failed: {e}")
    
    async def validate_caching_behavior(self):
        """Validate ETag caching behavior."""
        self.print_header("🗄️ TRACK C COMPONENT 4: ETag Caching")
        
        try:
            user_id = str(uuid4())
            url = f"{self.base_url}/v1/gamification/summary?user_id={user_id}"
            
            # First request
            response1 = requests.get(url)
            
            if response1.status_code == 200:
                # Check for cache headers
                headers = response1.headers
                cache_headers = ["etag", "cache-control", "last-modified"]
                
                if all(header in headers for header in cache_headers):
                    self.log_result("Cache Headers", True, "Cache headers present in response")
                    
                    etag = headers.get("etag")
                    
                    # Second request with If-None-Match
                    response2 = requests.get(url, headers={"If-None-Match": etag})
                    
                    if response2.status_code == 304:
                        self.log_result("Conditional Requests", True, "304 Not Modified working correctly")
                    else:
                        self.log_result("Conditional Requests", False, f"Expected 304, got {response2.status_code}")
                    
                    # Validate TTL is within 5-15 minutes
                    cache_control = headers.get("cache-control", "")
                    if "max-age=" in cache_control:
                        max_age = int(cache_control.split("max-age=")[1].split(",")[0])
                        if 300 <= max_age <= 900:  # 5-15 minutes
                            self.log_result("TTL Validation", True, f"Cache TTL within spec: {max_age}s")
                        else:
                            self.log_result("TTL Validation", False, f"Cache TTL outside 5-15min range: {max_age}s")
                    else:
                        self.log_result("TTL Validation", False, "No max-age found in cache-control")
                else:
                    missing = [h for h in cache_headers if h not in headers]
                    self.log_result("Cache Headers", False, f"Missing cache headers: {missing}")
            else:
                self.log_result("Caching Behavior", False, f"Initial request failed: {response1.status_code}")
                
        except Exception as e:
            self.log_result("Caching Behavior", False, f"Caching validation failed: {e}")
    
    async def validate_widget_templates(self):
        """Validate mobile widget templates."""
        self.print_header("📱 TRACK C COMPONENT 5: Mobile Widget Templates")
        
        try:
            from src.templates.widgets.ios_widget_config import generate_ios_widget_bundle
            from src.templates.widgets.android_widget_config import generate_android_widget_bundle
            
            # Test iOS widget configuration
            ios_config = generate_ios_widget_bundle()
            
            required_ios_sections = ["bundle_info", "widget_configurations", "api_configuration"]
            if all(section in ios_config for section in required_ios_sections):
                self.log_result("iOS Templates", True, "iOS widget configuration generation working")
                
                # Validate widget sizes
                widget_configs = ios_config["widget_configurations"]
                expected_sizes = ["small", "medium", "large"]
                
                if all(size in widget_configs for size in expected_sizes):
                    self.log_result("iOS Widget Sizes", True, "All iOS widget sizes configured")
                else:
                    missing = [s for s in expected_sizes if s not in widget_configs]
                    self.log_result("iOS Widget Sizes", False, f"Missing iOS sizes: {missing}")
            else:
                missing = [s for s in required_ios_sections if s not in ios_config]
                self.log_result("iOS Templates", False, f"Missing iOS config sections: {missing}")
            
            # Test Android widget configuration
            android_config = generate_android_widget_bundle()
            
            required_android_sections = ["bundle_info", "widget_configurations", "manifest_configuration"]
            if all(section in android_config for section in required_android_sections):
                self.log_result("Android Templates", True, "Android widget configuration generation working")
                
                # Validate widget sizes
                widget_configs = android_config["widget_configurations"]
                expected_sizes = ["small", "medium", "large"]
                
                if all(size in widget_configs for size in expected_sizes):
                    self.log_result("Android Widget Sizes", True, "All Android widget sizes configured")
                else:
                    missing = [s for s in expected_sizes if s not in widget_configs]
                    self.log_result("Android Widget Sizes", False, f"Missing Android sizes: {missing}")
            else:
                missing = [s for s in required_android_sections if s not in android_config]
                self.log_result("Android Templates", False, f"Missing Android config sections: {missing}")
                
        except Exception as e:
            self.log_result("Widget Templates", False, f"Template validation failed: {e}")
    
    async def validate_contract_compliance(self):
        """Validate widget API contract compliance."""
        self.print_header("📋 TRACK C COMPONENT 6: Contract Compliance")
        
        try:
            user_id = str(uuid4())
            response = requests.get(f"{self.base_url}/v1/gamification/summary?user_id={user_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check JSON shape contract
                required_fields = [
                    "user_id", "adherence_ring", "current_streak", 
                    "compact_message", "widget_deep_link", "cache_key"
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields:
                    self.log_result("JSON Shape", True, "JSON response shape meets contract")
                else:
                    self.log_result("JSON Shape", False, f"Missing required fields: {missing_fields}")
                
                # Check compact message length (≤50 chars)
                compact_message = data.get("compact_message", "")
                if len(compact_message) <= 50:
                    self.log_result("Compact Message", True, f"Compact message length valid: {len(compact_message)} chars")
                else:
                    self.log_result("Compact Message", False, f"Compact message too long: {len(compact_message)} chars")
                
                # Check deep link format
                deep_link = data.get("widget_deep_link", "")
                if deep_link.startswith("ainutritionist://"):
                    self.log_result("Deep Link Format", True, "Deep link format valid")
                else:
                    self.log_result("Deep Link Format", False, f"Invalid deep link format: {deep_link}")
                
                # Check response size (should be <10KB)
                response_size_kb = len(response.content) / 1024
                if response_size_kb < 10:
                    self.log_result("Response Size", True, f"Response size efficient: {response_size_kb:.2f}KB")
                else:
                    self.log_result("Response Size", False, f"Response too large: {response_size_kb:.2f}KB")
                    
        except Exception as e:
            self.log_result("Contract Compliance", False, f"Contract validation failed: {e}")
    
    async def validate_performance(self):
        """Validate performance characteristics."""
        self.print_header("⚡ TRACK C COMPONENT 7: Performance")
        
        try:
            user_id = str(uuid4())
            url = f"{self.base_url}/v1/gamification/summary?user_id={user_id}"
            
            # Test response time
            start_time = time.time()
            response = requests.get(url)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            if response_time_ms < 300:  # Target: <300ms
                self.log_result("Response Time", True, f"Response time good: {response_time_ms:.0f}ms")
            elif response_time_ms < 800:  # Acceptable: <800ms
                self.log_result("Response Time", True, f"Response time acceptable: {response_time_ms:.0f}ms")
            else:
                self.log_result("Response Time", False, f"Response time too slow: {response_time_ms:.0f}ms")
            
            # Test concurrent requests
            start_time = time.time()
            
            async def make_request():
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        return await resp.json()
            
            # Make 5 concurrent requests
            tasks = [make_request() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            successful_requests = sum(1 for r in results if not isinstance(r, Exception))
            
            if successful_requests == 5:
                self.log_result("Concurrent Requests", True, f"5 concurrent requests completed in {total_time:.2f}s")
            else:
                self.log_result("Concurrent Requests", False, f"Only {successful_requests}/5 requests succeeded")
                
        except Exception as e:
            self.log_result("Performance", False, f"Performance validation failed: {e}")
    
    async def run_validation(self):
        """Run complete Track C validation."""
        self.start_time = time.time()
        
        print(f"{Fore.MAGENTA}")
        print("🚀 AI Nutritionist - Track C Validation")
        print("=====================================")
        print("Widgets (iOS/Android) - Complete Implementation Test")
        print(f"{Style.RESET_ALL}")
        
        # Run all validation components
        await self.validate_domain_models()
        await self.validate_service_layer()
        await self.validate_api_endpoints()
        await self.validate_caching_behavior()
        await self.validate_widget_templates()
        await self.validate_contract_compliance()
        await self.validate_performance()
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate validation summary."""
        total_time = time.time() - self.start_time
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print("🎯 TRACK C VALIDATION SUMMARY")
        print(f"{'='*60}{Style.RESET_ALL}")
        
        print(f"\n📊 **Test Results:**")
        print(f"   • Total Tests: {total_tests}")
        print(f"   • {Fore.GREEN}Passed: {passed_tests}{Style.RESET_ALL}")
        print(f"   • {Fore.RED}Failed: {failed_tests}{Style.RESET_ALL}")
        print(f"   • Success Rate: {success_rate:.1f}%")
        print(f"   • Total Time: {total_time:.2f}s")
        
        if success_rate >= 85:
            status_color = Fore.GREEN
            status_message = "🎉 TRACK C IMPLEMENTATION: PRODUCTION READY!"
        elif success_rate >= 70:
            status_color = Fore.YELLOW
            status_message = "⚠️ TRACK C IMPLEMENTATION: NEEDS MINOR FIXES"
        else:
            status_color = Fore.RED
            status_message = "❌ TRACK C IMPLEMENTATION: NEEDS MAJOR FIXES"
        
        print(f"\n{status_color}{status_message}{Style.RESET_ALL}")
        
        if failed_tests > 0:
            print(f"\n{Fore.RED}❌ Failed Tests:{Style.RESET_ALL}")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['message']}")
        
        print(f"\n{Fore.CYAN}🔧 **Track C Components Status:**{Style.RESET_ALL}")
        components = [
            "Domain Models",
            "Service Layer", 
            "Widget API",
            "ETag Caching",
            "Mobile Templates",
            "Contract Compliance",
            "Performance"
        ]
        
        for i, component in enumerate(components, 1):
            # Check if component tests passed
            component_tests = [r for r in self.test_results if component.lower() in r["test"].lower()]
            component_success = all(r["success"] for r in component_tests) if component_tests else False
            
            status = f"{Fore.GREEN}✅" if component_success else f"{Fore.RED}❌"
            print(f"   C{i} {component}: {status}{Style.RESET_ALL}")
        
        # Save detailed results
        with open("track_c_validation_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "success_rate": success_rate,
                    "total_time": total_time,
                    "timestamp": datetime.now().isoformat()
                },
                "test_results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: track_c_validation_results.json")
        
        return success_rate >= 85


async def main():
    """Main validation entry point."""
    validator = TrackCValidator()
    
    try:
        await validator.run_validation()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ Validation interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Validation failed with error: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    asyncio.run(main())
