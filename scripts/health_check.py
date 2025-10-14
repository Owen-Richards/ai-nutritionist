#!/usr/bin/env python3
"""
Health check script for deployment verification.
Validates that the deployed application is healthy and responsive.
"""

import requests
import time
import sys
import argparse
from typing import List, Dict, Any


def check_endpoint_health(
    url: str,
    timeout: int = 30,
    expected_status: int = 200
) -> Dict[str, Any]:
    """Check health of a single endpoint."""
    try:
        start_time = time.time()
        response = requests.get(
            f"{url}/health",
            timeout=timeout,
            headers={"User-Agent": "CI-Health-Check/1.0"}
        )
        end_time = time.time()
        
        return {
            'url': url,
            'status_code': response.status_code,
            'response_time': end_time - start_time,
            'healthy': response.status_code == expected_status,
            'content': response.text[:200] if response.text else None
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'status_code': None,
            'response_time': None,
            'healthy': False,
            'error': str(e)
        }


def check_api_endpoints(base_url: str) -> List[Dict[str, Any]]:
    """Check health of critical API endpoints."""
    endpoints = [
        "/health",
        "/api/v1/health",
        "/api/v1/nutrition/analyze",
        "/api/v1/plans/generate"
    ]
    
    results = []
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            start_time = time.time()
            response = requests.get(
                url,
                timeout=10,
                headers={"User-Agent": "CI-Health-Check/1.0"}
            )
            end_time = time.time()
            
            results.append({
                'endpoint': endpoint,
                'url': url,
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'healthy': response.status_code in [200, 201, 204, 400, 401],  # 4xx may be expected for some endpoints
                'content_length': len(response.content) if response.content else 0
            })
        except requests.exceptions.RequestException as e:
            results.append({
                'endpoint': endpoint,
                'url': url,
                'status_code': None,
                'response_time': None,
                'healthy': False,
                'error': str(e)
            })
    
    return results


def monitor_health(url: str, duration: int = 60, interval: int = 5) -> bool:
    """Monitor health over a period of time."""
    print(f"🔍 Monitoring health for {duration} seconds (checking every {interval}s)")
    
    start_time = time.time()
    failed_checks = 0
    total_checks = 0
    
    while time.time() - start_time < duration:
        health_result = check_endpoint_health(url)
        total_checks += 1
        
        if health_result['healthy']:
            print(f"✅ Health check passed ({health_result['response_time']:.2f}s)")
        else:
            failed_checks += 1
            print(f"❌ Health check failed: {health_result.get('error', 'Unknown error')}")
        
        time.sleep(interval)
    
    success_rate = ((total_checks - failed_checks) / total_checks) * 100
    print(f"📊 Health monitoring complete: {success_rate:.1f}% success rate ({total_checks} checks)")
    
    return success_rate >= 95  # Require 95% success rate


def main():
    parser = argparse.ArgumentParser(description='Health check for deployed application')
    parser.add_argument('--url', required=True, help='Base URL of the application')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--monitor-duration', type=int, default=0, 
                       help='Duration to monitor health in seconds (0 = single check)')
    parser.add_argument('--monitor-interval', type=int, default=5, 
                       help='Interval between health checks in seconds')
    
    args = parser.parse_args()
    
    print(f"🏥 Starting health check for {args.url}")
    
    if args.monitor_duration > 0:
        # Continuous monitoring
        success = monitor_health(args.url, args.monitor_duration, args.monitor_interval)
        if not success:
            print("❌ Health monitoring failed")
            sys.exit(1)
    else:
        # Single health check
        health_result = check_endpoint_health(args.url, args.timeout)
        
        if health_result['healthy']:
            print(f"✅ Application is healthy")
            print(f"   Response time: {health_result['response_time']:.2f}s")
        else:
            print(f"❌ Application health check failed")
            if 'error' in health_result:
                print(f"   Error: {health_result['error']}")
            sys.exit(1)
    
    # Check API endpoints
    print("\n🔍 Checking API endpoints...")
    endpoint_results = check_api_endpoints(args.url)
    
    failed_endpoints = []
    for result in endpoint_results:
        if result['healthy']:
            print(f"✅ {result['endpoint']}: {result['status_code']} ({result['response_time']:.2f}s)")
        else:
            print(f"❌ {result['endpoint']}: Failed")
            failed_endpoints.append(result['endpoint'])
    
    if failed_endpoints:
        print(f"\n❌ {len(failed_endpoints)} endpoint(s) failed health check")
        sys.exit(1)
    else:
        print(f"\n✅ All endpoints passed health check")


if __name__ == '__main__':
    main()
