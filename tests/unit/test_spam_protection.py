#!/usr/bin/env python3
"""
Test AWS SMS Spam Protection
Validates rate limiting, spam detection, and cost controls
"""

import json
import time
import boto3
from typing import Dict, Any, List
import random
import string

# Test configuration
TEST_PHONE_NUMBERS = [
    '+15551234567',  # Test number 1
    '+15551234568',  # Test number 2
    '+15551234569',  # Test number 3 (will be used for spam)
]

LEGITIMATE_MESSAGES = [
    "I need a meal plan for 2 people with a $30 budget",
    "What are some healthy breakfast options?",
    "Can you suggest a vegetarian recipe?",
    "I have diabetes, what should I eat?",
    "Help me plan meals for this week",
]

SPAM_MESSAGES = [
    "CONGRATULATIONS! You've WON $1000000! Click here NOW to claim your FREE prize!",
    "URGENT! Your account will be closed unless you click this link immediately!",
    "Amazing investment opportunity! Get rich quick! Call now!",
    "Meet hot singles in your area! Click here for instant access!",
    "FREE VIAGRA! Order now and save 90%! Limited time offer!",
]

class SMSProtectionTester:
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.sms_client = boto3.client('pinpoint-sms-voice-v2')  # AWS End User Messaging SMS API
        self.results = []
        
    def test_spam_detection(self):
        """Test spam detection capabilities"""
        print("🧠 Testing Spam Detection...")
        
        for i, spam_msg in enumerate(SPAM_MESSAGES):
            phone = TEST_PHONE_NUMBERS[0]
            result = self._check_message(phone, spam_msg)
            
            spam_score = result.get('metadata', {}).get('spam_score', 0)
            allowed = result.get('allowed', True)
            
            print(f"  Test {i+1}: Spam score: {spam_score:.2f}, Allowed: {allowed}")
            
            # High spam should be blocked
            if spam_score > 0.7 and allowed:
                print(f"  ❌ FAIL: High spam message was allowed")
            elif spam_score > 0.7 and not allowed:
                print(f"  ✅ PASS: High spam message was blocked")
            else:
                print(f"  ⚠️  WARN: Spam score lower than expected")
                
            self.results.append({
                'test': 'spam_detection',
                'message': spam_msg[:50],
                'spam_score': spam_score,
                'allowed': allowed,
                'passed': spam_score > 0.5
            })
            
            time.sleep(1)  # Avoid rate limiting during test
    
    def test_legitimate_messages(self):
        """Test that legitimate messages are not blocked"""
        print("✅ Testing Legitimate Messages...")
        
        for i, legit_msg in enumerate(LEGITIMATE_MESSAGES):
            phone = TEST_PHONE_NUMBERS[1]
            result = self._check_message(phone, legit_msg)
            
            spam_score = result.get('metadata', {}).get('spam_score', 0)
            allowed = result.get('allowed', True)
            
            print(f"  Test {i+1}: Spam score: {spam_score:.2f}, Allowed: {allowed}")
            
            # Legitimate messages should be allowed
            if spam_score < 0.3 and allowed:
                print(f"  ✅ PASS: Legitimate message was allowed")
            elif not allowed:
                print(f"  ❌ FAIL: Legitimate message was blocked")
            else:
                print(f"  ⚠️  WARN: Spam score higher than expected for legitimate message")
                
            self.results.append({
                'test': 'legitimate_messages',
                'message': legit_msg[:50],
                'spam_score': spam_score,
                'allowed': allowed,
                'passed': allowed and spam_score < 0.5
            })
            
            time.sleep(1)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        print("⏰ Testing Rate Limiting...")
        
        phone = TEST_PHONE_NUMBERS[2]
        test_message = "Test rate limiting message"
        
        # Send messages rapidly to trigger rate limiting
        for i in range(15):
            result = self._check_message(phone, f"{test_message} {i+1}")
            allowed = result.get('allowed', True)
            reason = result.get('reason', 'unknown')
            
            print(f"  Message {i+1}: Allowed: {allowed}, Reason: {reason}")
            
            if i >= 10 and allowed:  # Should be rate limited after 10 messages
                print(f"  ❌ FAIL: Message {i+1} should have been rate limited")
            elif i >= 10 and not allowed and 'rate_limit' in reason:
                print(f"  ✅ PASS: Message {i+1} was properly rate limited")
            
            self.results.append({
                'test': 'rate_limiting',
                'message_number': i+1,
                'allowed': allowed,
                'reason': reason,
                'passed': (i < 10 and allowed) or (i >= 10 and not allowed)
            })
            
            time.sleep(0.5)  # Small delay between messages
    
    def test_user_reputation(self):
        """Test user reputation system"""
        print("📊 Testing User Reputation...")
        
        phone = TEST_PHONE_NUMBERS[0]
        
        # Send mix of legitimate and spam messages
        messages = [
            ("I want a healthy meal plan", False),  # Legitimate
            ("What's good for breakfast?", False),   # Legitimate  
            ("FREE MONEY! CLICK NOW!", True),       # Spam
            ("Can you help with recipes?", False),  # Legitimate
            ("WIN BIG! URGENT CALL NOW!", True),    # Spam
        ]
        
        for msg, is_spam in messages:
            result = self._check_message(phone, msg)
            spam_score = result.get('metadata', {}).get('spam_score', 0)
            allowed = result.get('allowed', True)
            
            expected_blocked = is_spam and spam_score > 0.7
            
            print(f"  Message: '{msg[:30]}...' - Score: {spam_score:.2f}, Allowed: {allowed}")
            
            if is_spam and not allowed:
                print(f"  ✅ PASS: Spam message was blocked")
            elif not is_spam and allowed:
                print(f"  ✅ PASS: Legitimate message was allowed")
            else:
                print(f"  ⚠️  Result may vary based on reputation")
            
            time.sleep(1)
    
    def test_cost_monitoring(self):
        """Test cost monitoring and alerts"""
        print("💰 Testing Cost Monitoring...")
        
        # This would test cost calculations in a real environment
        # For testing, we'll simulate the check
        
        try:
            # Check if cost monitoring Lambda exists
            response = self.lambda_client.get_function(
                FunctionName='ai-nutritionist-prod-spam-protection'
            )
            print("  ✅ PASS: Spam protection Lambda function exists")
            
            # Test daily cost analysis trigger
            test_event = {
                'action': 'daily_cost_analysis'
            }
            
            response = self.lambda_client.invoke(
                FunctionName='ai-nutritionist-prod-spam-protection',
                Payload=json.dumps(test_event)
            )
            
            if response['StatusCode'] == 200:
                print("  ✅ PASS: Daily cost analysis function works")
            else:
                print("  ❌ FAIL: Daily cost analysis function failed")
                
        except Exception as e:
            print(f"  ❌ FAIL: Cost monitoring test failed: {str(e)}")
    
    def test_blocking_functionality(self):
        """Test number blocking functionality"""
        print("🚫 Testing Number Blocking...")
        
        test_phone = '+15559999999'  # Test number for blocking
        
        try:
            # Test manual blocking
            block_event = {
                'action': 'block_number',
                'phone_number': test_phone,
                'reason': 'test_block'
            }
            
            response = self.lambda_client.invoke(
                FunctionName='ai-nutritionist-prod-spam-protection',
                Payload=json.dumps(block_event)
            )
            
            if response['StatusCode'] == 200:
                print(f"  ✅ PASS: Successfully blocked {test_phone}")
                
                # Test that blocked number is rejected
                result = self._check_message(test_phone, "Test message")
                if not result.get('allowed', True):
                    print("  ✅ PASS: Blocked number was rejected")
                else:
                    print("  ❌ FAIL: Blocked number was not rejected")
            else:
                print("  ❌ FAIL: Number blocking failed")
                
        except Exception as e:
            print(f"  ❌ FAIL: Blocking test failed: {str(e)}")
    
    def _check_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Helper method to check a message through spam protection"""
        try:
            event = {
                'action': 'check_message',
                'phone_number': phone_number,
                'message': message,
                'country_code': 'US'
            }
            
            response = self.lambda_client.invoke(
                FunctionName='ai-nutritionist-prod-spam-protection',
                Payload=json.dumps(event)
            )
            
            if response['StatusCode'] == 200:
                result = json.loads(response['Payload'].read())
                return json.loads(result['body'])
            else:
                return {'allowed': True, 'reason': 'check_failed'}
                
        except Exception as e:
            print(f"  Error checking message: {str(e)}")
            return {'allowed': True, 'reason': 'error', 'error': str(e)}
    
    def run_all_tests(self):
        """Run all spam protection tests"""
        print("🛡️  Starting SMS Spam Protection Tests\n")
        
        try:
            self.test_legitimate_messages()
            print()
            
            self.test_spam_detection()
            print()
            
            self.test_rate_limiting()
            print()
            
            self.test_user_reputation()
            print()
            
            self.test_cost_monitoring()
            print()
            
            self.test_blocking_functionality()
            print()
            
            self._print_summary()
            
        except Exception as e:
            print(f"❌ Test suite failed: {str(e)}")
    
    def _print_summary(self):
        """Print test results summary"""
        print("📊 Test Results Summary")
        print("=" * 50)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get('passed', False))
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        for i, result in enumerate(self.results, 1):
            status = "✅ PASS" if result.get('passed', False) else "❌ FAIL"
            test_type = result.get('test', 'unknown')
            print(f"  {i}. {test_type}: {status}")
        
        if passed_tests / total_tests >= 0.8:
            print("\n🎉 Spam protection is working well!")
        else:
            print("\n⚠️  Some protection features need attention.")


if __name__ == "__main__":
    tester = SMSProtectionTester()
    tester.run_all_tests()
