#!/usr/bin/env python3
"""
AI Nutritionist Cost Optimization Savings Calculator

This script estimates potential cost savings from implementing the cost optimization strategies.
"""

import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple

class CostOptimizationCalculator:
    """Calculate potential cost savings from optimization strategies"""
    
    def __init__(self):
        # Default AWS pricing (US East 1, as of 2024)
        self.pricing = {
            'lambda': {
                'request': 0.0000002,  # Per request
                'gb_second_x86': 0.0000166667,  # Per GB-second
                'gb_second_arm64': 0.0000133334,  # Per GB-second (20% cheaper)
            },
            'dynamodb': {
                'read_capacity': 0.00013,  # Per RCU hour
                'write_capacity': 0.00065,  # Per WCU hour
                'on_demand_read': 0.00025,  # Per read request unit
                'on_demand_write': 0.00125,  # Per write request unit
            },
            'api_gateway': {
                'request': 0.0000035,  # Per request
                'cache_0_5gb': 0.020,  # Per hour
                'cache_1_6gb': 0.038,  # Per hour
                'cache_6_1gb': 0.200,  # Per hour
            },
            's3': {
                'standard': 0.023,  # Per GB/month
                'ia': 0.0125,  # Per GB/month
                'glacier': 0.004,  # Per GB/month
                'deep_archive': 0.00099,  # Per GB/month
            },
            'cloudfront': {
                'request': 0.0000005,  # Per request
                'data_transfer': 0.085,  # Per GB
            }
        }
    
    def calculate_lambda_savings(self, current_usage: Dict) -> Dict:
        """Calculate Lambda cost savings from ARM64 migration"""
        monthly_invocations = current_usage.get('invocations', 1000000)
        avg_duration_ms = current_usage.get('duration_ms', 1000)
        memory_mb = current_usage.get('memory_mb', 256)
        
        # Current costs (x86)
        request_cost = monthly_invocations * self.pricing['lambda']['request']
        gb_seconds = (monthly_invocations * avg_duration_ms / 1000) * (memory_mb / 1024)
        compute_cost_x86 = gb_seconds * self.pricing['lambda']['gb_second_x86']
        current_total = request_cost + compute_cost_x86
        
        # Optimized costs (ARM64)
        compute_cost_arm64 = gb_seconds * self.pricing['lambda']['gb_second_arm64']
        optimized_total = request_cost + compute_cost_arm64
        
        savings = current_total - optimized_total
        savings_percentage = (savings / current_total) * 100 if current_total > 0 else 0
        
        return {
            'current_monthly_cost': current_total,
            'optimized_monthly_cost': optimized_total,
            'monthly_savings': savings,
            'annual_savings': savings * 12,
            'savings_percentage': savings_percentage,
            'optimization': 'ARM64 architecture migration'
        }
    
    def calculate_dynamodb_savings(self, current_usage: Dict) -> Dict:
        """Calculate DynamoDB cost savings from auto-scaling and on-demand"""
        provisioned_rcu = current_usage.get('provisioned_rcu', 25)
        provisioned_wcu = current_usage.get('provisioned_wcu', 25)
        actual_read_requests = current_usage.get('read_requests_month', 500000)
        actual_write_requests = current_usage.get('write_requests_month', 100000)
        hours_per_month = 730
        
        # Current provisioned costs
        current_read_cost = provisioned_rcu * self.pricing['dynamodb']['read_capacity'] * hours_per_month
        current_write_cost = provisioned_wcu * self.pricing['dynamodb']['write_capacity'] * hours_per_month
        current_total = current_read_cost + current_write_cost
        
        # On-demand costs
        on_demand_read_cost = actual_read_requests * self.pricing['dynamodb']['on_demand_read']
        on_demand_write_cost = actual_write_requests * self.pricing['dynamodb']['on_demand_write']
        on_demand_total = on_demand_read_cost + on_demand_write_cost
        
        # Auto-scaling costs (estimate 60% of provisioned)
        auto_scaling_total = current_total * 0.6
        
        # Choose best option
        best_option = min(
            ('on_demand', on_demand_total),
            ('auto_scaling', auto_scaling_total),
            key=lambda x: x[1]
        )
        
        savings = current_total - best_option[1]
        savings_percentage = (savings / current_total) * 100 if current_total > 0 else 0
        
        return {
            'current_monthly_cost': current_total,
            'optimized_monthly_cost': best_option[1],
            'monthly_savings': savings,
            'annual_savings': savings * 12,
            'savings_percentage': savings_percentage,
            'optimization': f'{best_option[0].replace("_", " ").title()} billing'
        }
    
    def calculate_api_gateway_savings(self, current_usage: Dict) -> Dict:
        """Calculate API Gateway cost savings from caching"""
        monthly_requests = current_usage.get('requests', 2000000)
        cache_hit_rate = current_usage.get('cache_hit_rate', 0.7)  # 70% cache hit rate
        cache_size = current_usage.get('cache_size', '1.6')  # GB
        hours_per_month = 730
        
        # Current costs (no caching)
        current_cost = monthly_requests * self.pricing['api_gateway']['request']
        
        # Optimized costs (with caching)
        cache_cost_per_hour = {
            '0.5': self.pricing['api_gateway']['cache_0_5gb'],
            '1.6': self.pricing['api_gateway']['cache_1_6gb'],
            '6.1': self.pricing['api_gateway']['cache_6_1gb']
        }.get(cache_size, self.pricing['api_gateway']['cache_1_6gb'])
        
        cache_monthly_cost = cache_cost_per_hour * hours_per_month
        reduced_requests = monthly_requests * (1 - cache_hit_rate)
        request_cost = reduced_requests * self.pricing['api_gateway']['request']
        optimized_total = cache_monthly_cost + request_cost
        
        savings = current_cost - optimized_total
        savings_percentage = (savings / current_cost) * 100 if current_cost > 0 else 0
        
        return {
            'current_monthly_cost': current_cost,
            'optimized_monthly_cost': optimized_total,
            'monthly_savings': savings,
            'annual_savings': savings * 12,
            'savings_percentage': savings_percentage,
            'optimization': f'Response caching ({cache_hit_rate*100:.0f}% hit rate)'
        }
    
    def calculate_s3_savings(self, current_usage: Dict) -> Dict:
        """Calculate S3 cost savings from lifecycle policies"""
        total_gb = current_usage.get('storage_gb', 1000)
        
        # Current costs (all Standard)
        current_cost = total_gb * self.pricing['s3']['standard']
        
        # Optimized costs (with lifecycle)
        # Assume: 40% Standard, 30% IA, 20% Glacier, 10% Deep Archive
        standard_gb = total_gb * 0.4
        ia_gb = total_gb * 0.3
        glacier_gb = total_gb * 0.2
        deep_archive_gb = total_gb * 0.1
        
        optimized_cost = (
            standard_gb * self.pricing['s3']['standard'] +
            ia_gb * self.pricing['s3']['ia'] +
            glacier_gb * self.pricing['s3']['glacier'] +
            deep_archive_gb * self.pricing['s3']['deep_archive']
        )
        
        savings = current_cost - optimized_cost
        savings_percentage = (savings / current_cost) * 100 if current_cost > 0 else 0
        
        return {
            'current_monthly_cost': current_cost,
            'optimized_monthly_cost': optimized_cost,
            'monthly_savings': savings,
            'annual_savings': savings * 12,
            'savings_percentage': savings_percentage,
            'optimization': 'Lifecycle policies (IA/Glacier/Deep Archive)'
        }
    
    def calculate_cloudfront_savings(self, current_usage: Dict) -> Dict:
        """Calculate CloudFront cost savings from price class optimization"""
        monthly_requests = current_usage.get('requests', 5000000)
        monthly_data_gb = current_usage.get('data_gb', 500)
        current_price_class = current_usage.get('price_class', 'PriceClass_All')
        
        # Current costs
        request_cost = monthly_requests * self.pricing['cloudfront']['request']
        data_cost = monthly_data_gb * self.pricing['cloudfront']['data_transfer']
        current_cost = request_cost + data_cost
        
        # Optimized costs (PriceClass_100 is ~15% cheaper for data transfer)
        if current_price_class != 'PriceClass_100':
            optimized_data_cost = data_cost * 0.85  # 15% reduction
            optimized_cost = request_cost + optimized_data_cost
            savings = current_cost - optimized_cost
        else:
            optimized_cost = current_cost
            savings = 0
        
        savings_percentage = (savings / current_cost) * 100 if current_cost > 0 else 0
        
        return {
            'current_monthly_cost': current_cost,
            'optimized_monthly_cost': optimized_cost,
            'monthly_savings': savings,
            'annual_savings': savings * 12,
            'savings_percentage': savings_percentage,
            'optimization': 'PriceClass_100 (North America + Europe)'
        }
    
    def generate_report(self, usage_profile: str = 'medium') -> Dict:
        """Generate comprehensive cost optimization report"""
        
        # Usage profiles
        usage_profiles = {
            'small': {
                'lambda': {
                    'invocations': 100000,
                    'duration_ms': 800,
                    'memory_mb': 256
                },
                'dynamodb': {
                    'provisioned_rcu': 5,
                    'provisioned_wcu': 5,
                    'read_requests_month': 50000,
                    'write_requests_month': 10000
                },
                'api_gateway': {
                    'requests': 200000,
                    'cache_hit_rate': 0.6,
                    'cache_size': '0.5'
                },
                's3': {
                    'storage_gb': 100
                },
                'cloudfront': {
                    'requests': 500000,
                    'data_gb': 50,
                    'price_class': 'PriceClass_All'
                }
            },
            'medium': {
                'lambda': {
                    'invocations': 1000000,
                    'duration_ms': 1000,
                    'memory_mb': 256
                },
                'dynamodb': {
                    'provisioned_rcu': 25,
                    'provisioned_wcu': 25,
                    'read_requests_month': 500000,
                    'write_requests_month': 100000
                },
                'api_gateway': {
                    'requests': 2000000,
                    'cache_hit_rate': 0.7,
                    'cache_size': '1.6'
                },
                's3': {
                    'storage_gb': 1000
                },
                'cloudfront': {
                    'requests': 5000000,
                    'data_gb': 500,
                    'price_class': 'PriceClass_All'
                }
            },
            'large': {
                'lambda': {
                    'invocations': 10000000,
                    'duration_ms': 1200,
                    'memory_mb': 512
                },
                'dynamodb': {
                    'provisioned_rcu': 100,
                    'provisioned_wcu': 100,
                    'read_requests_month': 5000000,
                    'write_requests_month': 1000000
                },
                'api_gateway': {
                    'requests': 20000000,
                    'cache_hit_rate': 0.8,
                    'cache_size': '6.1'
                },
                's3': {
                    'storage_gb': 10000
                },
                'cloudfront': {
                    'requests': 50000000,
                    'data_gb': 5000,
                    'price_class': 'PriceClass_All'
                }
            }
        }
        
        usage = usage_profiles.get(usage_profile, usage_profiles['medium'])
        
        # Calculate savings for each service
        lambda_savings = self.calculate_lambda_savings(usage['lambda'])
        dynamodb_savings = self.calculate_dynamodb_savings(usage['dynamodb'])
        api_gateway_savings = self.calculate_api_gateway_savings(usage['api_gateway'])
        s3_savings = self.calculate_s3_savings(usage['s3'])
        cloudfront_savings = self.calculate_cloudfront_savings(usage['cloudfront'])
        
        # Calculate totals
        total_current = sum([
            lambda_savings['current_monthly_cost'],
            dynamodb_savings['current_monthly_cost'],
            api_gateway_savings['current_monthly_cost'],
            s3_savings['current_monthly_cost'],
            cloudfront_savings['current_monthly_cost']
        ])
        
        total_optimized = sum([
            lambda_savings['optimized_monthly_cost'],
            dynamodb_savings['optimized_monthly_cost'],
            api_gateway_savings['optimized_monthly_cost'],
            s3_savings['optimized_monthly_cost'],
            cloudfront_savings['optimized_monthly_cost']
        ])
        
        total_savings = total_current - total_optimized
        total_savings_percentage = (total_savings / total_current) * 100 if total_current > 0 else 0
        
        return {
            'usage_profile': usage_profile,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'current_monthly_cost': total_current,
                'optimized_monthly_cost': total_optimized,
                'monthly_savings': total_savings,
                'annual_savings': total_savings * 12,
                'total_savings_percentage': total_savings_percentage
            },
            'service_savings': {
                'lambda': lambda_savings,
                'dynamodb': dynamodb_savings,
                'api_gateway': api_gateway_savings,
                's3': s3_savings,
                'cloudfront': cloudfront_savings
            },
            'implementation_priority': self.get_implementation_priority([
                ('Lambda (ARM64)', lambda_savings['savings_percentage'], lambda_savings['annual_savings']),
                ('DynamoDB (Auto-scaling)', dynamodb_savings['savings_percentage'], dynamodb_savings['annual_savings']),
                ('API Gateway (Caching)', api_gateway_savings['savings_percentage'], api_gateway_savings['annual_savings']),
                ('S3 (Lifecycle)', s3_savings['savings_percentage'], s3_savings['annual_savings']),
                ('CloudFront (Price Class)', cloudfront_savings['savings_percentage'], cloudfront_savings['annual_savings'])
            ])
        }
    
    def get_implementation_priority(self, optimizations: List[Tuple[str, float, float]]) -> List[Dict]:
        """Get implementation priority based on savings percentage and absolute savings"""
        # Sort by annual savings descending
        sorted_optimizations = sorted(optimizations, key=lambda x: x[2], reverse=True)
        
        priority_list = []
        for i, (name, percentage, annual_savings) in enumerate(sorted_optimizations):
            if percentage > 0:  # Only include optimizations with savings
                priority_list.append({
                    'rank': i + 1,
                    'optimization': name,
                    'savings_percentage': round(percentage, 1),
                    'annual_savings': round(annual_savings, 2),
                    'implementation_effort': self.get_implementation_effort(name),
                    'roi_score': round((percentage * annual_savings) / 100, 2)  # Simple ROI score
                })
        
        return priority_list
    
    def get_implementation_effort(self, optimization: str) -> str:
        """Get implementation effort level for each optimization"""
        effort_map = {
            'Lambda (ARM64)': 'Low',
            'DynamoDB (Auto-scaling)': 'Medium',
            'API Gateway (Caching)': 'Low',
            'S3 (Lifecycle)': 'Low',
            'CloudFront (Price Class)': 'Low'
        }
        return effort_map.get(optimization, 'Medium')

def print_report(report: Dict):
    """Print formatted cost optimization report"""
    print("=" * 80)
    print(f"  AI NUTRITIONIST COST OPTIMIZATION SAVINGS CALCULATOR")
    print("=" * 80)
    print(f"\nUsage Profile: {report['usage_profile'].upper()}")
    print(f"Generated: {report['generated_at']}")
    print("\n" + "=" * 80)
    print("  COST SUMMARY")
    print("=" * 80)
    
    summary = report['summary']
    print(f"Current Monthly Cost:    ${summary['current_monthly_cost']:.2f}")
    print(f"Optimized Monthly Cost:  ${summary['optimized_monthly_cost']:.2f}")
    print(f"Monthly Savings:         ${summary['monthly_savings']:.2f}")
    print(f"Annual Savings:          ${summary['annual_savings']:.2f}")
    print(f"Total Savings:           {summary['total_savings_percentage']:.1f}%")
    
    print("\n" + "=" * 80)
    print("  SERVICE-BY-SERVICE BREAKDOWN")
    print("=" * 80)
    
    for service, savings in report['service_savings'].items():
        print(f"\n{service.upper().replace('_', ' ')}:")
        print(f"  Current:       ${savings['current_monthly_cost']:.2f}/month")
        print(f"  Optimized:     ${savings['optimized_monthly_cost']:.2f}/month")
        print(f"  Savings:       ${savings['monthly_savings']:.2f}/month ({savings['savings_percentage']:.1f}%)")
        print(f"  Annual:        ${savings['annual_savings']:.2f}/year")
        print(f"  Optimization:  {savings['optimization']}")
    
    print("\n" + "=" * 80)
    print("  IMPLEMENTATION PRIORITY")
    print("=" * 80)
    print(f"{'Rank':<4} {'Optimization':<25} {'Savings %':<10} {'Annual $':<12} {'Effort':<8} {'ROI Score':<10}")
    print("-" * 80)
    
    for item in report['implementation_priority']:
        print(f"{item['rank']:<4} {item['optimization']:<25} {item['savings_percentage']:<10}% "
              f"${item['annual_savings']:<11.2f} {item['implementation_effort']:<8} {item['roi_score']:<10}")
    
    print("\n" + "=" * 80)
    print("  IMPLEMENTATION RECOMMENDATIONS")
    print("=" * 80)
    print("\n1. START WITH HIGH-ROI, LOW-EFFORT OPTIMIZATIONS:")
    high_roi_low_effort = [item for item in report['implementation_priority'] 
                          if item['implementation_effort'] == 'Low' and item['roi_score'] > 50]
    for item in high_roi_low_effort[:3]:
        print(f"   • {item['optimization']} - {item['savings_percentage']:.1f}% savings (${item['annual_savings']:.0f}/year)")
    
    print("\n2. QUICK WINS (Implement in first week):")
    print("   • Enable ARM64 architecture for Lambda functions")
    print("   • Configure S3 lifecycle policies")
    print("   • Set up API Gateway response caching")
    
    print("\n3. MEDIUM-TERM OPTIMIZATIONS (Implement in first month):")
    print("   • Configure DynamoDB auto-scaling")
    print("   • Optimize CloudFront pricing class")
    print("   • Set up comprehensive cost monitoring")
    
    print(f"\n💰 TOTAL ANNUAL SAVINGS POTENTIAL: ${summary['annual_savings']:.2f}")
    print(f"📊 OVERALL COST REDUCTION: {summary['total_savings_percentage']:.1f}%")
    print("\n" + "=" * 80)

def main():
    parser = argparse.ArgumentParser(description='Calculate AI Nutritionist cost optimization savings')
    parser.add_argument('--profile', choices=['small', 'medium', 'large'], default='medium',
                       help='Usage profile for calculation (default: medium)')
    parser.add_argument('--output', choices=['console', 'json'], default='console',
                       help='Output format (default: console)')
    
    args = parser.parse_args()
    
    calculator = CostOptimizationCalculator()
    report = calculator.generate_report(args.profile)
    
    if args.output == 'json':
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

if __name__ == '__main__':
    main()
