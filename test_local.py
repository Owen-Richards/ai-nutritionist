#!/usr/bin/env python3
"""
AI Nutritionist - Local Testing Script
Test the core functionality locally without deploying to AWS
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_env_file(filename=".env.local"):
    """Load environment variables from file"""
    env_file = Path(filename)
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print(f"✅ Loaded environment from {filename}")
    else:
        print(f"⚠️  {filename} not found, using system environment")

def test_message_handler():
    """Test the universal message handler"""
    print("\n🧪 Testing Universal Message Handler...")
    
    try:
        from handlers.universal_message_handler import lambda_handler
        
        # Mock incoming message event
        event = {
            'body': json.dumps({
                'Body': 'I want a healthy meal plan for today. I\'m vegetarian and have a $50 budget.',
                'From': '+1234567890',
                'MessageSid': 'test-message-id'
            }),
            'httpMethod': 'POST',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        context = {
            'aws_request_id': 'test-request-id',
            'function_name': 'test-function'
        }
        
        result = lambda_handler(event, context)
        
        print(f"✅ Handler Response: {json.dumps(result, indent=2)}")
        return True
        
    except Exception as e:
        print(f"❌ Handler Test Failed: {str(e)}")
        logger.exception("Handler test error")
        return False

def test_ai_service():
    """Test the AI service directly"""
    print("\n🤖 Testing AI Service...")
    
    try:
        from services.ai_service import AIService
        
        ai_service = AIService()
        
        # Test meal plan generation
        user_profile = {
            'dietary_preferences': ['vegetarian'],
            'budget_limit': 50,
            'health_goals': ['weight_loss'],
            'allergies': []
        }
        
        meal_plan = ai_service.generate_meal_plan(
            user_phone="+1234567890",
            user_message="I want a healthy meal plan for today",
            user_profile=user_profile
        )
        
        print(f"✅ AI Response: {meal_plan}")
        return True
        
    except Exception as e:
        print(f"❌ AI Service Test Failed: {str(e)}")
        logger.exception("AI service test error")
        return False

def test_nutrition_service():
    """Test the nutrition service"""
    print("\n🥗 Testing Nutrition Service...")
    
    try:
        from services.nutrition.tracker import NutritionTracker
        
        tracker = NutritionTracker()
        
        # Test nutrition analysis
        food_text = "1 cup of brown rice, grilled chicken breast, steamed broccoli"
        nutrition_data = tracker.analyze_nutrition(food_text)
        
        print(f"✅ Nutrition Analysis: {nutrition_data}")
        return True
        
    except Exception as e:
        print(f"❌ Nutrition Service Test Failed: {str(e)}")
        logger.exception("Nutrition service test error")
        return False

def test_database_connection():
    """Test DynamoDB connection"""
    print("\n🗄️ Testing Database Connection...")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Try to connect to DynamoDB
        if os.getenv('DYNAMODB_ENDPOINT_URL'):
            # Local DynamoDB
            dynamodb = boto3.resource('dynamodb', 
                                    endpoint_url=os.getenv('DYNAMODB_ENDPOINT_URL'))
        else:
            # AWS DynamoDB
            dynamodb = boto3.resource('dynamodb')
        
        # List tables
        tables = list(dynamodb.tables.all())
        print(f"✅ Connected to DynamoDB. Tables: {[t.name for t in tables]}")
        return True
        
    except ClientError as e:
        print(f"❌ DynamoDB Connection Failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Database Test Failed: {str(e)}")
        return False

def run_integration_test():
    """Run a full integration test"""
    print("\n🔄 Running Integration Test...")
    
    # Simulate a complete user interaction
    test_messages = [
        "Hi! I'm new here",
        "I want to lose weight and I'm vegetarian",
        "My budget is $75 per week",
        "Can you create a meal plan for today?",
        "What's the nutrition info for this meal?"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Message {i}: {message} ---")
        
        try:
            from handlers.universal_message_handler import lambda_handler
            
            event = {
                'body': json.dumps({
                    'Body': message,
                    'From': '+1234567890',
                    'MessageSid': f'test-message-{i}'
                }),
                'httpMethod': 'POST'
            }
            
            result = lambda_handler(event, {})
            
            if result.get('statusCode') == 200:
                response_body = json.loads(result.get('body', '{}'))
                print(f"✅ Response: {response_body.get('message', 'No message')}")
            else:
                print(f"⚠️  Response: {result}")
                
        except Exception as e:
            print(f"❌ Message {i} failed: {str(e)}")

def main():
    """Main testing function"""
    print("🚀 AI Nutritionist - Local Testing Suite")
    print("=" * 50)
    
    # Load environment variables
    load_env_file()
    
    # Run tests
    tests = [
        ("Database Connection", test_database_connection),
        ("AI Service", test_ai_service),
        ("Nutrition Service", test_nutrition_service),
        ("Message Handler", test_message_handler),
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    # Run integration test
    print("\n" + "=" * 50)
    run_integration_test()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 Tests Passed: {sum(results.values())}/{len(results)}")
    
    if all(results.values()):
        print("🎉 All tests passed! Ready for deployment.")
    else:
        print("⚠️  Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main()
