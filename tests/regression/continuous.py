"""
Continuous Testing Integration
CI/CD integration for automated regression testing
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .framework import RegressionTestFramework, FrameworkResult
from .config import RegressionTestConfig


@dataclass
class CIEnvironment:
    """CI/CD environment information"""
    provider: str  # github, gitlab, jenkins, etc.
    is_pr: bool
    branch: str
    commit_sha: str
    build_id: str
    build_url: Optional[str] = None
    pr_number: Optional[int] = None


class PreCommitHook:
    """Pre-commit hook integration"""
    
    @staticmethod
    def install(project_root: Path):
        """Install pre-commit hook"""
        hooks_dir = project_root / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        
        hook_script = hooks_dir / "pre-commit"
        
        hook_content = """#!/bin/bash
# Regression Testing Pre-commit Hook

echo "🔍 Running regression tests..."

# Run pre-commit tests
python -m tests.regression.cli pre-commit

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ Pre-commit tests passed"
else
    echo "❌ Pre-commit tests failed"
    echo "💡 Run 'python -m tests.regression.cli pre-commit' to see details"
fi

exit $exit_code
"""
        
        hook_script.write_text(hook_content)
        hook_script.chmod(0o755)
        
        print("✅ Pre-commit hook installed")
    
    @staticmethod
    def uninstall(project_root: Path):
        """Uninstall pre-commit hook"""
        hook_script = project_root / ".git" / "hooks" / "pre-commit"
        if hook_script.exists():
            hook_script.unlink()
            print("✅ Pre-commit hook removed")


class GitHubActionsIntegration:
    """GitHub Actions CI integration"""
    
    @staticmethod
    def generate_workflow(project_root: Path, workflow_name: str = "regression-tests"):
        """Generate GitHub Actions workflow for regression testing"""
        
        workflows_dir = project_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        workflow_file = workflows_dir / f"{workflow_name}.yml"
        
        workflow_content = """name: Regression Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    # Run nightly at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:
    inputs:
      test_type:
        description: 'Test type to run'
        required: true
        default: 'pull_request'
        type: choice
        options:
          - pull_request
          - nightly
          - release
          - flaky_detection

jobs:
  regression-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history for better test selection
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Set up test environment
      run: |
        # Create test reports directory
        mkdir -p test-reports
        
        # Set environment variables
        echo "REGRESSION_CI_MODE=true" >> $GITHUB_ENV
        echo "REGRESSION_MAX_WORKERS=4" >> $GITHUB_ENV
        echo "PYTHONPATH=$GITHUB_WORKSPACE/src:$PYTHONPATH" >> $GITHUB_ENV
    
    - name: Run regression tests (Pull Request)
      if: github.event_name == 'pull_request' || (github.event_name == 'workflow_dispatch' && inputs.test_type == 'pull_request')
      run: |
        python -m tests.regression.cli pull-request \\
          --max-duration 1800 \\
          --output test-reports/pr-regression.json
    
    - name: Run regression tests (Push to main/develop)
      if: github.event_name == 'push'
      run: |
        python -m tests.regression.cli nightly \\
          --output test-reports/push-regression.json
    
    - name: Run nightly regression tests
      if: github.event.schedule == '0 2 * * *' || (github.event_name == 'workflow_dispatch' && inputs.test_type == 'nightly')
      run: |
        python -m tests.regression.cli nightly \\
          --output test-reports/nightly-regression.json
    
    - name: Run flaky test detection
      if: github.event_name == 'workflow_dispatch' && inputs.test_type == 'flaky_detection'
      run: |
        python -m tests.regression.cli flaky-detection \\
          --runs-per-test 10 \\
          --output test-reports/flaky-detection.json
    
    - name: Upload test reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: regression-test-reports-py${{ matrix.python-version }}
        path: test-reports/
        retention-days: 30
    
    - name: Upload coverage reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: coverage-reports-py${{ matrix.python-version }}
        path: |
          htmlcov/
          .coverage
        retention-days: 30
    
    - name: Comment PR with results
      if: github.event_name == 'pull_request' && always()
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const path = 'test-reports/pr-regression.json';
          
          if (fs.existsSync(path)) {
            const report = JSON.parse(fs.readFileSync(path, 'utf8'));
            
            const body = `
            ## 🧪 Regression Test Results
            
            **Success Rate:** ${(report.summary.success_rate * 100).toFixed(1)}%
            **Total Tests:** ${report.summary.total_tests}
            **Duration:** ${(report.summary.total_duration / 60).toFixed(1)} minutes
            
            | Status | Count |
            |--------|-------|
            | ✅ Passed | ${report.summary.passed} |
            | ❌ Failed | ${report.summary.failed} |
            | ⏭️ Skipped | ${report.summary.skipped} |
            | 💥 Errors | ${report.summary.errors} |
            
            ${report.recommendations.length > 0 ? 
              '**Recommendations:**\\n' + 
              report.recommendations.map(r => `- ${r}`).join('\\n') : 
              ''}
            
            <details>
            <summary>View detailed report</summary>
            
            [Download full report](../../../actions/runs/${{ github.run_id }})
            
            </details>
            `;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
          }

  performance-tracking:
    runs-on: ubuntu-latest
    needs: regression-tests
    if: github.event_name == 'schedule' # Only on nightly runs
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Download test reports
      uses: actions/download-artifact@v3
      with:
        name: regression-test-reports-py3.11
        path: test-reports/
    
    - name: Track performance trends
      run: |
        python -c "
        import json
        import os
        from datetime import datetime
        
        # Load current results
        if os.path.exists('test-reports/nightly-regression.json'):
            with open('test-reports/nightly-regression.json') as f:
                current = json.load(f)
            
            # Store historical data (could be enhanced with database)
            trend_data = {
                'date': datetime.now().isoformat(),
                'success_rate': current['summary']['success_rate'],
                'duration': current['summary']['total_duration'],
                'total_tests': current['summary']['total_tests']
            }
            
            print(f'Performance data: {trend_data}')
        "
"""
        
        workflow_file.write_text(workflow_content)
        print(f"✅ GitHub Actions workflow created: {workflow_file}")


class JenkinsIntegration:
    """Jenkins CI integration"""
    
    @staticmethod
    def generate_jenkinsfile(project_root: Path):
        """Generate Jenkinsfile for regression testing"""
        
        jenkinsfile = project_root / "Jenkinsfile.regression"
        
        jenkinsfile_content = """pipeline {
    agent any
    
    environment {
        REGRESSION_CI_MODE = 'true'
        PYTHONPATH = "${WORKSPACE}/src"
    }
    
    triggers {
        // Nightly builds at 2 AM
        cron('0 2 * * *')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install -r requirements-dev.txt
                    mkdir -p test-reports
                '''
            }
        }
        
        stage('Pre-commit Tests') {
            when { changeRequest() }
            steps {
                sh 'python -m tests.regression.cli pre-commit --output test-reports/pre-commit.json'
            }
        }
        
        stage('Pull Request Tests') {
            when { changeRequest() }
            steps {
                sh 'python -m tests.regression.cli pull-request --output test-reports/pr-regression.json'
            }
        }
        
        stage('Nightly Tests') {
            when { 
                anyOf {
                    triggeredBy 'TimerTrigger'
                    branch 'main'
                }
            }
            steps {
                sh 'python -m tests.regression.cli nightly --output test-reports/nightly-regression.json'
            }
        }
        
        stage('Flaky Detection') {
            when { 
                anyOf {
                    triggeredBy 'TimerTrigger'
                    expression { params.RUN_FLAKY_DETECTION == 'true' }
                }
            }
            steps {
                sh 'python -m tests.regression.cli flaky-detection --output test-reports/flaky-detection.json'
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'test-reports/**/*', fingerprint: true
            
            script {
                if (fileExists('test-reports/pr-regression.json')) {
                    def report = readJSON file: 'test-reports/pr-regression.json'
                    
                    currentBuild.description = "Success Rate: ${(report.summary.success_rate * 100).round(1)}%"
                    
                    if (report.summary.success_rate < 0.9) {
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }
        
        failure {
            emailext (
                subject: "Regression Tests Failed - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: '''
                <h2>Regression Test Failure</h2>
                <p><strong>Job:</strong> ${JOB_NAME}</p>
                <p><strong>Build:</strong> ${BUILD_NUMBER}</p>
                <p><strong>Branch:</strong> ${BRANCH_NAME}</p>
                
                <p>Please check the build logs and test reports for details.</p>
                
                <p><a href="${BUILD_URL}">View Build</a></p>
                ''',
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}"""
        
        jenkinsfile.write_text(jenkinsfile_content)
        print(f"✅ Jenkinsfile created: {jenkinsfile}")


class ContinuousTestingOrchestrator:
    """Main orchestrator for continuous testing integration"""
    
    def __init__(self, config: Optional[RegressionTestConfig] = None):
        self.config = config or RegressionTestConfig.from_environment()
        self.framework = RegressionTestFramework(self.config)
    
    def detect_ci_environment(self) -> CIEnvironment:
        """Detect current CI/CD environment"""
        
        # GitHub Actions
        if os.getenv('GITHUB_ACTIONS'):
            return CIEnvironment(
                provider="github",
                is_pr=os.getenv('GITHUB_EVENT_NAME') == 'pull_request',
                branch=os.getenv('GITHUB_REF_NAME', 'unknown'),
                commit_sha=os.getenv('GITHUB_SHA', 'unknown'),
                build_id=os.getenv('GITHUB_RUN_ID', 'unknown'),
                build_url=f"https://github.com/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')}",
                pr_number=int(os.getenv('GITHUB_EVENT_PULL_REQUEST_NUMBER', 0)) or None
            )
        
        # GitLab CI
        elif os.getenv('GITLAB_CI'):
            return CIEnvironment(
                provider="gitlab",
                is_pr=os.getenv('CI_PIPELINE_SOURCE') == 'merge_request_event',
                branch=os.getenv('CI_COMMIT_REF_NAME', 'unknown'),
                commit_sha=os.getenv('CI_COMMIT_SHA', 'unknown'),
                build_id=os.getenv('CI_PIPELINE_ID', 'unknown'),
                build_url=os.getenv('CI_PIPELINE_URL'),
                pr_number=int(os.getenv('CI_MERGE_REQUEST_IID', 0)) or None
            )
        
        # Jenkins
        elif os.getenv('JENKINS_URL'):
            return CIEnvironment(
                provider="jenkins",
                is_pr=os.getenv('CHANGE_ID') is not None,
                branch=os.getenv('BRANCH_NAME', 'unknown'),
                commit_sha=os.getenv('GIT_COMMIT', 'unknown'),
                build_id=os.getenv('BUILD_ID', 'unknown'),
                build_url=os.getenv('BUILD_URL'),
                pr_number=int(os.getenv('CHANGE_ID', 0)) or None
            )
        
        # Default/Local
        else:
            return CIEnvironment(
                provider="local",
                is_pr=False,
                branch="unknown",
                commit_sha="unknown",
                build_id="local"
            )
    
    def run_ci_appropriate_tests(self) -> FrameworkResult:
        """Run tests appropriate for current CI environment"""
        
        ci_env = self.detect_ci_environment()
        
        if ci_env.is_pr:
            # Pull request - run comprehensive tests
            return self.framework.run_pull_request_tests()
        
        elif ci_env.branch in ['main', 'master', 'develop']:
            # Main branch - run nightly tests
            return self.framework.run_nightly_tests()
        
        else:
            # Feature branch - run pre-commit level tests
            return self.framework.run_pre_commit_tests()
    
    def setup_ci_integration(self, provider: str = "auto"):
        """Setup CI/CD integration"""
        
        if provider == "auto":
            ci_env = self.detect_ci_environment()
            provider = ci_env.provider
        
        project_root = self.config.project_root
        
        if provider == "github":
            GitHubActionsIntegration.generate_workflow(project_root)
        
        elif provider == "jenkins":
            JenkinsIntegration.generate_jenkinsfile(project_root)
        
        else:
            print(f"⚠️  CI provider '{provider}' not supported")
    
    def install_hooks(self):
        """Install git hooks for continuous testing"""
        PreCommitHook.install(self.config.project_root)
    
    def uninstall_hooks(self):
        """Remove git hooks"""
        PreCommitHook.uninstall(self.config.project_root)
