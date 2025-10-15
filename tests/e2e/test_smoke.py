"""
Smoke Tests for E2E Framework

Quick validation tests to ensure the E2E testing framework
is working correctly before running full test suites.
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path

# Add the tests/e2e directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from framework import (
    create_test_environment, TestUser, TestResult
)
from utils.automation import SeleniumAutomation, APIAutomation


@pytest.mark.smoke
class TestE2EFrameworkSmoke:
    """Smoke tests for E2E framework components"""
    
    def test_test_environment_creation(self):
        """Test that test environments can be created"""
        env = create_test_environment("local")
        
        assert env.environment == "local"
        assert env.web_app_url
        assert env.api_base_url
        assert env.database_config
        assert env.messaging_config
    
    def test_test_user_creation(self):
        """Test that test users can be created"""
        user = TestUser(
            user_id="test_smoke_user",
            phone_number="+15551234567",
            email="smoke@test.com",
            name="Smoke Test User",
            dietary_preferences=["vegetarian"],
            health_goals=["weight_loss"]
        )
        
        assert user.user_id == "test_smoke_user"
        assert user.phone_number == "+15551234567"
        assert user.email == "smoke@test.com"
        assert "vegetarian" in user.dietary_preferences
        assert "weight_loss" in user.health_goals
    
    def test_selenium_automation_setup(self):
        """Test that Selenium automation can be set up"""
        selenium = SeleniumAutomation(browser="chrome", headless=True)
        
        try:
            driver = selenium.setup_driver()
            assert driver is not None
            
            # Test basic navigation
            driver.get("https://www.google.com")
            assert "Google" in driver.title
            
        finally:
            selenium.close_driver()
    
    @pytest.mark.asyncio
    async def test_api_automation_setup(self):
        """Test that API automation can be set up"""
        api = APIAutomation("https://httpbin.org")
        
        try:
            await api.create_session()
            
            # Test basic API call
            response = await api.get("/get")
            
            assert response['status'] == 200
            assert response['success'] is True
            
        finally:
            await api.close_session()
    
    def test_test_result_creation(self):
        """Test that test results can be created"""
        result = TestResult(
            test_name="SmokeTest",
            status="passed",
            duration=1.5,
            metrics={'response_time': 200}
        )
        
        assert result.test_name == "SmokeTest"
        assert result.status == "passed"
        assert result.duration == 1.5
        assert result.metrics['response_time'] == 200


@pytest.mark.smoke
class TestE2EConfigurationSmoke:
    """Smoke tests for E2E configuration"""
    
    def test_config_import(self):
        """Test that configuration can be imported"""
        from config import E2ETestConfig, BROWSER_CONFIGS, PERFORMANCE_SCENARIOS
        
        config = E2ETestConfig()
        assert config.config is not None
        
        assert "chrome" in BROWSER_CONFIGS
        assert "firefox" in BROWSER_CONFIGS
        
        assert "daily_usage" in PERFORMANCE_SCENARIOS
    
    def test_browser_configs(self):
        """Test browser configurations"""
        from config import BROWSER_CONFIGS
        
        # Test Chrome config
        chrome_config = BROWSER_CONFIGS["chrome"]
        assert chrome_config["driver"] == "chromedriver"
        assert isinstance(chrome_config["options"], list)
        assert chrome_config["capabilities"]["browserName"] == "chrome"
        
        # Test Firefox config
        firefox_config = BROWSER_CONFIGS["firefox"]
        assert firefox_config["driver"] == "geckodriver"
        assert firefox_config["capabilities"]["browserName"] == "firefox"
    
    def test_performance_scenarios(self):
        """Test performance scenario configurations"""
        from config import PERFORMANCE_SCENARIOS
        
        # Test daily usage scenario
        daily_usage = PERFORMANCE_SCENARIOS["daily_usage"]
        assert daily_usage["description"]
        assert "operations" in daily_usage
        assert len(daily_usage["operations"]) > 0
        
        # Test operations have required fields
        for operation in daily_usage["operations"]:
            assert "action" in operation
            assert "weight" in operation


@pytest.mark.smoke
class TestE2EFixturesSmoke:
    """Smoke tests for E2E fixtures"""
    
    def test_fixture_imports(self):
        """Test that fixtures can be imported"""
        from fixtures.test_fixtures import (
            test_user, test_users, premium_test_user, family_test_user,
            test_meal_data, test_recipe_data, test_subscription_data
        )
        
        # Just test that imports work
        assert test_user is not None
        assert test_users is not None
        assert premium_test_user is not None
    
    @pytest.mark.asyncio
    async def test_test_environment_fixture(self, test_environment):
        """Test test environment fixture"""
        assert test_environment.environment in ["local", "staging"]
        assert test_environment.web_app_url
        assert test_environment.api_base_url
    
    def test_test_user_fixture(self, test_user):
        """Test test user fixture"""
        assert test_user.user_id
        assert test_user.phone_number
        assert test_user.email
        assert test_user.name
        assert isinstance(test_user.dietary_preferences, list)
        assert isinstance(test_user.health_goals, list)
    
    def test_test_meal_data_fixture(self, test_meal_data):
        """Test meal data fixture"""
        assert "breakfast" in test_meal_data
        assert "lunch" in test_meal_data
        assert "dinner" in test_meal_data
        
        breakfast = test_meal_data["breakfast"]
        assert "name" in breakfast
        assert "calories" in breakfast
        assert "protein" in breakfast
        assert "ingredients" in breakfast


@pytest.mark.smoke
class TestE2EUtilitiesSmoke:
    """Smoke tests for E2E utilities"""
    
    def test_automation_imports(self):
        """Test that automation utilities can be imported"""
        from utils.automation import (
            SeleniumAutomation,
            APIAutomation,
            MessageSimulationAutomation,
            DatabaseVerificationAutomation
        )
        
        # Test instantiation
        selenium = SeleniumAutomation()
        assert selenium.browser == "chrome"
        assert selenium.headless is True
        
        api = APIAutomation("http://localhost:8000")
        assert api.base_url == "http://localhost:8000"
    
    def test_selenium_utility_methods(self):
        """Test Selenium utility methods"""
        from utils.automation import SeleniumAutomation
        
        selenium = SeleniumAutomation(headless=True)
        
        # Test method existence
        assert hasattr(selenium, 'setup_driver')
        assert hasattr(selenium, 'navigate_to')
        assert hasattr(selenium, 'find_element_safe')
        assert hasattr(selenium, 'take_screenshot')
        assert hasattr(selenium, 'close_driver')
    
    @pytest.mark.asyncio
    async def test_api_utility_methods(self):
        """Test API utility methods"""
        from utils.automation import APIAutomation
        
        api = APIAutomation("https://httpbin.org")
        
        # Test method existence
        assert hasattr(api, 'create_session')
        assert hasattr(api, 'make_request')
        assert hasattr(api, 'get')
        assert hasattr(api, 'post')
        assert hasattr(api, 'close_session')


@pytest.mark.smoke
class TestE2EIntegrationSmoke:
    """Smoke tests for E2E integration points"""
    
    @pytest.mark.asyncio
    async def test_local_api_health_check(self):
        """Test local API health check if available"""
        from utils.automation import APIAutomation
        
        api = APIAutomation("http://localhost:8000")
        
        try:
            await api.create_session()
            
            # Try to hit health endpoint
            response = await api.get("/health")
            
            # If API is running, should get 200
            # If not running, will get connection error
            if response.get('status') == 200:
                assert response['success'] is True
                print("✅ Local API is running and healthy")
            else:
                print("ℹ️ Local API not running - expected for some test environments")
        
        except Exception as e:
            print(f"ℹ️ Local API connection failed: {e}")
            # This is expected if API is not running
        
        finally:
            await api.close_session()
    
    def test_local_web_app_availability(self):
        """Test local web app availability if running"""
        from utils.automation import SeleniumAutomation
        
        selenium = SeleniumAutomation(headless=True)
        
        try:
            driver = selenium.setup_driver()
            
            # Try to navigate to local web app
            try:
                driver.get("http://localhost:3000")
                
                # If successful, page should load
                if driver.current_url.startswith("http://localhost:3000"):
                    print("✅ Local web app is running")
                    assert True
                else:
                    print("ℹ️ Local web app redirected or not running")
            
            except Exception as e:
                print(f"ℹ️ Local web app not available: {e}")
                # This is expected if web app is not running
        
        finally:
            selenium.close_driver()


if __name__ == "__main__":
    # Run smoke tests directly
    pytest.main([__file__, "-v", "-m", "smoke"])
