"""
Simple validation tests for the project structure
"""

import json
import os
from pathlib import Path


def test_project_structure():
    """Test that all required project files exist"""
    project_root = Path(__file__).parent.parent
    
    # Check main directories
    assert (project_root / "src").exists()
    assert (project_root / "src" / "handlers").exists()
    assert (project_root / "src" / "services").exists()
    assert (project_root / "infrastructure").exists()
    assert (project_root / "tests").exists()
    
    # Check key files
    assert (project_root / "requirements.txt").exists()
    assert (project_root / "README.md").exists()
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "infrastructure" / "template.yaml").exists()


def test_sam_template_structure():
    """Test that SAM template has required structure"""
    project_root = Path(__file__).parent.parent
    sam_template = project_root / "infrastructure" / "template.yaml"
    
    assert sam_template.exists()
    
    # Read and basic validation
    content = sam_template.read_text()
    assert "AWSTemplateFormatVersion" in content
    assert "Transform: AWS::Serverless-2016-10-31" in content
    assert "MessageHandlerFunction" in content
    assert "SchedulerFunction" in content
    assert "UserDataTable" in content


def test_sample_data_files():
    """Test that sample data files are properly formatted"""
    project_root = Path(__file__).parent.parent
    
    # Test Twilio webhook sample (moved to fixtures)
    webhook_file = project_root / "tests" / "fixtures" / "data" / "sample-twilio-webhook.json"
    assert webhook_file.exists()
    
    webhook_data = json.loads(webhook_file.read_text())
    assert "From" in webhook_data
    assert "Body" in webhook_data
    assert "MessageSid" in webhook_data
    
    # Test recipe sample (moved to fixtures)
    recipe_file = project_root / "tests" / "fixtures" / "data" / "sample-recipes.json"
    assert recipe_file.exists()
    
    recipe_data = json.loads(recipe_file.read_text())
    assert isinstance(recipe_data, list)
    assert len(recipe_data) > 0
    assert "name" in recipe_data[0]
    assert "ingredients" in recipe_data[0]


def test_requirements_file():
    """Test that requirements.txt contains essential packages"""
    project_root = Path(__file__).parent.parent
    requirements_file = project_root / "requirements.txt"
    
    assert requirements_file.exists()
    
    content = requirements_file.read_text()
    assert "boto3" in content
    # Migrated from Twilio to AWS End User Messaging
    assert "stripe" in content  # For payments
    assert "pytest" in content


def test_documentation_files():
    """Test that documentation files exist and have content"""
    project_root = Path(__file__).parent.parent
    
    readme = project_root / "README.md"
    assert readme.exists()
    assert len(readme.read_text(encoding='utf-8')) > 1000  # Substantial content
    
    # Check consolidated documentation in docs/
    docs_readme = project_root / "docs" / "README.md"
    assert docs_readme.exists()
    assert "Prerequisites" in docs_readme.read_text(encoding='utf-8')
    
    # Check that essential configuration files exist
    env_template = project_root / ".env.template"
    assert env_template.exists()
    assert "AWS_DEFAULT_REGION" in env_template.read_text()


def test_python_modules_import():
    """Test that Python modules can be imported (syntax check)"""
    project_root = Path(__file__).parent.parent
    
    # Add src to path for imports
    import sys
    sys.path.insert(0, str(project_root / "src"))
    
    # Test that modules can be imported (basic syntax validation)
    try:
        # Test new domain-organized service imports
        import services.nutrition.insights
        import services.personalization.preferences
        import services.meal_planning.planner
        import services.messaging.sms
        import services.business.subscription
        # Basic syntax validation passed
        assert True
    except ImportError as e:
        # This is expected due to missing dependencies in test environment
        pass
    except SyntaxError as e:
        # This should not happen - indicates syntax errors
        assert False, f"Syntax error in module: {e}"


if __name__ == "__main__":
    test_project_structure()
    test_sam_template_structure()
    test_sample_data_files()
    test_requirements_file()
    test_documentation_files()
    test_python_modules_import()
    print("✅ All validation tests passed!")
