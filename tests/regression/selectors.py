"""
Test Selection Framework
Intelligent test selection based on code changes and test history
"""

from typing import List, Set, Dict, Optional, Tuple
from pathlib import Path
import ast
import subprocess
import json
import time
from dataclasses import dataclass
from collections import defaultdict

from .config import TestSuiteConfig, TestPriority, TestCategory


@dataclass
class TestFile:
    """Represents a test file with metadata"""
    path: Path
    category: TestCategory
    priority: TestPriority
    last_run: Optional[float] = None
    success_rate: float = 1.0
    avg_duration: float = 0.0
    dependencies: Set[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = set()


@dataclass  
class TestSelection:
    """Result of test selection process"""
    selected_tests: List[TestFile]
    reason: str
    confidence: float
    estimated_duration: float


class TestSelector:
    """Intelligent test selection based on changes and history"""
    
    def __init__(self, project_root: Path, test_history_file: Optional[Path] = None):
        self.project_root = project_root
        self.test_history_file = test_history_file or project_root / ".test_history.json"
        self.test_history = self._load_test_history()
        self.dependency_graph = {}
        
    def _load_test_history(self) -> Dict:
        """Load test execution history"""
        if self.test_history_file.exists():
            try:
                with open(self.test_history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def save_test_history(self):
        """Save test execution history"""
        try:
            with open(self.test_history_file, 'w') as f:
                json.dump(self.test_history, f, indent=2)
        except IOError:
            pass  # Fail silently if can't save
    
    def get_changed_files(self, base_branch: str = "main") -> Set[Path]:
        """Get files changed since base branch"""
        try:
            result = subprocess.run([
                "git", "diff", "--name-only", f"{base_branch}...HEAD"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                changed_files = set()
                for line in result.stdout.strip().split('\n'):
                    if line:
                        changed_files.add(Path(line))
                return changed_files
            else:
                # Fallback to staged files
                result = subprocess.run([
                    "git", "diff", "--cached", "--name-only"
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    changed_files = set()
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            changed_files.add(Path(line))
                    return changed_files
                    
        except subprocess.SubprocessError:
            pass
        
        return set()
    
    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build dependency graph of source files to test files"""
        dependency_graph = defaultdict(set)
        
        # Scan all Python files for imports
        for py_file in self.project_root.glob("**/*.py"):
            if py_file.is_file() and not str(py_file).startswith(str(self.project_root / ".git")):
                try:
                    dependencies = self._extract_dependencies(py_file)
                    relative_path = str(py_file.relative_to(self.project_root))
                    dependency_graph[relative_path] = dependencies
                except Exception:
                    # Skip files that can't be parsed
                    continue
        
        self.dependency_graph = dict(dependency_graph)
        return self.dependency_graph
    
    def _extract_dependencies(self, file_path: Path) -> Set[str]:
        """Extract dependencies from a Python file"""
        dependencies = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.add(node.module.split('.')[0])
                        
        except (SyntaxError, UnicodeDecodeError, OSError):
            pass
        
        return dependencies
    
    def find_affected_tests(self, changed_files: Set[Path]) -> Set[Path]:
        """Find tests affected by changed files"""
        affected_tests = set()
        
        # Direct test file changes
        for file_path in changed_files:
            if self._is_test_file(file_path):
                affected_tests.add(file_path)
        
        # Tests affected by source changes
        if not self.dependency_graph:
            self.build_dependency_graph()
        
        for changed_file in changed_files:
            if not self._is_test_file(changed_file):
                # Find tests that might be affected
                affected_tests.update(self._find_tests_for_source_file(changed_file))
        
        return affected_tests
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test file"""
        return (
            file_path.suffix == '.py' and 
            ('test' in file_path.parts or 
             file_path.name.startswith('test_') or
             file_path.name.endswith('_test.py'))
        )
    
    def _find_tests_for_source_file(self, source_file: Path) -> Set[Path]:
        """Find tests that should run for a changed source file"""
        tests = set()
        
        # Direct naming convention mapping
        source_name = source_file.stem
        test_patterns = [
            f"test_{source_name}.py",
            f"{source_name}_test.py", 
            f"test_{source_name}_*.py"
        ]
        
        for pattern in test_patterns:
            tests.update(self.project_root.glob(f"**/tests/**/{pattern}"))
            tests.update(self.project_root.glob(f"**/{pattern}"))
        
        # Module/package based mapping
        if source_file.parts:
            # If source is in src/services/ai.py, look for tests/unit/test_ai_service.py
            parts = list(source_file.parts)
            if 'src' in parts:
                src_index = parts.index('src')
                module_parts = parts[src_index + 1:]
                
                # Try various test naming patterns
                for i in range(len(module_parts)):
                    module_path = '/'.join(module_parts[:i+1])
                    module_name = module_parts[i].replace('.py', '')
                    
                    test_patterns = [
                        f"tests/**/test_{module_name}.py",
                        f"tests/**/test_{module_name}_*.py",
                        f"tests/**/*{module_name}*.py"
                    ]
                    
                    for pattern in test_patterns:
                        tests.update(self.project_root.glob(pattern))
        
        return tests
    
    def select_tests_for_commit(self, max_duration: int = 300) -> TestSelection:
        """Select tests for pre-commit (fast, high-confidence)"""
        changed_files = self.get_changed_files()
        
        if not changed_files:
            # No changes, run critical tests only
            critical_tests = self._get_tests_by_priority(TestPriority.CRITICAL)
            return TestSelection(
                selected_tests=critical_tests[:5],  # Limit to 5 fastest critical tests
                reason="No changes detected, running critical tests",
                confidence=0.9,
                estimated_duration=min(max_duration, sum(t.avg_duration for t in critical_tests[:5]))
            )
        
        # Find affected tests
        affected_tests = self.find_affected_tests(changed_files)
        test_files = []
        
        for test_path in affected_tests:
            test_file = self._get_test_file_info(test_path)
            if test_file and test_file.avg_duration <= max_duration / 4:  # Keep individual tests short
                test_files.append(test_file)
        
        # Sort by priority and duration
        test_files.sort(key=lambda t: (t.priority.value, t.avg_duration))
        
        # Select tests that fit in time budget
        selected = []
        total_duration = 0
        
        for test in test_files:
            if total_duration + test.avg_duration <= max_duration:
                selected.append(test)
                total_duration += test.avg_duration
        
        return TestSelection(
            selected_tests=selected,
            reason=f"Selected {len(selected)} tests affected by {len(changed_files)} changed files",
            confidence=0.85,
            estimated_duration=total_duration
        )
    
    def select_tests_for_pr(self, max_duration: int = 1800) -> TestSelection:
        """Select comprehensive tests for pull request validation"""
        changed_files = self.get_changed_files()
        affected_tests = self.find_affected_tests(changed_files)
        
        # Include affected tests + priority tests
        test_files = []
        
        # Add affected tests
        for test_path in affected_tests:
            test_file = self._get_test_file_info(test_path)
            if test_file:
                test_files.append(test_file)
        
        # Add critical and high priority tests
        priority_tests = (
            self._get_tests_by_priority(TestPriority.CRITICAL) +
            self._get_tests_by_priority(TestPriority.HIGH)
        )
        
        for test in priority_tests:
            if test not in test_files:
                test_files.append(test)
        
        # Sort by priority, success rate, and duration
        test_files.sort(key=lambda t: (
            t.priority.value,
            -t.success_rate,  # Prefer reliable tests
            t.avg_duration
        ))
        
        # Select tests within time budget
        selected = []
        total_duration = 0
        
        for test in test_files:
            if total_duration + test.avg_duration <= max_duration:
                selected.append(test)
                total_duration += test.avg_duration
        
        return TestSelection(
            selected_tests=selected,
            reason=f"PR validation: {len(selected)} tests (affected + priority)",
            confidence=0.95,
            estimated_duration=total_duration
        )
    
    def select_tests_for_nightly(self) -> TestSelection:
        """Select comprehensive tests for nightly regression"""
        # Run all tests except flaky ones
        all_tests = self._get_all_tests()
        
        # Filter out flaky tests (success rate < 80%)
        stable_tests = [t for t in all_tests if t.success_rate >= 0.8]
        
        total_duration = sum(t.avg_duration for t in stable_tests)
        
        return TestSelection(
            selected_tests=stable_tests,
            reason=f"Nightly regression: {len(stable_tests)} stable tests",
            confidence=0.98,
            estimated_duration=total_duration
        )
    
    def select_flaky_tests(self) -> TestSelection:
        """Select tests that are potentially flaky for analysis"""
        all_tests = self._get_all_tests()
        
        # Tests with low success rate or high variance
        flaky_tests = [
            t for t in all_tests 
            if t.success_rate < 0.9 and self._get_test_run_count(t) >= 5
        ]
        
        # Sort by flakiness (lowest success rate first)
        flaky_tests.sort(key=lambda t: t.success_rate)
        
        return TestSelection(
            selected_tests=flaky_tests,
            reason=f"Flaky test analysis: {len(flaky_tests)} potentially flaky tests",
            confidence=0.7,
            estimated_duration=sum(t.avg_duration for t in flaky_tests)
        )
    
    def _get_test_file_info(self, test_path: Path) -> Optional[TestFile]:
        """Get metadata for a test file"""
        if not test_path.exists():
            return None
        
        relative_path = str(test_path.relative_to(self.project_root))
        history = self.test_history.get(relative_path, {})
        
        # Determine category from path
        category = TestCategory.UNIT
        if 'integration' in test_path.parts:
            category = TestCategory.INTEGRATION
        elif 'e2e' in test_path.parts:
            category = TestCategory.E2E
        elif 'performance' in test_path.parts:
            category = TestCategory.PERFORMANCE
        elif 'security' in test_path.parts:
            category = TestCategory.SECURITY
        elif 'api' in test_path.parts:
            category = TestCategory.API
        
        # Determine priority from markers or naming
        priority = TestPriority.MEDIUM
        if 'critical' in test_path.name or 'core' in test_path.name:
            priority = TestPriority.CRITICAL
        elif 'important' in test_path.name or category == TestCategory.INTEGRATION:
            priority = TestPriority.HIGH
        elif 'optional' in test_path.name or category == TestCategory.PERFORMANCE:
            priority = TestPriority.LOW
        
        return TestFile(
            path=test_path,
            category=category,
            priority=priority,
            last_run=history.get('last_run'),
            success_rate=history.get('success_rate', 1.0),
            avg_duration=history.get('avg_duration', 30.0),  # Default 30s
            dependencies=set(history.get('dependencies', []))
        )
    
    def _get_tests_by_priority(self, priority: TestPriority) -> List[TestFile]:
        """Get all tests of a specific priority"""
        tests = []
        for test_path in self.project_root.glob("**/test_*.py"):
            test_file = self._get_test_file_info(test_path)
            if test_file and test_file.priority == priority:
                tests.append(test_file)
        return tests
    
    def _get_all_tests(self) -> List[TestFile]:
        """Get all test files"""
        tests = []
        for test_path in self.project_root.glob("**/test_*.py"):
            test_file = self._get_test_file_info(test_path)
            if test_file:
                tests.append(test_file)
        return tests
    
    def _get_test_run_count(self, test_file: TestFile) -> int:
        """Get number of times a test has been run"""
        relative_path = str(test_file.path.relative_to(self.project_root))
        history = self.test_history.get(relative_path, {})
        return history.get('run_count', 0)
    
    def update_test_result(self, test_path: Path, success: bool, duration: float):
        """Update test execution history"""
        relative_path = str(test_path.relative_to(self.project_root))
        
        if relative_path not in self.test_history:
            self.test_history[relative_path] = {
                'run_count': 0,
                'success_count': 0,
                'total_duration': 0.0,
                'last_run': None,
                'success_rate': 1.0,
                'avg_duration': 0.0
            }
        
        history = self.test_history[relative_path]
        history['run_count'] += 1
        history['total_duration'] += duration
        history['last_run'] = time.time()
        
        if success:
            history['success_count'] += 1
        
        history['success_rate'] = history['success_count'] / history['run_count']
        history['avg_duration'] = history['total_duration'] / history['run_count']
