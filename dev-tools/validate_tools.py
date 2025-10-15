#!/usr/bin/env python3
"""
Development Tools Validation Script

Validates that all development tools are properly installed and configured.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict
import importlib.util


class ToolValidator:
    """Validates development tools setup"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tools_dir = project_root / "dev-tools"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate_all(self) -> bool:
        """Run all validations"""
        print("🔍 Validating AI Nutritionist Development Tools...\n")
        
        # Validate structure
        self.validate_directory_structure()
        
        # Validate Python files
        self.validate_python_files()
        
        # Validate CLI
        self.validate_cli_tool()
        
        # Validate dependencies
        self.validate_dependencies()
        
        # Report results
        return self.report_results()
    
    def validate_directory_structure(self):
        """Validate directory structure"""
        print("📁 Validating directory structure...")
        
        required_dirs = [
            "dev-tools",
            "dev-tools/generators",
            "dev-tools/scripts", 
            "dev-tools/debugging",
            "dev-tools/docs",
            "dev-tools/templates"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                self.errors.append(f"Missing directory: {dir_path}")
            else:
                print(f"  ✅ {dir_path}")
    
    def validate_python_files(self):
        """Validate Python files exist and can be imported"""
        print("\n🐍 Validating Python files...")
        
        required_files = [
            "dev-tools/dev-cli.py",
            "dev-tools/generators/__init__.py",
            "dev-tools/generators/service_generator.py",
            "dev-tools/generators/entity_generator.py",
            "dev-tools/generators/repository_generator.py", 
            "dev-tools/generators/test_generator.py",
            "dev-tools/generators/enhanced_generators.py",
            "dev-tools/generators/migration_generator.py",
            "dev-tools/generators/api_generator.py",
            "dev-tools/scripts/setup_environment.py",
            "dev-tools/scripts/seed_database.py",
            "dev-tools/debugging/request_replay.py",
            "dev-tools/docs/api_docs_generator.py"
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.errors.append(f"Missing file: {file_path}")
            else:
                # Try to validate Python syntax
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        compile(f.read(), full_path, 'exec')
                    print(f"  ✅ {file_path}")
                except SyntaxError as e:
                    self.errors.append(f"Syntax error in {file_path}: {e}")
                except Exception as e:
                    self.warnings.append(f"Could not validate {file_path}: {e}")
    
    def validate_cli_tool(self):
        """Validate CLI tool functionality"""
        print("\n🖥️ Validating CLI tool...")
        
        cli_path = self.tools_dir / "dev-cli.py"
        if not cli_path.exists():
            self.errors.append("CLI tool not found: dev-cli.py")
            return
        
        try:
            # Test CLI help
            result = subprocess.run([
                sys.executable, str(cli_path), "--help"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("  ✅ CLI tool runs successfully")
                
                # Check for expected commands
                help_text = result.stdout
                expected_commands = ["setup", "generate", "db", "test", "debug", "docs"]
                
                for command in expected_commands:
                    if command in help_text:
                        print(f"  ✅ Command '{command}' available")
                    else:
                        self.warnings.append(f"Command '{command}' not found in help")
            else:
                self.errors.append(f"CLI tool failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.errors.append("CLI tool timed out")
        except Exception as e:
            self.errors.append(f"CLI tool error: {e}")
    
    def validate_dependencies(self):
        """Validate required dependencies"""
        print("\n📦 Validating dependencies...")
        
        required_packages = [
            "fastapi",
            "pydantic", 
            "boto3",
            "pytest",
            "aiohttp",
            "jinja2",
            "pyyaml"
        ]
        
        for package in required_packages:
            try:
                importlib.import_module(package)
                print(f"  ✅ {package}")
            except ImportError:
                self.warnings.append(f"Package '{package}' not installed (may be optional)")
    
    def report_results(self) -> bool:
        """Report validation results"""
        print("\n" + "="*60)
        print("📋 VALIDATION RESULTS")
        print("="*60)
        
        if not self.errors and not self.warnings:
            print("🎉 All validations passed! Development tools are ready to use.")
            print("\n🚀 Quick start:")
            print("  python dev-tools/dev-cli.py setup")
            print("  python dev-tools/dev-cli.py --help")
            return True
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if self.errors:
            print("\n🔧 Please fix the errors above before using the development tools.")
            return False
        else:
            print("\n✅ Development tools are functional with minor issues.")
            return True


def main():
    """Main validation entry point"""
    project_root = Path(__file__).parent.parent
    validator = ToolValidator(project_root)
    
    success = validator.validate_all()
    
    if success:
        print("\n🎯 Next steps:")
        print("  1. Run: python dev-tools/dev-cli.py setup")
        print("  2. Check: python dev-tools/dev-cli.py --help")
        print("  3. Generate: python dev-tools/dev-cli.py generate service --name ExampleService")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
