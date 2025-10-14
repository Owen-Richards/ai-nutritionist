"""
E2E Framework Initialization

Exports key classes and utilities for E2E testing.
"""

from .base import (
    BaseE2ETest,
    WebE2ETest,
    APIE2ETest,
    MessagingE2ETest,
    PerformanceE2ETest,
    E2ETestRunner,
    TestUser,
    TestEnvironment,
    TestResult,
    MessageSimulator,
    create_test_environment,
    generate_test_data
)

__all__ = [
    'BaseE2ETest',
    'WebE2ETest', 
    'APIE2ETest',
    'MessagingE2ETest',
    'PerformanceE2ETest',
    'E2ETestRunner',
    'TestUser',
    'TestEnvironment', 
    'TestResult',
    'MessageSimulator',
    'create_test_environment',
    'generate_test_data'
]
