#!/usr/bin/env python3
"""
Request Replay Tool

Replays HTTP requests for debugging:
- Captures and stores requests
- Replays requests with modifications
- Compares responses
- Analyzes differences
- Performance testing
"""

import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse
from dataclasses import dataclass, asdict
import time


@dataclass
class RequestCapture:
    """Captured request data"""
    request_id: str
    timestamp: str
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[str]
    response_status: int
    response_headers: Dict[str, str]
    response_body: str
    response_time: float
    metadata: Dict[str, Any]


class RequestReplayer:
    """Handles request capture and replay"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.captures_dir = project_root / "dev-tools" / "debugging" / "captures"
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        
    async def capture_request(self, 
                            method: str,
                            url: str,
                            headers: Optional[Dict[str, str]] = None,
                            body: Optional[str] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> RequestCapture:
        """Capture a request and its response"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers or {},
                    data=body
                ) as response:
                    response_body = await response.text()
                    response_time = time.time() - start_time
                    
                    capture = RequestCapture(
                        request_id=f"req_{int(time.time() * 1000)}",
                        timestamp=datetime.utcnow().isoformat(),
                        method=method,
                        url=url,
                        headers=headers or {},
                        body=body,
                        response_status=response.status,
                        response_headers=dict(response.headers),
                        response_body=response_body,
                        response_time=response_time,
                        metadata=metadata or {}
                    )
                    
                    # Save capture
                    await self._save_capture(capture)
                    return capture
                    
        except Exception as e:
            # Create error capture
            response_time = time.time() - start_time
            capture = RequestCapture(
                request_id=f"req_err_{int(time.time() * 1000)}",
                timestamp=datetime.utcnow().isoformat(),
                method=method,
                url=url,
                headers=headers or {},
                body=body,
                response_status=500,
                response_headers={},
                response_body=f"Error: {str(e)}",
                response_time=response_time,
                metadata={"error": str(e), **(metadata or {})}
            )
            
            await self._save_capture(capture)
            return capture
    
    async def replay_request(self, 
                           capture: RequestCapture,
                           modifications: Optional[Dict[str, Any]] = None) -> RequestCapture:
        """Replay a captured request with optional modifications"""
        
        # Apply modifications
        method = modifications.get("method", capture.method) if modifications else capture.method
        url = modifications.get("url", capture.url) if modifications else capture.url
        headers = modifications.get("headers", capture.headers) if modifications else capture.headers
        body = modifications.get("body", capture.body) if modifications else capture.body
        
        # Replay the request
        replay_capture = await self.capture_request(
            method=method,
            url=url,
            headers=headers,
            body=body,
            metadata={
                "replay_of": capture.request_id,
                "modifications": modifications or {},
                "original_timestamp": capture.timestamp
            }
        )
        
        return replay_capture
    
    async def _save_capture(self, capture: RequestCapture):
        """Save capture to file"""
        filename = f"{capture.request_id}.json"
        filepath = self.captures_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(capture), f, indent=2)
    
    def load_capture(self, request_id: str) -> Optional[RequestCapture]:
        """Load a captured request"""
        filename = f"{request_id}.json"
        filepath = self.captures_dir / filename
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            return RequestCapture(**data)
    
    def list_captures(self, 
                     filter_by: Optional[str] = None,
                     limit: int = 50) -> List[RequestCapture]:
        """List captured requests"""
        captures = []
        
        for capture_file in sorted(self.captures_dir.glob("*.json"), reverse=True):
            if len(captures) >= limit:
                break
                
            try:
                with open(capture_file, 'r') as f:
                    data = json.load(f)
                    capture = RequestCapture(**data)
                    
                    # Apply filter
                    if filter_by:
                        if (filter_by.lower() not in capture.url.lower() and
                            filter_by.lower() not in capture.method.lower()):
                            continue
                    
                    captures.append(capture)
                    
            except Exception as e:
                print(f"Warning: Could not load capture {capture_file}: {e}")
        
        return captures
    
    def compare_captures(self, 
                        capture1: RequestCapture, 
                        capture2: RequestCapture) -> Dict[str, Any]:
        """Compare two request captures"""
        comparison = {
            "request_differences": {},
            "response_differences": {},
            "performance_differences": {},
            "summary": {}
        }
        
        # Compare requests
        if capture1.method != capture2.method:
            comparison["request_differences"]["method"] = {
                "capture1": capture1.method,
                "capture2": capture2.method
            }
        
        if capture1.url != capture2.url:
            comparison["request_differences"]["url"] = {
                "capture1": capture1.url,
                "capture2": capture2.url
            }
        
        if capture1.headers != capture2.headers:
            comparison["request_differences"]["headers"] = {
                "capture1": capture1.headers,
                "capture2": capture2.headers
            }
        
        if capture1.body != capture2.body:
            comparison["request_differences"]["body"] = {
                "capture1": capture1.body,
                "capture2": capture2.body
            }
        
        # Compare responses
        if capture1.response_status != capture2.response_status:
            comparison["response_differences"]["status"] = {
                "capture1": capture1.response_status,
                "capture2": capture2.response_status
            }
        
        if capture1.response_body != capture2.response_body:
            comparison["response_differences"]["body"] = {
                "capture1": capture1.response_body,
                "capture2": capture2.response_body,
                "body_length_diff": len(capture2.response_body) - len(capture1.response_body)
            }
        
        # Compare performance
        time_diff = capture2.response_time - capture1.response_time
        comparison["performance_differences"] = {
            "response_time_diff": time_diff,
            "capture1_time": capture1.response_time,
            "capture2_time": capture2.response_time,
            "performance_change": "faster" if time_diff < 0 else "slower" if time_diff > 0 else "same"
        }
        
        # Summary
        comparison["summary"] = {
            "has_request_differences": bool(comparison["request_differences"]),
            "has_response_differences": bool(comparison["response_differences"]),
            "significant_performance_change": abs(time_diff) > 0.1,  # 100ms threshold
            "status_code_changed": capture1.response_status != capture2.response_status
        }
        
        return comparison
    
    async def batch_replay(self, 
                          captures: List[RequestCapture],
                          modifications: Optional[Dict[str, Any]] = None,
                          parallel: bool = True) -> List[RequestCapture]:
        """Replay multiple requests"""
        if parallel:
            tasks = [
                self.replay_request(capture, modifications)
                for capture in captures
            ]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for capture in captures:
                result = await self.replay_request(capture, modifications)
                results.append(result)
            return results
    
    async def performance_test(self,
                             capture: RequestCapture,
                             iterations: int = 10,
                             concurrent: int = 1) -> Dict[str, Any]:
        """Run performance test on a captured request"""
        results = {
            "iterations": iterations,
            "concurrent_requests": concurrent,
            "response_times": [],
            "status_codes": [],
            "errors": [],
            "statistics": {}
        }
        
        # Run iterations
        for i in range(0, iterations, concurrent):
            batch_size = min(concurrent, iterations - i)
            
            # Create tasks for concurrent requests
            tasks = [
                self.replay_request(capture)
                for _ in range(batch_size)
            ]
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    results["errors"].append(str(result))
                else:
                    results["response_times"].append(result.response_time)
                    results["status_codes"].append(result.response_status)
        
        # Calculate statistics
        if results["response_times"]:
            times = results["response_times"]
            results["statistics"] = {
                "min_time": min(times),
                "max_time": max(times),
                "avg_time": sum(times) / len(times),
                "median_time": sorted(times)[len(times) // 2],
                "total_requests": len(times),
                "error_count": len(results["errors"]),
                "success_rate": (len(times) / iterations) * 100
            }
        
        return results
    
    def generate_report(self, captures: List[RequestCapture]) -> str:
        """Generate a report from captures"""
        if not captures:
            return "No captures to report on."
        
        report_lines = [
            "# Request Replay Report",
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Total Captures: {len(captures)}",
            "",
            "## Summary",
        ]
        
        # Status code distribution
        status_codes = {}
        total_time = 0
        methods = {}
        
        for capture in captures:
            status_codes[capture.response_status] = status_codes.get(capture.response_status, 0) + 1
            total_time += capture.response_time
            methods[capture.method] = methods.get(capture.method, 0) + 1
        
        report_lines.extend([
            f"- Average Response Time: {total_time / len(captures):.3f}s",
            f"- HTTP Methods: {', '.join([f'{method}({count})' for method, count in methods.items()])}",
            f"- Status Codes: {', '.join([f'{code}({count})' for code, count in status_codes.items()])}",
            "",
            "## Captures"
        ])
        
        # Individual captures
        for capture in captures[:20]:  # Limit to first 20
            report_lines.extend([
                f"### {capture.request_id}",
                f"- **Time**: {capture.timestamp}",
                f"- **Request**: {capture.method} {capture.url}",
                f"- **Response**: {capture.response_status} ({capture.response_time:.3f}s)",
                ""
            ])
        
        if len(captures) > 20:
            report_lines.append(f"... and {len(captures) - 20} more captures")
        
        return "\n".join(report_lines)


async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Request Replay Tool")
    parser.add_argument("command", choices=["capture", "replay", "list", "compare", "performance", "report"])
    
    # Capture arguments
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--url", help="Request URL")
    parser.add_argument("--headers", help="Headers as JSON string")
    parser.add_argument("--body", help="Request body")
    
    # Replay arguments
    parser.add_argument("--request-id", help="Request ID to replay")
    parser.add_argument("--modifications", help="Modifications as JSON string")
    
    # List arguments
    parser.add_argument("--filter", help="Filter captures by URL or method")
    parser.add_argument("--limit", type=int, default=50, help="Limit number of results")
    
    # Compare arguments
    parser.add_argument("--request-id-2", help="Second request ID for comparison")
    
    # Performance arguments
    parser.add_argument("--iterations", type=int, default=10, help="Number of iterations")
    parser.add_argument("--concurrent", type=int, default=1, help="Concurrent requests")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    replayer = RequestReplayer(project_root)
    
    if args.command == "capture":
        if not args.url:
            print("Error: --url is required for capture command")
            sys.exit(1)
        
        headers = json.loads(args.headers) if args.headers else None
        
        print(f"Capturing request: {args.method} {args.url}")
        capture = await replayer.capture_request(
            method=args.method,
            url=args.url,
            headers=headers,
            body=args.body
        )
        
        print(f"Captured request: {capture.request_id}")
        print(f"Status: {capture.response_status}")
        print(f"Response time: {capture.response_time:.3f}s")
    
    elif args.command == "replay":
        if not args.request_id:
            print("Error: --request-id is required for replay command")
            sys.exit(1)
        
        original_capture = replayer.load_capture(args.request_id)
        if not original_capture:
            print(f"Error: Capture {args.request_id} not found")
            sys.exit(1)
        
        modifications = json.loads(args.modifications) if args.modifications else None
        
        print(f"Replaying request: {args.request_id}")
        replay_capture = await replayer.replay_request(original_capture, modifications)
        
        print(f"Replay completed: {replay_capture.request_id}")
        print(f"Status: {replay_capture.response_status}")
        print(f"Response time: {replay_capture.response_time:.3f}s")
    
    elif args.command == "list":
        captures = replayer.list_captures(filter_by=args.filter, limit=args.limit)
        
        print(f"Found {len(captures)} captures:")
        for capture in captures:
            print(f"  {capture.request_id}: {capture.method} {capture.url} -> {capture.response_status} ({capture.response_time:.3f}s)")
    
    elif args.command == "compare":
        if not args.request_id or not args.request_id_2:
            print("Error: --request-id and --request-id-2 are required for compare command")
            sys.exit(1)
        
        capture1 = replayer.load_capture(args.request_id)
        capture2 = replayer.load_capture(args.request_id_2)
        
        if not capture1 or not capture2:
            print("Error: One or both captures not found")
            sys.exit(1)
        
        comparison = replayer.compare_captures(capture1, capture2)
        print(json.dumps(comparison, indent=2))
    
    elif args.command == "performance":
        if not args.request_id:
            print("Error: --request-id is required for performance command")
            sys.exit(1)
        
        capture = replayer.load_capture(args.request_id)
        if not capture:
            print(f"Error: Capture {args.request_id} not found")
            sys.exit(1)
        
        print(f"Running performance test on {args.request_id}")
        print(f"Iterations: {args.iterations}, Concurrent: {args.concurrent}")
        
        results = await replayer.performance_test(capture, args.iterations, args.concurrent)
        
        print("\nPerformance Test Results:")
        print(json.dumps(results["statistics"], indent=2))
    
    elif args.command == "report":
        captures = replayer.list_captures(limit=1000)
        report = replayer.generate_report(captures)
        print(report)


if __name__ == "__main__":
    asyncio.run(main())
