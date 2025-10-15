"""
E2E Test Framework Base Classes and Infrastructure

Provides:
- Base test classes for different test types
- Test data management
- Environment setup/teardown
- Common utilities and assertions
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from unittest.mock import Mock, AsyncMock, patch
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions


@dataclass
class TestUser:
    """Test user data model"""
    user_id: str
    phone_number: str
    email: str
    name: str
    dietary_preferences: List[str]
    health_goals: List[str]
    subscription_tier: str = "free"
    family_members: List[Dict[str, Any]] = None
    onboarding_completed: bool = False
    
    def __post_init__(self):
        if self.family_members is None:
            self.family_members = []


@dataclass
class TestEnvironment:
    """Test environment configuration"""
    environment: str  # local, staging, production
    api_base_url: str
    web_app_url: str
    database_config: Dict[str, Any]
    messaging_config: Dict[str, Any]
    ai_config: Dict[str, Any]
    payment_config: Dict[str, Any]
    
    def is_local(self) -> bool:
        return self.environment == "local"
    
    def is_staging(self) -> bool:
        return self.environment == "staging"
    
    def is_production(self) -> bool:
        return self.environment == "production"


@dataclass
class TestResult:
    """Test execution result tracking"""
    test_name: str
    status: str  # passed, failed, skipped
    duration: float
    error_message: Optional[str] = None
    screenshots: List[str] = None
    logs: List[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.screenshots is None:
            self.screenshots = []
        if self.logs is None:
            self.logs = []
        if self.metrics is None:
            self.metrics = {}


class BaseE2ETest(ABC):
    """Base class for all E2E tests"""
    
    def __init__(self, environment: TestEnvironment):
        self.environment = environment
        self.test_data: Dict[str, Any] = {}
        self.test_users: List[TestUser] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    @abstractmethod
    async def setup(self) -> None:
        """Setup test environment and data"""
        pass
    
    @abstractmethod
    async def execute(self) -> TestResult:
        """Execute the test scenario"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up test data and resources"""
        pass
    
    async def run(self) -> TestResult:
        """Run the complete test workflow"""
        self.start_time = datetime.utcnow()
        
        try:
            await self.setup()
            result = await self.execute()
            return result
        except Exception as e:
            return TestResult(
                test_name=self.__class__.__name__,
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
        finally:
            await self.cleanup()
            self.end_time = datetime.utcnow()
    
    def _get_duration(self) -> float:
        """Calculate test duration"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def create_test_user(self, **kwargs) -> TestUser:
        """Create a test user with default or custom data"""
        defaults = {
            'user_id': f"test_user_{int(time.time())}",
            'phone_number': f"+1555{int(time.time()) % 10000:04d}",
            'email': f"test{int(time.time())}@example.com",
            'name': f"Test User {int(time.time())}",
            'dietary_preferences': ['vegetarian'],
            'health_goals': ['weight_loss']
        }
        defaults.update(kwargs)
        
        user = TestUser(**defaults)
        self.test_users.append(user)
        return user


class WebE2ETest(BaseE2ETest):
    """Base class for web application E2E tests using Selenium"""
    
    def __init__(self, environment: TestEnvironment, browser: str = "chrome"):
        super().__init__(environment)
        self.browser = browser
        self.driver: Optional[webdriver.Remote] = None
        self.wait: Optional[WebDriverWait] = None
        
    async def setup(self) -> None:
        """Setup web driver and navigate to application"""
        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.driver.get(self.environment.web_app_url)
    
    async def cleanup(self) -> None:
        """Close web driver and clean up"""
        if self.driver:
            self.driver.quit()
    
    def _create_driver(self) -> webdriver.Remote:
        """Create web driver based on browser configuration"""
        if self.browser.lower() == "chrome":
            options = ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            return webdriver.Chrome(options=options)
        elif self.browser.lower() == "firefox":
            options = FirefoxOptions()
            options.add_argument("--headless")
            return webdriver.Firefox(options=options)
        else:
            raise ValueError(f"Unsupported browser: {self.browser}")
    
    def take_screenshot(self, name: str) -> str:
        """Take a screenshot and return the file path"""
        if not self.driver:
            return ""
        
        filename = f"screenshot_{name}_{int(time.time())}.png"
        filepath = f"tests/e2e/screenshots/{filename}"
        self.driver.save_screenshot(filepath)
        return filepath
    
    def wait_for_element(self, locator: tuple, timeout: int = 10) -> Any:
        """Wait for element to be present and return it"""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located(locator))
    
    def wait_for_clickable(self, locator: tuple, timeout: int = 10) -> Any:
        """Wait for element to be clickable and return it"""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.element_to_be_clickable(locator))


class APIE2ETest(BaseE2ETest):
    """Base class for API E2E tests"""
    
    def __init__(self, environment: TestEnvironment):
        super().__init__(environment)
        self.session = None
        
    async def setup(self) -> None:
        """Setup HTTP session for API calls"""
        import aiohttp
        self.session = aiohttp.ClientSession(
            base_url=self.environment.api_base_url,
            headers={'Content-Type': 'application/json'}
        )
    
    async def cleanup(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an API request and return response"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        async with self.session.request(method, path, **kwargs) as response:
            response_data = {
                'status': response.status,
                'headers': dict(response.headers),
                'body': await response.json() if response.content_type == 'application/json' else await response.text()
            }
            return response_data


class MessagingE2ETest(BaseE2ETest):
    """Base class for messaging channel E2E tests"""
    
    def __init__(self, environment: TestEnvironment, channel: str):
        super().__init__(environment)
        self.channel = channel  # whatsapp, sms, imessage
        self.message_simulator = None
        
    async def setup(self) -> None:
        """Setup message simulation environment"""
        self.message_simulator = MessageSimulator(
            channel=self.channel,
            config=self.environment.messaging_config
        )
    
    async def send_message(self, user: TestUser, message: str) -> Dict[str, Any]:
        """Send a message from user"""
        return await self.message_simulator.send_message(
            from_number=user.phone_number,
            message=message
        )
    
    async def receive_message(self, timeout: int = 30) -> Dict[str, Any]:
        """Wait for and receive a message response"""
        return await self.message_simulator.receive_message(timeout=timeout)


class MessageSimulator:
    """Simulates messaging interactions for different channels"""
    
    def __init__(self, channel: str, config: Dict[str, Any]):
        self.channel = channel
        self.config = config
        self.message_queue: List[Dict[str, Any]] = []
        
    async def send_message(self, from_number: str, message: str) -> Dict[str, Any]:
        """Simulate sending a message"""
        message_data = {
            'from': from_number,
            'body': message,
            'channel': self.channel,
            'timestamp': datetime.utcnow().isoformat(),
            'message_id': f"msg_{int(time.time())}"
        }
        
        # Add to queue for processing
        self.message_queue.append(message_data)
        
        # Simulate webhook call to application
        await self._trigger_webhook(message_data)
        
        return message_data
    
    async def receive_message(self, timeout: int = 30) -> Dict[str, Any]:
        """Wait for a response message"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for response messages
            responses = await self._check_responses()
            if responses:
                return responses[0]
            
            await asyncio.sleep(0.5)
        
        raise TimeoutError("No response received within timeout period")
    
    async def _trigger_webhook(self, message_data: Dict[str, Any]) -> None:
        """Trigger webhook to simulate incoming message"""
        # This would make an actual HTTP request to the webhook endpoint
        # For now, we'll mock this
        pass
    
    async def _check_responses(self) -> List[Dict[str, Any]]:
        """Check for response messages"""
        # This would check the outbound message queue/logs
        # For now, we'll mock this
        return []


class PerformanceE2ETest(BaseE2ETest):
    """Base class for performance E2E tests"""
    
    def __init__(self, environment: TestEnvironment, load_config: Dict[str, Any]):
        super().__init__(environment)
        self.load_config = load_config
        self.metrics: Dict[str, List[float]] = {
            'response_times': [],
            'throughput': [],
            'error_rates': [],
            'cpu_usage': [],
            'memory_usage': []
        }
    
    async def execute_load_test(self, duration: int, concurrent_users: int) -> Dict[str, Any]:
        """Execute load test with specified parameters"""
        tasks = []
        
        for i in range(concurrent_users):
            user = self.create_test_user()
            task = asyncio.create_task(self._user_simulation(user, duration))
            tasks.append(task)
        
        # Run all user simulations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate metrics
        return self._aggregate_metrics(results)
    
    async def _user_simulation(self, user: TestUser, duration: int) -> Dict[str, Any]:
        """Simulate a single user's behavior for the test duration"""
        start_time = time.time()
        operations = 0
        errors = 0
        
        while time.time() - start_time < duration:
            try:
                # Simulate user operations
                await self._simulate_user_operation(user)
                operations += 1
            except Exception:
                errors += 1
            
            # Random delay between operations
            await asyncio.sleep(0.5 + (time.time() % 2))
        
        return {
            'user_id': user.user_id,
            'operations': operations,
            'errors': errors,
            'duration': time.time() - start_time
        }
    
    @abstractmethod
    async def _simulate_user_operation(self, user: TestUser) -> None:
        """Simulate a single user operation - to be implemented by subclasses"""
        pass
    
    def _aggregate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate performance metrics from all user simulations"""
        total_operations = sum(r.get('operations', 0) for r in results if isinstance(r, dict))
        total_errors = sum(r.get('errors', 0) for r in results if isinstance(r, dict))
        total_duration = max(r.get('duration', 0) for r in results if isinstance(r, dict))
        
        return {
            'total_operations': total_operations,
            'total_errors': total_errors,
            'error_rate': (total_errors / total_operations) if total_operations > 0 else 0,
            'throughput': total_operations / total_duration if total_duration > 0 else 0,
            'duration': total_duration
        }


class E2ETestRunner:
    """Orchestrates E2E test execution and reporting"""
    
    def __init__(self, environment: TestEnvironment):
        self.environment = environment
        self.test_results: List[TestResult] = []
        
    async def run_test_suite(self, test_classes: List[type]) -> Dict[str, Any]:
        """Run a complete test suite"""
        results = []
        
        for test_class in test_classes:
            test_instance = test_class(self.environment)
            result = await test_instance.run()
            results.append(result)
            self.test_results.append(result)
        
        return self._generate_report(results)
    
    def _generate_report(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        passed = len([r for r in results if r.status == "passed"])
        failed = len([r for r in results if r.status == "failed"])
        skipped = len([r for r in results if r.status == "skipped"])
        total_duration = sum(r.duration for r in results)
        
        return {
            'summary': {
                'total_tests': len(results),
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'success_rate': (passed / len(results)) * 100 if results else 0,
                'total_duration': total_duration
            },
            'results': [asdict(r) for r in results],
            'environment': asdict(self.environment),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def run_continuous_testing(self, interval_minutes: int = 60) -> None:
        """Run continuous E2E testing at specified intervals"""
        while True:
            print(f"Starting E2E test run at {datetime.utcnow()}")
            
            # This would run your test suite
            # For now, we'll just wait
            await asyncio.sleep(interval_minutes * 60)


# Test configuration and factory functions
def create_test_environment(env_name: str = "local") -> TestEnvironment:
    """Create test environment configuration"""
    environments = {
        "local": TestEnvironment(
            environment="local",
            api_base_url="http://localhost:8000",
            web_app_url="http://localhost:3000",
            database_config={"type": "sqlite", "url": ":memory:"},
            messaging_config={"mock": True},
            ai_config={"mock": True},
            payment_config={"mock": True}
        ),
        "staging": TestEnvironment(
            environment="staging",
            api_base_url="https://staging-api.ai-nutritionist.com",
            web_app_url="https://staging.ai-nutritionist.com",
            database_config={"type": "postgresql", "url": "staging_db_url"},
            messaging_config={"provider": "aws_pinpoint"},
            ai_config={"provider": "openai"},
            payment_config={"provider": "stripe"}
        ),
        "production": TestEnvironment(
            environment="production",
            api_base_url="https://api.ai-nutritionist.com",
            web_app_url="https://ai-nutritionist.com",
            database_config={"type": "postgresql", "url": "prod_db_url"},
            messaging_config={"provider": "aws_pinpoint"},
            ai_config={"provider": "openai"},
            payment_config={"provider": "stripe"}
        )
    }
    
    return environments.get(env_name, environments["local"])


# Utility functions for test data management
def generate_test_data(data_type: str, count: int = 1) -> List[Dict[str, Any]]:
    """Generate test data for various entities"""
    generators = {
        'users': _generate_test_users,
        'meals': _generate_test_meals,
        'recipes': _generate_test_recipes,
        'subscriptions': _generate_test_subscriptions
    }
    
    generator = generators.get(data_type)
    if not generator:
        raise ValueError(f"Unknown data type: {data_type}")
    
    return [generator() for _ in range(count)]


def _generate_test_users() -> Dict[str, Any]:
    """Generate test user data"""
    import random
    
    return {
        'name': f"Test User {random.randint(1000, 9999)}",
        'email': f"test{random.randint(1000, 9999)}@example.com",
        'phone': f"+1555{random.randint(1000, 9999)}",
        'dietary_preferences': random.choice([
            ['vegetarian'], ['vegan'], ['keto'], ['paleo'], []
        ]),
        'health_goals': random.choice([
            ['weight_loss'], ['muscle_gain'], ['maintenance'], ['general_health']
        ])
    }


def _generate_test_meals() -> Dict[str, Any]:
    """Generate test meal data"""
    import random
    
    return {
        'name': f"Test Meal {random.randint(1000, 9999)}",
        'calories': random.randint(300, 800),
        'protein': random.randint(10, 40),
        'carbs': random.randint(20, 80),
        'fat': random.randint(5, 30),
        'meal_type': random.choice(['breakfast', 'lunch', 'dinner', 'snack'])
    }


def _generate_test_recipes() -> Dict[str, Any]:
    """Generate test recipe data"""
    import random
    
    return {
        'name': f"Test Recipe {random.randint(1000, 9999)}",
        'ingredients': ['ingredient1', 'ingredient2', 'ingredient3'],
        'instructions': ['step1', 'step2', 'step3'],
        'prep_time': random.randint(10, 60),
        'cook_time': random.randint(10, 120),
        'servings': random.randint(1, 6)
    }


def _generate_test_subscriptions() -> Dict[str, Any]:
    """Generate test subscription data"""
    import random
    
    return {
        'tier': random.choice(['free', 'premium', 'enterprise']),
        'status': random.choice(['active', 'cancelled', 'pending']),
        'start_date': datetime.utcnow().isoformat(),
        'end_date': (datetime.utcnow() + timedelta(days=30)).isoformat()
    }
