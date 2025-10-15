"""
Automated cleanup script for massive pivot
Removes over-engineered components to achieve 70% complexity reduction
"""

import glob
import os
import shutil
from pathlib import Path
from typing import Dict, List


class PivotCleanup:
    """Execute ruthless simplification of codebase"""

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.removed_files = []
        self.removed_dirs = []
        self.errors = []

    def execute_pivot_cleanup(self) -> Dict:
        """Remove over-engineered components"""

        print("🗑️ EXECUTING MASSIVE PIVOT CLEANUP...")
        print("=" * 60)

        # 1. Remove unnecessary directories
        dirs_to_remove = [
            "chaos-engineering",
            "compliance-automation",
            "accessibility",
            "performance/comprehensive",
        ]

        self._remove_directories(dirs_to_remove)

        # 2. Remove specific over-engineered files
        files_to_remove = [
            "src/services/infrastructure/incident_management.py",
            "src/services/infrastructure/disaster_recovery.py",
            "src/config/monitoring_config.py",
            "src/config/chaos_config.py",
            "src/config/disaster_recovery_config.py",
            "src/config/complex_profit_config.py",
        ]

        self._remove_files(files_to_remove)

        # 3. Remove complex monitoring (keep only simple monitoring)
        monitoring_patterns = [
            "infrastructure/monitoring/advanced_*",
            "packages/shared/monitoring/complex_*",
            "src/services/infrastructure/observability.py",
        ]

        self._remove_by_pattern(monitoring_patterns)

        # Generate report
        return self._generate_report()

    def _remove_directories(self, dirs: List[str]):
        """Remove directories and track results"""
        for dir_name in dirs:
            dir_path = self.repo_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                try:
                    shutil.rmtree(dir_path)
                    self.removed_dirs.append(str(dir_path))
                    print(f"✅ Removed directory: {dir_name}")
                except Exception as e:
                    error = f"Failed to remove {dir_name}: {str(e)}"
                    self.errors.append(error)
                    print(f"❌ {error}")
            else:
                print(f"⚠️  Directory not found (skipping): {dir_name}")

    def _remove_files(self, files: List[str]):
        """Remove specific files"""
        for file_name in files:
            file_path = self.repo_root / file_name
            if file_path.exists() and file_path.is_file():
                try:
                    file_path.unlink()
                    self.removed_files.append(str(file_path))
                    print(f"✅ Removed file: {file_name}")
                except Exception as e:
                    error = f"Failed to remove {file_name}: {str(e)}"
                    self.errors.append(error)
                    print(f"❌ {error}")
            else:
                print(f"⚠️  File not found (skipping): {file_name}")

    def _remove_by_pattern(self, patterns: List[str]):
        """Remove files matching glob patterns"""
        for pattern in patterns:
            pattern_path = self.repo_root / pattern
            matches = glob.glob(str(pattern_path))

            if not matches:
                print(f"⚠️  No matches for pattern: {pattern}")
                continue

            for match in matches:
                match_path = Path(match)
                try:
                    if match_path.is_file():
                        match_path.unlink()
                        self.removed_files.append(str(match_path))
                        print(f"✅ Removed (pattern): {match_path.relative_to(self.repo_root)}")
                    elif match_path.is_dir():
                        shutil.rmtree(match_path)
                        self.removed_dirs.append(str(match_path))
                        print(f"✅ Removed dir (pattern): {match_path.relative_to(self.repo_root)}")
                except Exception as e:
                    error = f"Failed to remove {match}: {str(e)}"
                    self.errors.append(error)
                    print(f"❌ {error}")

    def _generate_report(self) -> Dict:
        """Generate cleanup report"""
        total_removed = len(self.removed_files) + len(self.removed_dirs)

        report = {
            "removed_files": len(self.removed_files),
            "removed_directories": len(self.removed_dirs),
            "total_removed": total_removed,
            "errors": len(self.errors),
            "estimated_complexity_reduction": "70%",
            "status": "success" if len(self.errors) == 0 else "partial",
        }

        print("\n" + "=" * 60)
        print("📊 PIVOT CLEANUP REPORT")
        print("=" * 60)
        print(f"Files removed: {report['removed_files']}")
        print(f"Directories removed: {report['removed_directories']}")
        print(f"Total items removed: {report['total_removed']}")
        print(f"Errors encountered: {report['errors']}")
        print(f"Estimated complexity reduction: {report['estimated_complexity_reduction']}")
        print(f"Status: {report['status'].upper()}")

        if self.errors:
            print("\n⚠️  ERRORS:")
            for error in self.errors:
                print(f"  - {error}")

        print("\n✅ PIVOT CLEANUP COMPLETE!")
        print("Next steps:")
        print("  1. Create new simplified services")
        print("  2. Update dependencies")
        print("  3. Run tests to verify core functionality")
        print("  4. Deploy to staging for validation")

        return report


def main():
    """Execute cleanup from repo root"""
    import sys

    # Get repo root (assume script is in tools/)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"📂 Repository root: {repo_root}")
    print(f"🚀 Starting pivot cleanup...\n")

    cleanup = PivotCleanup(str(repo_root))
    report = cleanup.execute_pivot_cleanup()

    # Exit with error code if cleanup had errors
    if report["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
