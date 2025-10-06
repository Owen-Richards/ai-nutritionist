#!/usr/bin/env python3
"""
Standalone test of cost optimization logic without AWS dependencies
"""

import sys
sys.path.append('.')

from src.config.cost_optimization_config import (
    get_request_cost_estimate, 
    get_user_cost_limit,
    is_nutritional_query,
    is_complex_query,
    should_suggest_upgrade,
    cost_config
)
import re
from decimal import Decimal

def test_spam_detection(message: str) -> bool:
    """Test spam detection logic"""
    message_lower = message.lower()
    for pattern in cost_config.SPAM_PATTERNS:
        if re.search(pattern, message_lower):
            return True
    return False

def test_cost_optimization_logic():
    print('🧪 Testing Cost Optimization Logic (Standalone)')
    print('=' * 55)
    
    # Test 1: Valid nutrition request
    print('\n✅ Test 1: Valid nutrition request')
    message1 = 'What should I eat for breakfast to lose weight?'
    is_nutrition = is_nutritional_query(message1)
    is_complex = is_complex_query(message1)
    is_spam = test_spam_detection(message1)
    cost = get_request_cost_estimate('nutrition_analysis')
    
    print(f'Message: "{message1}"')
    print(f'Is Nutritional: {is_nutrition}')
    print(f'Is Complex: {is_complex}')
    print(f'Is Spam: {is_spam}')
    print(f'Estimated Cost: ${cost:.4f}')
    print(f'Decision: {"PROCESS" if is_nutrition and not is_spam else "REJECT"}')
    
    # Test 2: Spam request
    print('\n❌ Test 2: Spam request')
    message2 = 'CONGRATULATIONS! You won $1000000 in our casino lottery!'
    is_nutrition2 = is_nutritional_query(message2)
    is_spam2 = test_spam_detection(message2)
    
    print(f'Message: "{message2}"')
    print(f'Is Nutritional: {is_nutrition2}')
    print(f'Is Spam: {is_spam2}')
    print(f'Decision: {"PROCESS" if is_nutrition2 and not is_spam2 else "BLOCK_SPAM"}')
    
    # Test 3: Non-nutritional request
    print('\n⚠️  Test 3: Non-nutritional request')
    message3 = 'What is the weather today?'
    is_nutrition3 = is_nutritional_query(message3)
    is_spam3 = test_spam_detection(message3)
    
    print(f'Message: "{message3}"')
    print(f'Is Nutritional: {is_nutrition3}')
    print(f'Is Spam: {is_spam3}')
    print(f'Decision: {"PROCESS" if is_nutrition3 and not is_spam3 else "REDIRECT_TO_FAQ"}')
    
    # Test 4: Cost estimates
    print('\n💰 Test 4: Request type cost estimates')
    for request_type in ['simple_message', 'meal_plan', 'nutrition_analysis', 'image_analysis']:
        cost = get_request_cost_estimate(request_type)
        print(f'  {request_type:18}: ${cost:.4f}')
    
    # Test 5: User tier limits
    print('\n🎯 Test 5: User tier cost limits (daily)')
    for tier in ['free', 'premium', 'enterprise']:
        daily_limit = get_user_cost_limit(tier, 'daily')
        monthly_limit = get_user_cost_limit(tier, 'monthly')
        per_request = get_user_cost_limit(tier, 'per_request')
        print(f'  {tier:10}: ${daily_limit}/day, ${monthly_limit}/month, ${per_request}/request')
    
    # Test 6: Upgrade suggestions
    print('\n📈 Test 6: Upgrade suggestion logic')
    for request_count in [1, 2, 3, 4, 6, 9]:
        should_upgrade = should_suggest_upgrade('free', request_count)
        print(f'  Request #{request_count}: {"Suggest upgrade" if should_upgrade else "No suggestion"}')
    
    # Test 7: Complex query detection
    print('\n🧠 Test 7: Complex query detection')
    complex_queries = [
        'Create a weekly meal plan for weight loss',
        'Generate a shopping list for keto diet',
        'Analyze my macro breakdown for the day',
        'What should I eat?'  # Simple query
    ]
    
    for query in complex_queries:
        is_complex = is_complex_query(query)
        print(f'  "{query[:40]}...": {"Complex" if is_complex else "Simple"}')
    
    # Test 8: Configuration validation
    print('\n⚙️  Test 8: Configuration validation')
    from src.config.cost_optimization_config import validate_cost_config
    
    config_errors = validate_cost_config()
    if config_errors:
        print('  Configuration issues:')
        for error in config_errors:
            print(f'    ⚠️  {error}')
    else:
        print('  ✅ Configuration is valid!')
    
    # Test 9: Cost calculation simulation
    print('\n🧮 Test 9: Cost calculation simulation')
    scenarios = [
        ('free', 'nutrition_analysis', 10),     # 10 nutrition analysis requests
        ('premium', 'meal_plan', 5),            # 5 meal plan requests
        ('enterprise', 'image_analysis', 3),    # 3 image analysis requests
    ]
    
    for tier, request_type, count in scenarios:
        cost_per_request = get_request_cost_estimate(request_type)
        total_cost = cost_per_request * count
        daily_limit = get_user_cost_limit(tier, 'daily')
        
        print(f'  {tier} user, {count}x {request_type}:')
        print(f'    Total cost: ${total_cost:.4f}')
        print(f'    Daily limit: ${daily_limit:.4f}')
        print(f'    Status: {"✅ Within limit" if total_cost <= daily_limit else "❌ Exceeds limit"}')
        print()
    
    print('🎉 Cost optimization logic testing complete!')
    print('\n💡 Key Insights:')
    print('  • Spam detection prevents costly processing of non-legitimate requests')
    print('  • Nutritional relevance check ensures we only process relevant queries')
    print('  • Tiered pricing allows for different service levels')
    print('  • Complex query detection enables appropriate cost allocation')
    print('  • Configuration validation ensures system integrity')

if __name__ == '__main__':
    test_cost_optimization_logic()
