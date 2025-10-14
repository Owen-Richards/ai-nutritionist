#!/usr/bin/env python3
"""
Performance regression detection script for CI/CD pipeline.
Compares current benchmark results with baseline to detect regressions.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List


def load_benchmark_results(file_path: str) -> Dict[str, Any]:
    """Load benchmark results from JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Benchmark file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in benchmark file: {e}")
        return {}


def analyze_performance_regression(
    current_results: Dict[str, Any],
    baseline_results: Dict[str, Any],
    threshold_percent: float = 10.0
) -> List[Dict[str, Any]]:
    """Analyze performance regression between current and baseline results."""
    regressions = []
    
    if not baseline_results:
        print("ℹ️ No baseline results found, skipping regression analysis")
        return regressions
    
    current_benchmarks = current_results.get('benchmarks', [])
    baseline_benchmarks = {b['name']: b for b in baseline_results.get('benchmarks', [])}
    
    for benchmark in current_benchmarks:
        name = benchmark.get('name', '')
        current_mean = benchmark.get('stats', {}).get('mean', 0)
        
        if name in baseline_benchmarks:
            baseline_mean = baseline_benchmarks[name].get('stats', {}).get('mean', 0)
            
            if baseline_mean > 0:
                regression_percent = ((current_mean - baseline_mean) / baseline_mean) * 100
                
                if regression_percent > threshold_percent:
                    regressions.append({
                        'name': name,
                        'current_mean': current_mean,
                        'baseline_mean': baseline_mean,
                        'regression_percent': regression_percent,
                        'threshold': threshold_percent
                    })
    
    return regressions


def main():
    parser = argparse.ArgumentParser(description='Check for performance regressions')
    parser.add_argument('current_results', help='Current benchmark results JSON file')
    parser.add_argument('--baseline', help='Baseline benchmark results JSON file')
    parser.add_argument('--threshold', type=float, default=10.0, 
                       help='Regression threshold percentage (default: 10.0)')
    parser.add_argument('--output', help='Output file for regression report')
    
    args = parser.parse_args()
    
    # Load current results
    current_results = load_benchmark_results(args.current_results)
    if not current_results:
        sys.exit(1)
    
    # Load baseline results if provided
    baseline_results = {}
    if args.baseline and Path(args.baseline).exists():
        baseline_results = load_benchmark_results(args.baseline)
    
    # Analyze regressions
    regressions = analyze_performance_regression(
        current_results, baseline_results, args.threshold
    )
    
    # Generate report
    if regressions:
        print(f"❌ Performance regressions detected ({len(regressions)} issues):")
        for regression in regressions:
            print(f"  • {regression['name']}: "
                  f"{regression['regression_percent']:.1f}% slower "
                  f"({regression['current_mean']:.4f}s vs {regression['baseline_mean']:.4f}s)")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    'status': 'regression_detected',
                    'regressions': regressions,
                    'total_regressions': len(regressions)
                }, f, indent=2)
        
        sys.exit(1)
    else:
        print("✅ No performance regressions detected")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    'status': 'no_regressions',
                    'total_benchmarks': len(current_results.get('benchmarks', [])),
                    'threshold_percent': args.threshold
                }, f, indent=2)


if __name__ == '__main__':
    main()
