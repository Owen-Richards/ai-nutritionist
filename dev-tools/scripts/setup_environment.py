#!/usr/bin/env python3
"""
Local Environment Setup Script

Automates the complete setup of the development environment:
- Python environment creation and configuration
- Dependency installation
- AWS credentials setup
- Database initialization
- Configuration file creation
- Development tools installation
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional
import json
import shutil


class EnvironmentSetup:
    """Handles local development environment setup"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.system = platform.system().lower()
        self.python_executable = self._find_python_executable()
        
    def setup_complete_environment(self) -> bool:
        """Set up complete development environment"""
        try:
            print("🚀 Setting up AI Nutritionist development environment...")
            
            # Step 1: Check prerequisites
            print("\n📋 Checking prerequisites...")
            if not self._check_prerequisites():
                print("❌ Prerequisites check failed")
                return False
            
            # Step 2: Create Python virtual environment
            print("\n🐍 Setting up Python environment...")
            if not self._setup_python_environment():
                print("❌ Python environment setup failed")
                return False
            
            # Step 3: Install dependencies
            print("\n📦 Installing dependencies...")
            if not self._install_dependencies():
                print("❌ Dependency installation failed")
                return False
            
            # Step 4: Setup configuration
            print("\n⚙️ Setting up configuration...")
            if not self._setup_configuration():
                print("❌ Configuration setup failed")
                return False
            
            # Step 5: Initialize database
            print("\n🗄️ Initializing database...")
            if not self._initialize_database():
                print("❌ Database initialization failed")
                return False
            
            # Step 6: Setup development tools
            print("\n🛠️ Setting up development tools...")
            if not self._setup_development_tools():
                print("❌ Development tools setup failed")
                return False
            
            # Step 7: Run validation tests
            print("\n✅ Running validation tests...")
            if not self._run_validation_tests():
                print("❌ Validation tests failed")
                return False
            
            print("\n🎉 Development environment setup completed successfully!")
            self._print_next_steps()
            return True
            
        except Exception as e:
            print(f"❌ Environment setup failed: {e}")
            return False
    
    def _check_prerequisites(self) -> bool:
        """Check if all prerequisites are installed"""
        prerequisites = [
            ("python", self._check_python),
            ("git", self._check_git),
            ("aws-cli", self._check_aws_cli),
            ("node", self._check_node),
        ]
        
        all_good = True
        for name, check_func in prerequisites:
            if check_func():
                print(f"✅ {name} is available")
            else:
                print(f"❌ {name} is missing or not properly configured")
                all_good = False
        
        return all_good
    
    def _check_python(self) -> bool:
        """Check if Python 3.8+ is available"""
        try:
            result = subprocess.run([self.python_executable, "--version"], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split()[1]
                major, minor = map(int, version.split('.')[:2])
                return major >= 3 and minor >= 8
        except:
            pass
        return False
    
    def _check_git(self) -> bool:
        """Check if Git is available"""
        try:
            result = subprocess.run(["git", "--version"], 
                                 capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _check_aws_cli(self) -> bool:
        """Check if AWS CLI is available"""
        try:
            result = subprocess.run(["aws", "--version"], 
                                 capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _check_node(self) -> bool:
        """Check if Node.js is available"""
        try:
            result = subprocess.run(["node", "--version"], 
                                 capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _find_python_executable(self) -> str:
        """Find the appropriate Python executable"""
        candidates = ["python3", "python", "py"]
        for candidate in candidates:
            try:
                result = subprocess.run([candidate, "--version"], 
                                     capture_output=True, text=True)
                if result.returncode == 0 and "Python 3" in result.stdout:
                    return candidate
            except:
                continue
        return "python"
    
    def _setup_python_environment(self) -> bool:
        """Set up Python virtual environment"""
        try:
            venv_path = self.project_root / ".venv"
            
            # Remove existing virtual environment if it exists
            if venv_path.exists():
                print("🗑️ Removing existing virtual environment...")
                shutil.rmtree(venv_path)
            
            # Create new virtual environment
            print("📦 Creating virtual environment...")
            subprocess.run([self.python_executable, "-m", "venv", str(venv_path)], 
                         check=True)
            
            # Activate virtual environment and upgrade pip
            if self.system == "windows":
                pip_executable = venv_path / "Scripts" / "pip.exe"
                python_executable = venv_path / "Scripts" / "python.exe"
            else:
                pip_executable = venv_path / "bin" / "pip"
                python_executable = venv_path / "bin" / "python"
            
            print("⬆️ Upgrading pip...")
            subprocess.run([str(python_executable), "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error setting up Python environment: {e}")
            return False
    
    def _install_dependencies(self) -> bool:
        """Install project dependencies"""
        try:
            venv_path = self.project_root / ".venv"
            
            if self.system == "windows":
                pip_executable = venv_path / "Scripts" / "pip.exe"
            else:
                pip_executable = venv_path / "bin" / "pip"
            
            # Install production dependencies
            print("📋 Installing production dependencies...")
            subprocess.run([str(pip_executable), "install", "-r", "requirements.txt"], 
                         cwd=self.project_root, check=True)
            
            # Install development dependencies
            dev_requirements = self.project_root / "requirements-dev.txt"
            if dev_requirements.exists():
                print("🔧 Installing development dependencies...")
                subprocess.run([str(pip_executable), "install", "-r", "requirements-dev.txt"], 
                             cwd=self.project_root, check=True)
            
            # Install pre-commit hooks
            print("🪝 Installing pre-commit hooks...")
            if self.system == "windows":
                precommit_executable = venv_path / "Scripts" / "pre-commit.exe"
            else:
                precommit_executable = venv_path / "bin" / "pre-commit"
            
            subprocess.run([str(precommit_executable), "install"], 
                         cwd=self.project_root, check=True)
            
            # Install JavaScript dependencies if package.json exists
            package_json = self.project_root / "package.json"
            if package_json.exists():
                print("📦 Installing JavaScript dependencies...")
                subprocess.run(["npm", "install"], cwd=self.project_root, check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing dependencies: {e}")
            return False
    
    def _setup_configuration(self) -> bool:
        """Set up configuration files"""
        try:
            # Create .env file from template
            env_template = self.project_root / ".env.template"
            env_file = self.project_root / ".env"
            
            if env_template.exists() and not env_file.exists():
                print("📝 Creating .env file from template...")
                shutil.copy(env_template, env_file)
                print("⚠️ Please update .env file with your AWS credentials and configuration")
            
            # Create local config directory
            config_dir = self.project_root / "config" / "local"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create local development configuration
            local_config = {
                "environment": "development",
                "debug": True,
                "aws": {
                    "region": "us-east-1",
                    "profile": "default"
                },
                "database": {
                    "endpoint": "http://localhost:8000",
                    "region": "us-east-1"
                },
                "api": {
                    "host": "localhost",
                    "port": 8000,
                    "reload": True
                },
                "logging": {
                    "level": "DEBUG",
                    "format": "detailed"
                }
            }
            
            config_file = config_dir / "development.json"
            if not config_file.exists():
                print("⚙️ Creating local development configuration...")
                with open(config_file, 'w') as f:
                    json.dump(local_config, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up configuration: {e}")
            return False
    
    def _initialize_database(self) -> bool:
        """Initialize local database"""
        try:
            # Check if DynamoDB Local is available
            print("🔍 Checking for DynamoDB Local...")
            
            # Create database directory
            db_dir = self.project_root / "data" / "dynamodb"
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Create sample data directory
            sample_data_dir = self.project_root / "data" / "sample"
            sample_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Run database initialization script if it exists
            db_init_script = self.project_root / "dev-tools" / "scripts" / "init_database.py"
            if db_init_script.exists():
                venv_path = self.project_root / ".venv"
                if self.system == "windows":
                    python_executable = venv_path / "Scripts" / "python.exe"
                else:
                    python_executable = venv_path / "bin" / "python"
                
                print("🗄️ Running database initialization script...")
                subprocess.run([str(python_executable), str(db_init_script)], 
                             cwd=self.project_root, check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error initializing database: {e}")
            return False
        except Exception as e:
            print(f"⚠️ Database initialization warning: {e}")
            return True  # Non-critical error
    
    def _setup_development_tools(self) -> bool:
        """Set up development tools and utilities"""
        try:
            # Create tools directory
            tools_dir = self.project_root / "dev-tools"
            tools_dir.mkdir(exist_ok=True)
            
            # Make generator scripts executable
            generators_dir = tools_dir / "generators"
            if generators_dir.exists():
                for script in generators_dir.glob("*.py"):
                    if self.system != "windows":
                        os.chmod(script, 0o755)
            
            # Create development scripts directory
            scripts_dir = tools_dir / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            
            # Create logs directory
            logs_dir = self.project_root / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            # Create test data directory
            test_data_dir = self.project_root / "tests" / "data"
            test_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup IDE configuration
            self._setup_ide_configuration()
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting up development tools: {e}")
            return False
    
    def _setup_ide_configuration(self):
        """Set up IDE configuration files"""
        try:
            # VS Code configuration
            vscode_dir = self.project_root / ".vscode"
            vscode_dir.mkdir(exist_ok=True)
            
            # VS Code settings
            vscode_settings = {
                "python.defaultInterpreterPath": "./.venv/bin/python" if self.system != "windows" else "./.venv/Scripts/python.exe",
                "python.linting.enabled": True,
                "python.linting.pylintEnabled": False,
                "python.linting.flake8Enabled": True,
                "python.linting.mypyEnabled": True,
                "python.formatting.provider": "black",
                "python.sortImports.args": ["--profile", "black"],
                "editor.formatOnSave": True,
                "editor.codeActionsOnSave": {
                    "source.organizeImports": True
                },
                "files.exclude": {
                    "**/__pycache__": True,
                    "**/*.pyc": True,
                    ".venv": True,
                    ".pytest_cache": True,
                    ".mypy_cache": True
                }
            }
            
            settings_file = vscode_dir / "settings.json"
            if not settings_file.exists():
                with open(settings_file, 'w') as f:
                    json.dump(vscode_settings, f, indent=2)
            
            # VS Code launch configuration
            launch_config = {
                "version": "0.2.0",
                "configurations": [
                    {
                        "name": "Python: Current File",
                        "type": "python",
                        "request": "launch",
                        "program": "${file}",
                        "console": "integratedTerminal"
                    },
                    {
                        "name": "Python: FastAPI",
                        "type": "python",
                        "request": "launch",
                        "module": "uvicorn",
                        "args": ["src.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
                        "console": "integratedTerminal"
                    },
                    {
                        "name": "Python: Tests",
                        "type": "python",
                        "request": "launch",
                        "module": "pytest",
                        "args": ["tests/", "-v"],
                        "console": "integratedTerminal"
                    }
                ]
            }
            
            launch_file = vscode_dir / "launch.json"
            if not launch_file.exists():
                with open(launch_file, 'w') as f:
                    json.dump(launch_config, f, indent=2)
            
        except Exception as e:
            print(f"⚠️ IDE configuration warning: {e}")
    
    def _run_validation_tests(self) -> bool:
        """Run validation tests to ensure setup is correct"""
        try:
            venv_path = self.project_root / ".venv"
            if self.system == "windows":
                python_executable = venv_path / "Scripts" / "python.exe"
            else:
                python_executable = venv_path / "bin" / "python"
            
            # Run project validation tests
            validation_test = self.project_root / "tests" / "test_project_validation.py"
            if validation_test.exists():
                print("🧪 Running project validation tests...")
                result = subprocess.run([str(python_executable), str(validation_test)], 
                                     cwd=self.project_root, capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Project validation tests passed")
                else:
                    print(f"❌ Project validation tests failed: {result.stderr}")
                    return False
            
            # Test import of main modules
            print("📦 Testing module imports...")
            test_imports = [
                "import src.core",
                "import src.services",
                "import src.api",
                "from src.main import app"
            ]
            
            for import_stmt in test_imports:
                result = subprocess.run([str(python_executable), "-c", import_stmt], 
                                     cwd=self.project_root, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ Import test failed: {import_stmt}")
                    print(f"Error: {result.stderr}")
                    return False
            
            print("✅ All module imports successful")
            return True
            
        except Exception as e:
            print(f"❌ Error running validation tests: {e}")
            return False
    
    def _print_next_steps(self):
        """Print next steps for the developer"""
        venv_activation = (
            ".venv\\Scripts\\activate" if self.system == "windows" 
            else "source .venv/bin/activate"
        )
        
        print(f"""
🎯 Next Steps:

1. Activate the virtual environment:
   {venv_activation}

2. Update your .env file with AWS credentials:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - AWS_DEFAULT_REGION

3. Start the development server:
   uvicorn src.main:app --reload

4. Run tests:
   pytest tests/ -v

5. Generate code using development tools:
   python dev-tools/generators/service_generator.py --help

6. Access API documentation:
   http://localhost:8000/docs

📚 Documentation:
   - Architecture: docs/architecture-diagram.mmd
   - API Reference: docs/api/
   - Deployment: docs/deployment_instructions.md

🛠️ Development Commands:
   - make test          # Run tests
   - make format        # Format code
   - make lint          # Run linting
   - make build         # Build for deployment

Happy coding! 🚀
""")


def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent.parent
    setup = EnvironmentSetup(project_root)
    
    success = setup.setup_complete_environment()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
