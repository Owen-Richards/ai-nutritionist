#!/usr/bin/env python3
"""
Cost Estimation Script - Run BEFORE deploying to AWS
Estimates monthly costs for the AI Nutritionist application
"""

def estimate_costs():
    print("💰 AI NUTRITIONIST - COST ESTIMATION")
    print("=" * 50)
    
    # Base AWS costs (monthly estimates)
    costs = {
        "🔹 Lambda (Free Tier)": 0.00,  # 1M requests/month free
        "🔹 API Gateway": 0.00,          # 1M requests/month free  
        "🔹 DynamoDB (Pay-per-request)": 2.00,  # ~$2 for testing
        "🔹 CloudWatch Logs": 1.00,     # Basic logging
        "🔹 S3 Storage": 0.50,          # Minimal storage
        "🔹 Bedrock (Claude Haiku)": 0.00,  # With MOCK_AI_RESPONSES=true
    }
    
    total_base = sum(costs.values())
    
    print("\n📊 ESTIMATED MONTHLY COSTS (Testing Mode):")
    for service, cost in costs.items():
        print(f"{service}: ${cost:.2f}")
    
    print(f"\n💰 TOTAL BASE COST: ${total_base:.2f}/month")
    
    print("\n⚠️ VARIABLE COSTS (When MOCK_AI_RESPONSES=false):")
    print("🔹 Bedrock Claude Haiku: $0.25 per 1K input tokens")
    print("🔹 Bedrock Claude Haiku: $1.25 per 1K output tokens")
    print("🔹 Example: 100 AI requests/day = ~$5-10/month")
    
    print("\n📋 COST PROTECTION MEASURES:")
    print("✅ Billing alerts set at $20 (80% of $25 budget)")
    print("✅ Emergency alerts at $23.75 (95% of budget)")  
    print("✅ MOCK_AI_RESPONSES=true (no Bedrock costs initially)")
    print("✅ DynamoDB pay-per-request (no provisioned costs)")
    print("✅ Lambda free tier covers testing")
    
    print("\n🚨 MAXIMUM POSSIBLE COST WITH PROTECTIONS: $25/month")
    
    return total_base

if __name__ == "__main__":
    estimate_costs()
