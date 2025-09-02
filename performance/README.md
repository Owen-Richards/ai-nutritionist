# Performance Testing with Locust

This directory contains performance testing scripts using [Locust](https://locust.io/).

## Running Performance Tests

### Local Testing

1. **Install Locust**
   ```bash
   pip install locust
   ```

2. **Start your local API**
   ```bash
   sam local start-api
   ```

3. **Run Locust tests**
   ```bash
   cd performance/
   locust -f locustfile.py --host=http://localhost:3000
   ```

4. **Open the web UI**
   Navigate to http://localhost:8089

### Load Testing Scenarios

- **Baseline**: 10 users, 2 users/second spawn rate
- **Peak Load**: 100 users, 10 users/second spawn rate  
- **Stress Test**: 500 users, 25 users/second spawn rate
- **Endurance**: 50 users for 30 minutes

### Metrics to Monitor

- **Response Time**: p95 < 5 seconds for meal plans
- **Throughput**: > 100 requests/second
- **Error Rate**: < 1% for all endpoints
- **Resource Usage**: Memory, CPU, DynamoDB capacity

## Test Files

- `locustfile.py` - Main load testing scenarios
- `webhook_tests.py` - Twilio webhook simulation
- `ai_service_tests.py` - AI service performance tests
