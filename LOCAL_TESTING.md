# 🧪 AI Nutritionist - Local Development & Testing Guide

## 🏠 Running Locally

You can test the AI Nutritionist locally in several ways before deploying to AWS:

### Option 1: Quick Python Tests (Easiest - No Docker Required)

```bash
# Run the comprehensive test suite
test-quick.bat

# Or run individual tests
python test_local.py
```

This will test:
- ✅ Database connections
- ✅ AI service functionality  
- ✅ Nutrition analysis
- ✅ Message handling
- ✅ Full integration scenarios

### Option 2: SAM Local API Gateway (Most Realistic)

#### Prerequisites
- Docker Desktop installed and running
- AWS SAM CLI installed

#### Start Local Server
```bash
# Start the local development server
start-local.bat

# Your local API will be available at: http://localhost:3000
```

#### Test Local Endpoints
```bash
# Test health endpoint
curl http://localhost:3000/health

# Test webhook endpoint with nutrition question
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "Body": "I want a healthy vegetarian meal plan for today with a $50 budget",
    "From": "+1234567890"
  }'

# Test billing webhook
curl -X POST http://localhost:3000/billing/webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "customer.subscription.created", "data": {"object": {"id": "sub_test"}}}'
```

### Option 3: Direct Function Testing

```bash
# Test specific handlers directly
cd src
python -c "
import sys, json
sys.path.append('.')
from handlers.universal_message_handler import lambda_handler

event = {
    'body': json.dumps({
        'Body': 'Create a meal plan for weight loss',
        'From': '+1234567890'
    }),
    'httpMethod': 'POST'
}

result = lambda_handler(event, {})
print(json.dumps(result, indent=2))
"
```

## 🔧 Local Environment Setup

### 1. Configure Local Environment

```bash
# 1. Copy the local environment template
copy .env.local .env

# 2. Edit .env with your test API keys
# - Use Edamam test/sandbox keys
# - Use Stripe test keys (sk_test_...)
# - Set MOCK_AI_RESPONSES=true for testing without real AI calls
```

### 2. Install Dependencies

```bash
# Ensure you have the virtual environment activated
.venv\Scripts\activate

# Install any missing packages
pip install -r requirements.txt
```

### 3. Set Up Local DynamoDB (Optional)

```bash
# Option A: Use AWS DynamoDB (easier)
# Just configure AWS credentials with: aws configure

# Option B: Run DynamoDB Local (completely offline)
# Download from: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html
# Start with: java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb
```

## 🧪 Testing Scenarios

### Basic Functionality Tests

```bash
# 1. Quick health check
python test_local.py

# 2. Test AI responses
python -c "
from src.services.ai_service import AIService
ai = AIService()
response = ai.generate_meal_plan('+1234567890', 'I want to lose weight', {})
print(response)
"

# 3. Test nutrition analysis
python -c "
from src.services.nutrition.tracker import NutritionTracker
tracker = NutritionTracker()
nutrition = tracker.analyze_nutrition('1 cup rice, chicken breast')
print(nutrition)
"
```

### User Journey Tests

```bash
# Test a complete user conversation
python -c "
import json
from src.handlers.universal_message_handler import lambda_handler

messages = [
    'Hi! I\'m new here',
    'I want to lose weight and I\'m vegetarian', 
    'My budget is $75 per week',
    'Can you create a meal plan for today?'
]

for msg in messages:
    event = {
        'body': json.dumps({'Body': msg, 'From': '+1234567890'}),
        'httpMethod': 'POST'
    }
    result = lambda_handler(event, {})
    print(f'User: {msg}')
    print(f'Bot: {json.loads(result[\"body\"])[\"message\"]}')
    print('-' * 50)
"
```

## 🚀 Testing with Real Messaging

### Ngrok Tunnel (Test with Real WhatsApp/SMS)

```bash
# 1. Install ngrok: https://ngrok.com/
# 2. Start your local server
start-local.bat

# 3. In another terminal, create tunnel
ngrok http 3000

# 4. Use the ngrok URL (e.g., https://abc123.ngrok.io) as your webhook URL
# 5. Configure in Twilio/WhatsApp Business Console
```

## 🔍 Debugging & Monitoring

### View Logs

```bash
# Local Python logs
python test_local.py

# SAM Local logs (automatically displayed)
# Shows in terminal when running start-local.bat

# Custom logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Your test code here
"
```

### Mock External Services

The local environment includes mocking for:
- ✅ **AI/Bedrock calls** - Returns pre-written responses
- ✅ **Edamam API** - Returns sample nutrition data  
- ✅ **Stripe payments** - Skips actual payment processing
- ✅ **SMS sending** - Logs instead of sending

### Performance Testing

```bash
# Test response times
python -c "
import time
from src.handlers.universal_message_handler import lambda_handler

start = time.time()
result = lambda_handler({
    'body': '{\"Body\": \"meal plan\", \"From\": \"+1234567890\"}',
    'httpMethod': 'POST'
}, {})
end = time.time()

print(f'Response time: {end - start:.2f} seconds')
print(f'Status: {result[\"statusCode\"]}')
"
```

## 🎯 What to Test Before Deployment

### ✅ Core Functionality Checklist

- [ ] **Message Processing** - Handles incoming messages correctly
- [ ] **AI Responses** - Generates relevant meal plans and advice
- [ ] **User Profiles** - Remembers preferences and dietary restrictions
- [ ] **Nutrition Analysis** - Processes food descriptions accurately
- [ ] **Payment Handling** - Processes subscription events (in test mode)
- [ ] **Error Handling** - Graceful failure for invalid inputs
- [ ] **Performance** - Response times under 5 seconds
- [ ] **Security** - No sensitive data in logs

### 🚨 Common Issues & Solutions

**Issue: Module import errors**
```bash
# Solution: Set PYTHONPATH
set PYTHONPATH=%cd%\src
python test_local.py
```

**Issue: AWS credentials not found**
```bash
# Solution: Configure AWS CLI
aws configure
# Or use local DynamoDB: set DYNAMODB_ENDPOINT_URL=http://localhost:8000
```

**Issue: Docker not running (for SAM Local)**
```bash
# Solution: Start Docker Desktop
# Then run: start-local.bat
```

**Issue: API rate limits**
```bash
# Solution: Use mock responses for testing
# Set MOCK_AI_RESPONSES=true in .env
```

## 🎉 Ready for Production?

Once local testing passes:

1. ✅ All tests in `test_local.py` pass
2. ✅ User journey flows work end-to-end  
3. ✅ Response times are acceptable
4. ✅ No errors in local logs
5. ✅ Mocked services behave as expected

**You're ready to deploy to AWS!** 🚀

```bash
# Deploy to production
bash deploy-production.sh
```
