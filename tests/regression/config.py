"""
Regression Test Configuration
Centralized configuration for regression testing framework
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set
from pathlib import Path
import os


class TestPriority(Enum):
    """Test priority levels for regression testing"""
    CRITICAL = "critical"    # Core functionality - must pass
    HIGH = "high"           # Important features - should pass  
    MEDIUM = "medium"       # Standard features - nice to pass
    LOW = "low"            # Edge cases - optional


class TestCategory(Enum):
    """Test categories for organization"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    API = "api"
    UI = "ui"


class TestTrigger(Enum):
    """When regression tests should run"""
    PRE_COMMIT = "pre_commit"
    PULL_REQUEST = "pull_request"
    NIGHTLY = "nightly"
    RELEASE = "release"
    MANUAL = "manual"


@dataclass
class TestSuiteConfig:
    """Configuration for a test suite"""
    name: str
    category: TestCategory
    priority: TestPriority
    path: Path
    patterns: List[str] = field(default_factory=list)
    markers: List[str] = field(default_factory=list)
    timeout: int = 300  # seconds
    retry_count: int = 0
    dependencies: List[str] = field(default_factory=list)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    setup_commands: List[str] = field(default_factory=list)
    teardown_commands: List[str] = field(default_factory=list)


@dataclass
class ParallelConfig:
    """Configuration for parallel test execution"""
    max_workers: int = 4
    worker_timeout: int = 600
    chunk_size: int = 10
    enable_xdist: bool = True
    distribute_by: str = "worksteal"  # worksteal, load, loadscope


@dataclass
class FlakeDetectionConfig:
    """Configuration for flaky test detection"""
    enabled: bool = True
    min_runs: int = 5
    max_runs: int = 20
    failure_threshold: float = 0.2  # 20% failure rate = flaky
    quarantine_flaky: bool = True
    report_flaky: bool = True


@dataclass
class ReportingConfig:
    """Configuration for test reporting"""
    formats: List[str] = field(default_factory=lambda: ["json", "html", "junit"])
    output_dir: Path = field(default_factory=lambda: Path("test-reports"))
    include_coverage: bool = True
    coverage_threshold: float = 80.0
    include_performance: bool = True
    include_trends: bool = True


@dataclass
class RegressionTestConfig:
    """Main configuration for regression testing framework"""
    
    # Basic settings
    project_root: Path = field(default_factory=lambda: Path.cwd())
    test_root: Path = field(default_factory=lambda: Path("tests"))
    src_root: Path = field(default_factory=lambda: Path("src"))
    
    # Test suites configuration
    test_suites: List[TestSuiteConfig] = field(default_factory=list)
    
    # Execution configuration
    parallel: ParallelConfig = field(default_factory=ParallelConfig)
    flake_detection: FlakeDetectionConfig = field(default_factory=FlakeDetectionConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    
    # Environment
    python_executable: str = "python"
    pytest_executable: str = "pytest"
    virtual_env: Optional[str] = None
    
    # CI/CD Integration
    ci_mode: bool = False
    artifact_retention_days: int = 30
    
    # Notification settings
    slack_webhook: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize default test suites if none provided"""
        if not self.test_suites:
            self._setup_default_suites()
    
    def _setup_default_suites(self):
        """Setup default test suite configurations"""
        
        # Critical path tests
        self.test_suites.append(TestSuiteConfig(
            name="critical_path",
            category=TestCategory.INTEGRATION,
            priority=TestPriority.CRITICAL,
            path=self.test_root / "critical",
            patterns=["test_*critical*.py", "test_*core*.py"],
            markers=["critical"],
            timeout=600,
            retry_count=2
        ))
        
        # Unit tests
        self.test_suites.append(TestSuiteConfig(
            name="unit_tests",
            category=TestCategory.UNIT,
            priority=TestPriority.HIGH,
            path=self.test_root / "unit",
            patterns=["test_*.py"],
            markers=["unit"],
            timeout=300
        ))
        
        # Integration tests
        self.test_suites.append(TestSuiteConfig(
            name="integration_tests",
            category=TestCategory.INTEGRATION,
            priority=TestPriority.HIGH,
            path=self.test_root / "integration",
            patterns=["test_*.py"],
            markers=["integration"],
            timeout=900,
            environment_vars={
                "TEST_MODE": "integration",
                "AWS_DEFAULT_REGION": "us-east-1"
            }
        ))
        
        # API tests  
        self.test_suites.append(TestSuiteConfig(
            name="api_tests",
            category=TestCategory.API,
            priority=TestPriority.HIGH,
            path=self.test_root / "api",
            patterns=["test_*api*.py"],
            markers=["api"],
            timeout=450
        ))
        
        # Performance tests
        self.test_suites.append(TestSuiteConfig(
            name="performance_tests",
            category=TestCategory.PERFORMANCE,
            priority=TestPriority.MEDIUM,
            path=self.test_root / "performance",
            patterns=["test_*performance*.py", "test_*perf*.py"],
            markers=["performance", "slow"],
            timeout=1800  # 30 minutes
        ))
        
        # Security tests
        self.test_suites.append(TestSuiteConfig(
            name="security_tests",
            category=TestCategory.SECURITY,
            priority=TestPriority.HIGH,
            path=self.test_root / "security",
            patterns=["test_*security*.py", "test_*auth*.py"],
            markers=["security"],
            timeout=600
        ))
        
        # E2E tests
        self.test_suites.append(TestSuiteConfig(
            name="e2e_tests",
            category=TestCategory.E2E,
            priority=TestPriority.MEDIUM,
            path=self.test_root / "e2e",
            patterns=["test_*.py"],
            markers=["e2e"],
            timeout=1200,
            retry_count=1
        ))
    
    def get_suites_by_priority(self, priority: TestPriority) -> List[TestSuiteConfig]:
        """Get test suites by priority level"""
        return [suite for suite in self.test_suites if suite.priority == priority]
    
    def get_suites_by_category(self, category: TestCategory) -> List[TestSuiteConfig]:
        """Get test suites by category"""
        return [suite for suite in self.test_suites if suite.category == category]
    
    def get_suites_for_trigger(self, trigger: TestTrigger) -> List[TestSuiteConfig]:
        """Get test suites that should run for a specific trigger"""
        trigger_map = {
            TestTrigger.PRE_COMMIT: [TestPriority.CRITICAL],
            TestTrigger.PULL_REQUEST: [TestPriority.CRITICAL, TestPriority.HIGH],
            TestTrigger.NIGHTLY: [TestPriority.CRITICAL, TestPriority.HIGH, TestPriority.MEDIUM],
            TestTrigger.RELEASE: [TestPriority.CRITICAL, TestPriority.HIGH, TestPriority.MEDIUM, TestPriority.LOW],
            TestTrigger.MANUAL: [TestPriority.CRITICAL, TestPriority.HIGH, TestPriority.MEDIUM, TestPriority.LOW]
        }
        
        priorities = trigger_map.get(trigger, [])
        suites = []
        for priority in priorities:
            suites.extend(self.get_suites_by_priority(priority))
        return suites
    
    @classmethod
    def from_environment(cls) -> 'RegressionTestConfig':
        """Create configuration from environment variables"""
        config = cls()
        
        # Override from environment
        if os.getenv('REGRESSION_MAX_WORKERS'):
            config.parallel.max_workers = int(os.getenv('REGRESSION_MAX_WORKERS'))
        
        if os.getenv('REGRESSION_CI_MODE'):
            config.ci_mode = os.getenv('REGRESSION_CI_MODE').lower() == 'true'
        
        if os.getenv('REGRESSION_PYTHON_EXECUTABLE'):
            config.python_executable = os.getenv('REGRESSION_PYTHON_EXECUTABLE')
        
        if os.getenv('VIRTUAL_ENV'):
            config.virtual_env = os.getenv('VIRTUAL_ENV')
            
        if os.getenv('SLACK_WEBHOOK_URL'):
            config.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        
        return config
    
    def validate(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        if not self.project_root.exists():
            errors.append(f"Project root does not exist: {self.project_root}")
        
        if not (self.project_root / self.test_root).exists():
            errors.append(f"Test root does not exist: {self.test_root}")
        
        if not (self.project_root / self.src_root).exists():
            errors.append(f"Source root does not exist: {self.src_root}")
        
        if self.parallel.max_workers < 1:
            errors.append("max_workers must be at least 1")
        
        if not 0 <= self.flake_detection.failure_threshold <= 1:
            errors.append("failure_threshold must be between 0 and 1")
        
        if not 0 <= self.reporting.coverage_threshold <= 100:
            errors.append("coverage_threshold must be between 0 and 100")
        
        return errors


# Default configuration instance
DEFAULT_CONFIG = RegressionTestConfig()
