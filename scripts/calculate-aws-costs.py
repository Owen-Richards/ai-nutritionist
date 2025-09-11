#!/usr/bin/env python3
"""
AI Nutritionist AWS Cost Calculator
Estimates monthly AWS costs based on usage patterns
"""

import json
from datetime import datetime

class AWSCostCalculator:
    def __init__(self):
        self.pricing = {
            'lambda': {
                'requests': 0.0000002,  # per request after free tier
                'gb_second': 0.0000166667,  # per GB-second
                'free_requests': 1000000,  # monthly
                'free_gb_seconds': 400000  # monthly
            },
            'dynamodb': {
                'read_units': 0.00013,  # per RCU per hour
                'write_units': 0.00065,  # per WCU per hour
                'storage': 0.25,  # per GB per month
                'free_storage': 25,  # GB monthly
                'free_read_units': 25,  # monthly average
                'free_write_units': 25  # monthly average
            },
            'api_gateway': {
                'requests': 0.0000035,  # per request after free tier
                'free_requests': 1000000  # monthly
            },
            'bedrock': {
                'input_tokens': 0.00025,  # per 1K tokens (Claude Haiku)
                'output_tokens': 0.00125  # per 1K tokens (Claude Haiku)
            },
            's3': {
                'storage': 0.023,  # per GB per month
                'requests': 0.0004,  # per 1K PUT requests
                'free_storage': 5,  # GB monthly
                'free_requests': 20000  # monthly
            },
            'cloudwatch': {
                'metrics': 0.30,  # per metric per month
                'logs': 0.50,  # per GB ingested
                'free_metrics': 10  # monthly
            }
        }

    def calculate_lambda_cost(self, monthly_requests, avg_duration_ms, memory_mb):
        """Calculate Lambda costs"""
        free_requests = self.pricing['lambda']['free_requests']
        billable_requests = max(0, monthly_requests - free_requests)
        
        request_cost = billable_requests * self.pricing['lambda']['requests']
        
        # GB-seconds calculation
        gb_seconds = (monthly_requests * avg_duration_ms / 1000 * memory_mb / 1024)
        free_gb_seconds = self.pricing['lambda']['free_gb_seconds']
        billable_gb_seconds = max(0, gb_seconds - free_gb_seconds)
        
        compute_cost = billable_gb_seconds * self.pricing['lambda']['gb_second']
        
        return request_cost + compute_cost

    def calculate_dynamodb_cost(self, read_units, write_units, storage_gb):
        """Calculate DynamoDB costs"""
        free_read = self.pricing['dynamodb']['free_read_units']
        free_write = self.pricing['dynamodb']['free_write_units']
        free_storage = self.pricing['dynamodb']['free_storage']
        
        # Hours in a month (assuming 730)
        hours_per_month = 730
        
        read_cost = max(0, read_units - free_read) * hours_per_month * self.pricing['dynamodb']['read_units']
        write_cost = max(0, write_units - free_write) * hours_per_month * self.pricing['dynamodb']['write_units']
        storage_cost = max(0, storage_gb - free_storage) * self.pricing['dynamodb']['storage']
        
        return read_cost + write_cost + storage_cost

    def calculate_api_gateway_cost(self, monthly_requests):
        """Calculate API Gateway costs"""
        free_requests = self.pricing['api_gateway']['free_requests']
        billable_requests = max(0, monthly_requests - free_requests)
        return billable_requests * self.pricing['api_gateway']['requests']

    def calculate_bedrock_cost(self, monthly_meal_plans, avg_input_tokens, avg_output_tokens):
        """Calculate Bedrock AI costs"""
        total_input_tokens = monthly_meal_plans * avg_input_tokens
        total_output_tokens = monthly_meal_plans * avg_output_tokens
        
        input_cost = (total_input_tokens / 1000) * self.pricing['bedrock']['input_tokens']
        output_cost = (total_output_tokens / 1000) * self.pricing['bedrock']['output_tokens']
        
        return input_cost + output_cost

    def estimate_business_costs(self, scenario="startup"):
        """Estimate costs for different business scenarios"""
        scenarios = {
            "startup": {
                "monthly_users": 100,
                "api_requests_per_user": 50,
                "meal_plans_per_user": 3,
                "messages_per_user": 20,
                "description": "Early stage with 100 active users"
            },
            "growing": {
                "monthly_users": 500,
                "api_requests_per_user": 80,
                "meal_plans_per_user": 5,
                "messages_per_user": 40,
                "description": "Growing business with 500 active users"
            },
            "established": {
                "monthly_users": 2000,
                "api_requests_per_user": 120,
                "meal_plans_per_user": 8,
                "messages_per_user": 60,
                "description": "Established business with 2000 active users"
            }
        }
        
        if scenario not in scenarios:
            scenario = "startup"
        
        params = scenarios[scenario]
        
        # Calculate usage metrics
        total_api_requests = params["monthly_users"] * params["api_requests_per_user"]
        total_meal_plans = params["monthly_users"] * params["meal_plans_per_user"]
        total_messages = params["monthly_users"] * params["messages_per_user"]
        
        # Lambda usage (message handling + meal plan generation)
        lambda_requests = total_api_requests + total_meal_plans
        avg_duration = 3000  # 3 seconds average
        memory_size = 512  # MB
        
        # DynamoDB usage
        read_units = params["monthly_users"] * 2  # profile + meal plan reads
        write_units = total_meal_plans * 0.5  # meal plan writes
        storage_gb = params["monthly_users"] * 0.1  # 100KB per user average
        
        # Bedrock usage (for meal plan generation)
        avg_input_tokens = 1500  # prompt tokens
        avg_output_tokens = 2000  # response tokens
        
        # Calculate costs
        costs = {
            "lambda": self.calculate_lambda_cost(lambda_requests, avg_duration, memory_size),
            "dynamodb": self.calculate_dynamodb_cost(read_units, write_units, storage_gb),
            "api_gateway": self.calculate_api_gateway_cost(total_api_requests),
            "bedrock": self.calculate_bedrock_cost(total_meal_plans, avg_input_tokens, avg_output_tokens),
            "s3": 5.0,  # Estimated for web assets and backups
            "cloudwatch": 10.0,  # Estimated for monitoring
            "other": 15.0  # SNS, SES, etc.
        }
        
        total_cost = sum(costs.values())
        
        return {
            "scenario": scenario,
            "description": params["description"],
            "users": params["monthly_users"],
            "costs": costs,
            "total_monthly_cost": total_cost,
            "cost_per_user": total_cost / params["monthly_users"],
            "usage_metrics": {
                "api_requests": total_api_requests,
                "meal_plans": total_meal_plans,
                "messages": total_messages
            }
        }

def main():
    calculator = AWSCostCalculator()
    
    print("🧮 AI Nutritionist AWS Cost Calculator")
    print("=" * 50)
    print()
    
    scenarios = ["startup", "growing", "established"]
    
    for scenario in scenarios:
        result = calculator.estimate_business_costs(scenario)
        
        print(f"📊 {scenario.upper()} SCENARIO")
        print(f"Description: {result['description']}")
        print(f"Monthly Users: {result['users']:,}")
        print()
        
        print("💰 Monthly AWS Costs:")
        for service, cost in result['costs'].items():
            print(f"  • {service.replace('_', ' ').title()}: ${cost:.2f}")
        
        print(f"\n💳 TOTAL MONTHLY COST: ${result['total_monthly_cost']:.2f}")
        print(f"📈 Cost per User: ${result['cost_per_user']:.2f}")
        print()
        
        print("📊 Usage Metrics:")
        for metric, value in result['usage_metrics'].items():
            print(f"  • {metric.replace('_', ' ').title()}: {value:,}")
        
        print("\n" + "─" * 50 + "\n")
    
    # Revenue projection
    print("💰 REVENUE PROJECTIONS")
    print("=" * 50)
    
    revenue_scenarios = {
        "startup": {"premium_users": 20, "monthly_price": 19.99},
        "growing": {"premium_users": 125, "monthly_price": 19.99},
        "established": {"premium_users": 600, "monthly_price": 19.99}
    }
    
    for scenario in scenarios:
        cost_result = calculator.estimate_business_costs(scenario)
        revenue_data = revenue_scenarios[scenario]
        
        monthly_revenue = revenue_data["premium_users"] * revenue_data["monthly_price"]
        monthly_cost = cost_result["total_monthly_cost"]
        monthly_profit = monthly_revenue - monthly_cost
        profit_margin = (monthly_profit / monthly_revenue * 100) if monthly_revenue > 0 else 0
        
        print(f"🎯 {scenario.upper()} SCENARIO:")
        print(f"  Premium Users: {revenue_data['premium_users']}")
        print(f"  Monthly Revenue: ${monthly_revenue:.2f}")
        print(f"  Monthly AWS Costs: ${monthly_cost:.2f}")
        print(f"  Monthly Profit: ${monthly_profit:.2f}")
        print(f"  Profit Margin: {profit_margin:.1f}%")
        print()
    
    print("📝 NOTES:")
    print("• Costs include AWS Free Tier benefits for first 12 months")
    print("• Actual costs may vary based on usage patterns")
    print("• Consider additional costs: domain, email, marketing")
    print("• Revenue assumes 20-30% free-to-premium conversion rate")

if __name__ == "__main__":
    main()
