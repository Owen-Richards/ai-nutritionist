"""
Test Maintenance and Analytics
Tools for maintaining test health and analyzing test metrics
"""

import json
import sqlite3
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import ast
import re

from .config import RegressionTestConfig
from .selectors import TestFile
from .runners import TestResult, TestStatus


@dataclass
class TestMetrics:
    """Comprehensive test metrics"""
    test_path: str
    total_runs: int
    success_count: int
    failure_count: int
    avg_duration: float
    min_duration: float
    max_duration: float
    success_rate: float
    stability_score: float  # 0-1, based on variance in results
    last_run: datetime
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    flakiness_score: float  # 0-1, higher = more flaky
    maintenance_priority: str  # high, medium, low
    tags: Set[str]


@dataclass
class RefactoringRecommendation:
    """Test refactoring recommendation"""
    test_path: str
    issue_type: str
    severity: str  # high, medium, low
    description: str
    recommended_action: str
    effort_estimate: str  # small, medium, large


@dataclass
class TestDataManagement:
    """Test data management tracking"""
    fixture_files: List[str]
    mock_objects: List[str]
    test_databases: List[str]
    external_dependencies: List[str]
    cleanup_needed: List[str]


class TestAnalytics:
    """Advanced test analytics and insights"""
    
    def __init__(self, config: RegressionTestConfig):
        self.config = config
        self.db_path = config.project_root / ".test_analytics.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for test analytics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    worker_id TEXT,
                    error_message TEXT,
                    output_size INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_metrics_cache (
                    test_path TEXT PRIMARY KEY,
                    metrics_json TEXT NOT NULL,
                    last_updated DATETIME NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS refactoring_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_path TEXT NOT NULL,
                    refactoring_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    before_metrics TEXT,
                    after_metrics TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_runs_path ON test_runs(test_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_runs_timestamp ON test_runs(timestamp)")
    
    def record_test_result(self, result: TestResult):
        """Record test result for analytics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO test_runs (test_path, status, duration, timestamp, worker_id, error_message, output_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.test_file,
                result.status.value,
                result.duration,
                datetime.now().isoformat(),
                result.worker_id,
                result.error[:1000] if result.error else None,  # Limit error message size
                len(result.output) if result.output else 0
            ))
    
    def calculate_test_metrics(self, test_path: str, days: int = 30) -> Optional[TestMetrics]:
        """Calculate comprehensive metrics for a test"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, duration, timestamp, error_message
                FROM test_runs 
                WHERE test_path = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (test_path, cutoff_date.isoformat()))
            
            rows = cursor.fetchall()
        
        if not rows:
            return None
        
        # Calculate basic metrics
        total_runs = len(rows)
        success_count = sum(1 for row in rows if row[0] == 'passed')
        failure_count = total_runs - success_count
        
        durations = [row[1] for row in rows]
        avg_duration = statistics.mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        success_rate = success_count / total_runs if total_runs > 0 else 0.0
        
        # Calculate stability score (lower variance = more stable)
        if len(durations) > 1:
            duration_stdev = statistics.stdev(durations)
            stability_score = max(0, 1 - (duration_stdev / avg_duration))
        else:
            stability_score = 1.0
        
        # Calculate flakiness score
        flakiness_score = self._calculate_flakiness_score(rows)
        
        # Determine maintenance priority
        maintenance_priority = self._determine_maintenance_priority(
            success_rate, flakiness_score, avg_duration, total_runs
        )
        
        # Extract tags from test file
        tags = self._extract_test_tags(test_path)
        
        # Get timestamps
        timestamps = [datetime.fromisoformat(row[2]) for row in rows]
        last_run = max(timestamps)
        
        success_timestamps = [
            datetime.fromisoformat(row[2]) for row in rows if row[0] == 'passed'
        ]
        last_success = max(success_timestamps) if success_timestamps else None
        
        failure_timestamps = [
            datetime.fromisoformat(row[2]) for row in rows if row[0] != 'passed'
        ]
        last_failure = max(failure_timestamps) if failure_timestamps else None
        
        return TestMetrics(
            test_path=test_path,
            total_runs=total_runs,
            success_count=success_count,
            failure_count=failure_count,
            avg_duration=avg_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            success_rate=success_rate,
            stability_score=stability_score,
            last_run=last_run,
            last_success=last_success,
            last_failure=last_failure,
            flakiness_score=flakiness_score,
            maintenance_priority=maintenance_priority,
            tags=tags
        )
    
    def _calculate_flakiness_score(self, test_runs: List[Tuple]) -> float:
        """Calculate flakiness score based on test run patterns"""
        
        if len(test_runs) < 5:
            return 0.0  # Not enough data
        
        # Look for patterns of pass/fail alternation
        statuses = [row[0] for row in test_runs]
        
        # Count transitions between pass/fail
        transitions = 0
        for i in range(1, len(statuses)):
            if (statuses[i] == 'passed') != (statuses[i-1] == 'passed'):
                transitions += 1
        
        # High transition rate = high flakiness
        max_possible_transitions = len(statuses) - 1
        flakiness_score = transitions / max_possible_transitions if max_possible_transitions > 0 else 0.0
        
        return min(1.0, flakiness_score)
    
    def _determine_maintenance_priority(self, success_rate: float, flakiness_score: float, 
                                      avg_duration: float, total_runs: int) -> str:
        """Determine maintenance priority for a test"""
        
        # High priority conditions
        if success_rate < 0.8 or flakiness_score > 0.3 or avg_duration > 300:
            return "high"
        
        # Medium priority conditions  
        if success_rate < 0.95 or flakiness_score > 0.1 or avg_duration > 120:
            return "medium"
        
        return "low"
    
    def _extract_test_tags(self, test_path: str) -> Set[str]:
        """Extract tags from test file content"""
        tags = set()
        
        try:
            with open(test_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for pytest markers
            marker_matches = re.findall(r'@pytest\.mark\.(\w+)', content)
            tags.update(marker_matches)
            
            # Look for custom tags in docstrings or comments
            tag_matches = re.findall(r'#\s*tags?:\s*([^\n]+)', content, re.IGNORECASE)
            for match in tag_matches:
                tags.update(tag.strip() for tag in match.split(','))
            
            # Infer tags from file path
            path_parts = Path(test_path).parts
            if 'integration' in path_parts:
                tags.add('integration')
            if 'unit' in path_parts:
                tags.add('unit')
            if 'performance' in path_parts:
                tags.add('performance')
            if 'security' in path_parts:
                tags.add('security')
                
        except (IOError, UnicodeDecodeError):
            pass
        
        return tags
    
    def get_top_flaky_tests(self, limit: int = 10) -> List[TestMetrics]:
        """Get the most flaky tests"""
        
        # Get all unique test paths
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT DISTINCT test_path FROM test_runs")
            test_paths = [row[0] for row in cursor.fetchall()]
        
        # Calculate metrics for each test
        test_metrics = []
        for test_path in test_paths:
            metrics = self.calculate_test_metrics(test_path)
            if metrics and metrics.flakiness_score > 0:
                test_metrics.append(metrics)
        
        # Sort by flakiness score
        test_metrics.sort(key=lambda m: m.flakiness_score, reverse=True)
        
        return test_metrics[:limit]
    
    def get_slowest_tests(self, limit: int = 10) -> List[TestMetrics]:
        """Get the slowest tests"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT DISTINCT test_path FROM test_runs")
            test_paths = [row[0] for row in cursor.fetchall()]
        
        test_metrics = []
        for test_path in test_paths:
            metrics = self.calculate_test_metrics(test_path)
            if metrics:
                test_metrics.append(metrics)
        
        test_metrics.sort(key=lambda m: m.avg_duration, reverse=True)
        
        return test_metrics[:limit]
    
    def get_maintenance_recommendations(self) -> List[RefactoringRecommendation]:
        """Get test maintenance recommendations"""
        
        recommendations = []
        
        # Get high-priority tests
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT DISTINCT test_path FROM test_runs")
            test_paths = [row[0] for row in cursor.fetchall()]
        
        for test_path in test_paths:
            metrics = self.calculate_test_metrics(test_path)
            if not metrics:
                continue
            
            # Check for various issues
            if metrics.success_rate < 0.8:
                recommendations.append(RefactoringRecommendation(
                    test_path=test_path,
                    issue_type="low_success_rate",
                    severity="high",
                    description=f"Test has low success rate of {metrics.success_rate:.1%}",
                    recommended_action="Review test logic and fix flaky assertions",
                    effort_estimate="medium"
                ))
            
            if metrics.flakiness_score > 0.3:
                recommendations.append(RefactoringRecommendation(
                    test_path=test_path,
                    issue_type="flaky_test",
                    severity="high",
                    description=f"Test is flaky with score {metrics.flakiness_score:.2f}",
                    recommended_action="Add proper wait conditions and stabilize test",
                    effort_estimate="large"
                ))
            
            if metrics.avg_duration > 300:
                recommendations.append(RefactoringRecommendation(
                    test_path=test_path,
                    issue_type="slow_test",
                    severity="medium",
                    description=f"Test is slow with average duration {metrics.avg_duration:.1f}s",
                    recommended_action="Optimize test or move to nightly suite",
                    effort_estimate="medium"
                ))
            
            if metrics.total_runs < 5:
                recommendations.append(RefactoringRecommendation(
                    test_path=test_path,
                    issue_type="rarely_run",
                    severity="low",
                    description=f"Test has only been run {metrics.total_runs} times",
                    recommended_action="Verify test is being selected properly",
                    effort_estimate="small"
                ))
        
        return recommendations


class TestRefactoring:
    """Test refactoring and maintenance tools"""
    
    def __init__(self, config: RegressionTestConfig):
        self.config = config
        self.analytics = TestAnalytics(config)
    
    def identify_duplicate_tests(self) -> Dict[str, List[str]]:
        """Identify potentially duplicate test cases"""
        
        test_signatures = defaultdict(list)
        
        for test_file in self.config.project_root.glob("**/test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        # Create signature based on function content
                        signature = self._create_function_signature(node)
                        test_signatures[signature].append(str(test_file))
                        
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
        
        # Return groups with more than one test
        duplicates = {sig: tests for sig, tests in test_signatures.items() if len(tests) > 1}
        
        return duplicates
    
    def _create_function_signature(self, func_node: ast.FunctionDef) -> str:
        """Create a signature for function comparison"""
        
        # Extract key elements that indicate similar tests
        elements = []
        
        # Function name (normalized)
        normalized_name = re.sub(r'test_\d+', 'test_N', func_node.name)
        elements.append(normalized_name)
        
        # Count different types of AST nodes
        node_counts = Counter()
        for node in ast.walk(func_node):
            node_counts[type(node).__name__] += 1
        
        elements.append(str(sorted(node_counts.items())))
        
        return "|".join(elements)
    
    def suggest_test_organization(self) -> Dict[str, List[str]]:
        """Suggest better test organization"""
        
        suggestions = {
            "move_to_integration": [],
            "move_to_unit": [],
            "create_new_suite": [],
            "consolidate_files": []
        }
        
        for test_file in self.config.project_root.glob("**/test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Analyze test characteristics
                has_external_deps = any(
                    pattern in content.lower() 
                    for pattern in ['requests.', 'http', 'api', 'database', 'redis', 'aws']
                )
                
                has_mock_usage = 'mock' in content.lower() or '@patch' in content
                
                is_in_unit_dir = 'unit' in test_file.parts
                is_in_integration_dir = 'integration' in test_file.parts
                
                # Suggest moves based on characteristics
                if has_external_deps and is_in_unit_dir:
                    suggestions["move_to_integration"].append(str(test_file))
                
                elif not has_external_deps and has_mock_usage and is_in_integration_dir:
                    suggestions["move_to_unit"].append(str(test_file))
                
                # Check if file is too large (suggests need for splitting)
                if len(content.split('\n')) > 500:
                    suggestions["create_new_suite"].append(str(test_file))
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        return suggestions
    
    def analyze_test_coverage_gaps(self) -> Dict[str, Any]:
        """Analyze test coverage gaps"""
        
        coverage_analysis = {
            "untested_modules": [],
            "low_coverage_modules": [],
            "missing_edge_cases": [],
            "recommended_tests": []
        }
        
        # Find source files without corresponding tests
        src_files = list(self.config.project_root.glob("src/**/*.py"))
        test_files = list(self.config.project_root.glob("**/test_*.py"))
        
        tested_modules = set()
        for test_file in test_files:
            # Extract module being tested from test file name and imports
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for imports from src
                import_matches = re.findall(r'from\s+src\.([^\s]+)', content)
                tested_modules.update(import_matches)
                
            except (UnicodeDecodeError, OSError):
                continue
        
        # Find untested modules
        for src_file in src_files:
            relative_path = src_file.relative_to(self.config.project_root / "src")
            module_path = str(relative_path).replace('/', '.').replace('.py', '')
            
            if not any(module_path.startswith(tested) for tested in tested_modules):
                coverage_analysis["untested_modules"].append(str(src_file))
        
        return coverage_analysis


class TestDataManager:
    """Manage test data and fixtures"""
    
    def __init__(self, config: RegressionTestConfig):
        self.config = config
        self.fixtures_dir = config.project_root / "tests" / "fixtures"
    
    def audit_test_data(self) -> TestDataManagement:
        """Audit test data usage and identify cleanup needs"""
        
        fixture_files = list(self.fixtures_dir.glob("**/*.py")) if self.fixtures_dir.exists() else []
        mock_objects = []
        test_databases = []
        external_dependencies = []
        cleanup_needed = []
        
        # Scan test files for data usage patterns
        for test_file in self.config.project_root.glob("**/test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find mock usage
                if '@patch' in content or 'Mock(' in content:
                    mock_objects.append(str(test_file))
                
                # Find database usage
                if any(db_pattern in content.lower() for db_pattern in ['sqlite', 'postgres', 'mysql', 'redis']):
                    test_databases.append(str(test_file))
                
                # Find external dependencies
                if any(ext_pattern in content.lower() for ext_pattern in ['requests.', 'http', 'api']):
                    external_dependencies.append(str(test_file))
                
                # Find potential cleanup issues
                if 'setup' in content.lower() and 'teardown' not in content.lower():
                    cleanup_needed.append(str(test_file))
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        return TestDataManagement(
            fixture_files=[str(f) for f in fixture_files],
            mock_objects=mock_objects,
            test_databases=test_databases,
            external_dependencies=external_dependencies,
            cleanup_needed=cleanup_needed
        )
    
    def generate_fixture_recommendations(self) -> List[str]:
        """Generate recommendations for fixture improvements"""
        
        recommendations = []
        test_data = self.audit_test_data()
        
        if len(test_data.mock_objects) > 10:
            recommendations.append(
                f"Consider consolidating {len(test_data.mock_objects)} mock objects into reusable fixtures"
            )
        
        if len(test_data.test_databases) > 5:
            recommendations.append(
                f"Consider using database fixtures for {len(test_data.test_databases)} database tests"
            )
        
        if test_data.cleanup_needed:
            recommendations.append(
                f"Add proper teardown for {len(test_data.cleanup_needed)} tests with setup methods"
            )
        
        if not self.fixtures_dir.exists():
            recommendations.append("Create tests/fixtures directory to organize test data")
        
        return recommendations
    
    def cleanup_unused_fixtures(self) -> List[str]:
        """Identify and suggest cleanup of unused fixtures"""
        
        if not self.fixtures_dir.exists():
            return []
        
        # Find all fixture definitions
        fixture_definitions = set()
        for fixture_file in self.fixtures_dir.glob("**/*.py"):
            try:
                with open(fixture_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find @pytest.fixture definitions
                fixture_matches = re.findall(r'@pytest\.fixture[^\n]*\ndef\s+(\w+)', content)
                fixture_definitions.update(fixture_matches)
                
            except (UnicodeDecodeError, OSError):
                continue
        
        # Find fixture usage in test files
        used_fixtures = set()
        for test_file in self.config.project_root.glob("**/test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find fixture usage in function parameters
                for fixture in fixture_definitions:
                    if f"def test_.*{fixture}" in content or f", {fixture}" in content:
                        used_fixtures.add(fixture)
                        
            except (UnicodeDecodeError, OSError):
                continue
        
        unused_fixtures = fixture_definitions - used_fixtures
        
        return list(unused_fixtures)
