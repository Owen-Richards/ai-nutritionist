"""
Regression Testing Framework
Comprehensive test suite for detecting regressions across all system components
"""

from .config import RegressionTestConfig
from .framework import RegressionTestFramework
from .selectors import TestSelector
from .runners import ParallelTestRunner
from .reporters import RegressionReporter

__all__ = [
    "RegressionTestConfig",
    "RegressionTestFramework", 
    "TestSelector",
    "ParallelTestRunner",
    "RegressionReporter"
]
