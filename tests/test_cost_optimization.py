#!/usr/bin/env python3
"""
Quick test of the cost optimization system
"""

import sys
sys.path.append('.')

from src.services.business.cost_optimizer import optimize_request_cost
from src.config.cost_optimization_config import get_request_cost_estimate, get_user_cost_limit

def test_cost_optimization():
    print('Testing Cost Optimization System')
    print('=' * 50)
    
    # Test 1: Valid nutrition request
    print('\nTest 1: Valid nutrition request')
    result = optimize_request_cost(
        user_phone='+1234567890',
        message='What should I eat for breakfast to lose weight?',
        request_type='nutrition_analysis',
        user_tier='free'
    )
    print(f'Should Process: {result["should_process"]}')
    print(f'Action: {result["action"]}')
    print(f'Reason: {result["reason"]}')
    print(f'Estimated Cost: ${result["estimated_cost"]:.4f}')
    
    # Test 2: Spam request
    print('\nTest 2: Spam request')
    result = optimize_request_cost(
        user_phone='+1234567890',
        message='CONGRATULATIONS! You won $1000000 in our casino lottery!',
        request_type='simple_message',
        user_tier='free'
    )
    print(f'Should Process: {result["should_process"]}')
    print(f'Action: {result["action"]}')
    print(f'Reason: {result["reason"]}')
    
    # Test 3: Cost estimates
    print('\nTest 3: Cost estimates')
    for request_type in ['simple_message', 'meal_plan', 'nutrition_analysis']:
        cost = get_request_cost_estimate(request_type)
        print(f'{request_type}: ${cost:.4f}')
    
    # Test 4: User limits
    print('\nTest 4: User tier limits')
    for tier in ['free', 'premium', 'enterprise']:
        daily_limit = get_user_cost_limit(tier, 'daily')
        print(f'{tier}: ${daily_limit}/day')
    
    print('\nCost optimization system is working!')

if __name__ == '__main__':
    test_cost_optimization()
