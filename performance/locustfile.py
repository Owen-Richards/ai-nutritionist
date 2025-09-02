from locust import HttpUser, task, between
import json
import random


class NutritionistUser(HttpUser):
    """Simulates a user interacting with the AI Nutritionist bot."""
    
    wait_time = between(2, 10)  # Wait 2-10 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        self.user_id = f"test_user_{random.randint(1000, 9999)}"
        self.phone_number = f"+1555{random.randint(1000000, 9999999)}"
    
    @task(3)
    def send_meal_plan_request(self):
        """Simulate requesting a meal plan - most common action."""
        webhook_data = {
            "MessageSid": f"SM{random.randint(10**32, 10**33)}",
            "From": self.phone_number,
            "To": "+15551234567",
            "Body": "I need a meal plan for 2 people, budget $60, vegetarian",
            "AccountSid": "test_account_sid",
            "MessagingServiceSid": "test_messaging_sid"
        }
        
        with self.client.post(
            "/webhook",
            data=webhook_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def send_grocery_list_request(self):
        """Simulate requesting a grocery list."""
        webhook_data = {
            "MessageSid": f"SM{random.randint(10**32, 10**33)}",
            "From": self.phone_number,
            "To": "+15551234567",
            "Body": "grocery list",
            "AccountSid": "test_account_sid",
            "MessagingServiceSid": "test_messaging_sid"
        }
        
        self.client.post("/webhook", data=webhook_data)
    
    @task(1)
    def send_help_request(self):
        """Simulate requesting help - least resource intensive."""
        webhook_data = {
            "MessageSid": f"SM{random.randint(10**32, 10**33)}",
            "From": self.phone_number,
            "To": "+15551234567",
            "Body": "help",
            "AccountSid": "test_account_sid",
            "MessagingServiceSid": "test_messaging_sid"
        }
        
        self.client.post("/webhook", data=webhook_data)
    
    @task(1)
    def send_preferences_update(self):
        """Simulate updating dietary preferences."""
        preferences = [
            "I'm allergic to nuts",
            "I want to go keto",
            "No dairy please",
            "Gluten-free meals only",
            "Budget is now $80"
        ]
        
        webhook_data = {
            "MessageSid": f"SM{random.randint(10**32, 10**33)}",
            "From": self.phone_number,
            "To": "+15551234567",
            "Body": random.choice(preferences),
            "AccountSid": "test_account_sid",
            "MessagingServiceSid": "test_messaging_sid"
        }
        
        self.client.post("/webhook", data=webhook_data)


class AIServiceUser(HttpUser):
    """Simulates direct AI service calls for performance testing."""
    
    wait_time = between(1, 5)
    
    @task
    def test_ai_service_direct(self):
        """Test AI service performance directly."""
        # This would require exposing AI service endpoint for testing
        # In production, this would be internal only
        pass


# Custom test scenarios
class PeakHourTraffic(NutritionistUser):
    """Simulates peak hour traffic patterns."""
    weight = 3
    wait_time = between(1, 3)  # More aggressive timing


class LightUsage(NutritionistUser):
    """Simulates light usage periods."""
    weight = 1
    wait_time = between(10, 30)  # Longer gaps between requests
