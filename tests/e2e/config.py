"""
E2E Test Configuration

Centralized configuration for E2E testing including
environment settings, test parameters, and browser configurations.
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class E2EConfig:
    """E2E test configuration settings"""
    environment: str = "local"
    base_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    timeout: int = 30
    headless: bool = True
    browser: str = "chrome"
    parallel_execution: bool = False
    screenshot_on_failure: bool = True
    video_recording: bool = False
    report_format: str = "html"
    
    # Performance test settings
    load_test_users: int = 100
    stress_test_max_users: int = 1000
    endurance_test_hours: int = 2
    
    # Database settings
    cleanup_test_data: bool = True
    preserve_on_failure: bool = True


class E2ETestConfig:
    """Configuration manager for E2E tests"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment and defaults"""
        env = os.getenv('E2E_ENVIRONMENT', 'local')
        
        configs = {
            'local': {
                'environment': 'local',
                'web_app_url': 'http://localhost:3000',
                'api_base_url': 'http://localhost:8000',
                'database': {
                    'type': 'dynamodb_local',
                    'endpoint': 'http://localhost:8000'
                },
                'messaging': {
                    'mock_webhooks': True,
                    'simulate_delays': False
                },
                'ai_services': {
                    'mock_openai': True,
                    'mock_responses': True
                },
                'payment': {
                    'use_test_keys': True,
                    'mock_stripe': True
                }
            },
            'staging': {
                'environment': 'staging',
                'web_app_url': 'https://staging.ai-nutritionist.com',
                'api_base_url': 'https://staging-api.ai-nutritionist.com',
                'database': {
                    'type': 'dynamodb',
                    'region': 'us-east-1'
                },
                'messaging': {
                    'mock_webhooks': False,
                    'use_test_numbers': True
                },
                'ai_services': {
                    'mock_openai': False,
                    'use_test_tokens': True
                },
                'payment': {
                    'use_test_keys': True,
                    'mock_stripe': False
                }
            },
            'production': {
                'environment': 'production',
                'web_app_url': 'https://ai-nutritionist.com',
                'api_base_url': 'https://api.ai-nutritionist.com',
                'database': {
                    'type': 'dynamodb',
                    'region': 'us-east-1'
                },
                'messaging': {
                    'mock_webhooks': False,
                    'use_test_numbers': True  # Always use test numbers in automated tests
                },
                'ai_services': {
                    'mock_openai': False,
                    'use_test_tokens': True
                },
                'payment': {
                    'use_test_keys': True,  # Always use test keys in automated tests
                    'mock_stripe': False
                }
            }
        }
        
        base_config = configs.get(env, configs['local'])
        
        # Override with environment variables
        base_config.update({
            'headless': os.getenv('E2E_HEADLESS', 'true').lower() == 'true',
            'browser': os.getenv('E2E_BROWSER', 'chrome'),
            'parallel': os.getenv('E2E_PARALLEL', 'false').lower() == 'true',
            'timeout': int(os.getenv('E2E_TIMEOUT', '30')),
            'screenshot_on_failure': os.getenv('E2E_SCREENSHOTS', 'true').lower() == 'true',
            'video_recording': os.getenv('E2E_VIDEO', 'false').lower() == 'true'
        })
        
        return base_config
    
    def get_selenium_config(self) -> Dict[str, Any]:
        """Get Selenium-specific configuration"""
        return {
            'browser': self.config['browser'],
            'headless': self.config['headless'],
            'timeout': self.config['timeout'],
            'window_size': (1920, 1080),
            'options': {
                'chrome': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-plugins'
                ],
                'firefox': [
                    '--width=1920',
                    '--height=1080'
                ]
            }
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API testing configuration"""
        return {
            'base_url': self.config['api_base_url'],
            'timeout': self.config['timeout'],
            'retry_attempts': 3,
            'retry_delay': 1,
            'headers': {
                'Content-Type': 'application/json',
                'User-Agent': 'AI-Nutritionist-E2E-Tests/1.0'
            }
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance testing configuration"""
        return {
            'load_test': {
                'users': [10, 50, 100, 200],
                'duration_minutes': [5, 10, 15],
                'ramp_up_seconds': 60
            },
            'stress_test': {
                'max_users': 1000,
                'increment': 100,
                'increment_duration': 300
            },
            'spike_test': {
                'baseline_users': 10,
                'spike_users': 500,
                'spike_duration': 180
            },
            'endurance_test': {
                'duration_hours': 2,
                'users': 100,
                'monitoring_interval': 300
            }
        }
    
    def get_test_data_config(self) -> Dict[str, Any]:
        """Get test data configuration"""
        return {
            'users': {
                'count': 100,
                'cleanup_after_test': True,
                'preserve_on_failure': True
            },
            'meals': {
                'sample_size': 50,
                'include_images': False  # For faster testing
            },
            'recipes': {
                'sample_size': 20,
                'include_nutrition_data': True
            }
        }
    
    def get_reporting_config(self) -> Dict[str, Any]:
        """Get test reporting configuration"""
        return {
            'formats': ['html', 'json'],
            'include_screenshots': True,
            'include_logs': True,
            'include_performance_metrics': True,
            'output_directory': 'tests/e2e/output',
            'archive_results': True
        }


# Test environment-specific configurations
TEST_ENVIRONMENTS = {
    'local': {
        'description': 'Local development environment',
        'requirements': [
            'Local API server running on port 8000',
            'Local web app running on port 3000',
            'Local DynamoDB instance',
            'Mock external services'
        ],
        'setup_commands': [
            'docker-compose up -d dynamodb-local',
            'npm run dev',  # Start web app
            'uvicorn main:app --reload'  # Start API
        ]
    },
    'staging': {
        'description': 'Staging environment for integration testing',
        'requirements': [
            'Staging environment deployed',
            'Test database access',
            'Test messaging credentials',
            'Test payment keys'
        ],
        'setup_commands': []
    },
    'production': {
        'description': 'Production environment (read-only tests only)',
        'requirements': [
            'Production environment access',
            'Read-only test credentials',
            'Test-specific endpoints enabled'
        ],
        'setup_commands': []
    }
}

# Browser configurations for cross-browser testing
BROWSER_CONFIGS = {
    'chrome': {
        'driver': 'chromedriver',
        'options': [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions'
        ],
        'capabilities': {
            'browserName': 'chrome',
            'browserVersion': 'latest'
        }
    },
    'firefox': {
        'driver': 'geckodriver',
        'options': [
            '--width=1920',
            '--height=1080'
        ],
        'capabilities': {
            'browserName': 'firefox',
            'browserVersion': 'latest'
        }
    },
    'safari': {
        'driver': 'safaridriver',
        'options': [],
        'capabilities': {
            'browserName': 'safari',
            'browserVersion': 'latest'
        }
    }
}

# Mobile device configurations
MOBILE_CONFIGS = {
    'iPhone_12': {
        'deviceName': 'iPhone 12',
        'platformName': 'iOS',
        'platformVersion': '15.0',
        'browserName': 'Safari',
        'viewport': {'width': 390, 'height': 844}
    },
    'iPad_Pro': {
        'deviceName': 'iPad Pro',
        'platformName': 'iOS',
        'platformVersion': '15.0',
        'browserName': 'Safari',
        'viewport': {'width': 1024, 'height': 1366}
    },
    'Samsung_Galaxy': {
        'deviceName': 'Samsung Galaxy S21',
        'platformName': 'Android',
        'platformVersion': '11.0',
        'browserName': 'Chrome',
        'viewport': {'width': 360, 'height': 800}
    }
}

# Test data templates
TEST_DATA_TEMPLATES = {
    'user_registration': {
        'name': 'Test User {timestamp}',
        'email': 'test{timestamp}@example.com',
        'phone': '+1555{random:4}',
        'password': 'TestPassword123!',
        'dietary_preferences': ['vegetarian'],
        'health_goals': ['weight_loss']
    },
    'meal_logging': {
        'breakfast': 'Oatmeal with berries and honey',
        'lunch': 'Grilled chicken salad with mixed vegetables',
        'dinner': 'Salmon with quinoa and broccoli',
        'snack': 'Greek yogurt with nuts'
    },
    'family_setup': {
        'spouse': {
            'name': 'Spouse {timestamp}',
            'age': 32,
            'relationship': 'spouse',
            'dietary_preferences': ['vegetarian']
        },
        'child': {
            'name': 'Child {timestamp}',
            'age': 8,
            'relationship': 'child',
            'dietary_preferences': ['kid_friendly']
        }
    }
}

# Performance test scenarios
PERFORMANCE_SCENARIOS = {
    'daily_usage': {
        'description': 'Simulate typical daily usage patterns',
        'operations': [
            {'action': 'log_meal', 'weight': 40},
            {'action': 'view_meal_plan', 'weight': 30},
            {'action': 'search_recipes', 'weight': 20},
            {'action': 'check_progress', 'weight': 10}
        ]
    },
    'meal_planning_peak': {
        'description': 'Simulate meal planning peak hours',
        'operations': [
            {'action': 'generate_meal_plan', 'weight': 50},
            {'action': 'customize_meal_plan', 'weight': 30},
            {'action': 'save_meal_plan', 'weight': 20}
        ]
    },
    'registration_surge': {
        'description': 'Simulate new user registration surge',
        'operations': [
            {'action': 'user_registration', 'weight': 60},
            {'action': 'onboarding_completion', 'weight': 40}
        ]
    }
}

# Expected performance benchmarks
PERFORMANCE_BENCHMARKS = {
    'response_times': {
        'api_endpoints': {
            'p50': 200,  # milliseconds
            'p90': 500,
            'p95': 1000,
            'p99': 2000
        },
        'web_pages': {
            'p50': 1000,  # milliseconds
            'p90': 2000,
            'p95': 3000,
            'p99': 5000
        }
    },
    'throughput': {
        'api_requests_per_second': 100,
        'concurrent_users': 200,
        'meal_plans_per_minute': 50
    },
    'error_rates': {
        'api_errors': 0.01,  # 1%
        'client_errors': 0.005,  # 0.5%
        'timeout_errors': 0.001  # 0.1%
    }
}
