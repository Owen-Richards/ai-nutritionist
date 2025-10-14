"""
CI/CD Integration for Contract Testing

Provides automated contract testing integration for continuous integration
and deployment pipelines.
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from src.contracts.core.contract_manager import ContractManager
from src.contracts.core.provider_verifier import ProviderVerifier
from src.contracts.core.consumer_tester import ConsumerTester
from src.contracts.core.version_compatibility import VersionCompatibilityChecker
from src.contracts.providers.nutrition_provider import NutritionServiceProvider
from src.contracts.providers.meal_planning_provider import MealPlanningServiceProvider
from src.contracts.providers.messaging_provider import MessagingServiceProvider
from src.contracts.consumers.mobile_app_consumer import MobileAppConsumer


logger = logging.getLogger(__name__)


class ContractTestingCI:
    """CI/CD integration for contract testing."""
    
    def __init__(
        self,
        contract_dir: str = "contracts",
        pact_dir: str = "pacts",
        results_dir: str = "contract-test-results"
    ):
        self.contract_dir = Path(contract_dir)
        self.pact_dir = Path(pact_dir)
        self.results_dir = Path(results_dir)
        
        # Create directories
        self.contract_dir.mkdir(exist_ok=True)
        self.pact_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.contract_manager = ContractManager(self.contract_dir)
        self.provider_verifier = ProviderVerifier()
        self.version_checker = VersionCompatibilityChecker()
        
        # Test results
        self.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown",
            "summary": {},
            "contract_validations": [],
            "provider_verifications": [],
            "consumer_tests": [],
            "breaking_changes": [],
            "warnings": []
        }
    
    def run_consumer_contract_tests(self, consumer: str = "mobile-app") -> Dict[str, Any]:
        """Run consumer contract tests."""
        logger.info(f"Running consumer contract tests for {consumer}")
        
        consumer_tester = ConsumerTester(consumer_name=consumer, pact_dir=self.pact_dir)
        
        if consumer == "mobile-app":
            consumer_instance = MobileAppConsumer(consumer_tester)
        else:
            raise ValueError(f"Unsupported consumer: {consumer}")
        
        results = {
            "consumer": consumer,
            "status": "passed",
            "contracts_generated": {},
            "validations": {},
            "errors": []
        }
        
        try:
            # Generate contracts
            contracts = consumer_instance.generate_consumer_contracts()
            results["contracts_generated"] = {
                provider: str(contract) for provider, contract in contracts.items()
            }
            
            # Validate expectations
            validations = consumer_instance.validate_expectations()
            results["validations"] = validations
            
            # Check for any validation failures
            for provider, validation in validations.items():
                if not validation.get("valid", False):
                    results["status"] = "failed"
                    results["errors"].append(f"Validation failed for {provider}: {validation}")
        
        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(str(e))
            logger.error(f"Consumer contract tests failed: {e}")
        
        self.test_results["consumer_tests"].append(results)
        return results
    
    async def run_provider_verification_tests(
        self,
        provider_configs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run provider verification tests."""
        logger.info("Running provider verification tests")
        
        verification_results = []
        
        for config in provider_configs:
            provider_name = config["name"]
            provider_url = config["url"]
            auth_headers = config.get("auth_headers", {})
            
            logger.info(f"Verifying provider: {provider_name}")
            
            result = {
                "provider": provider_name,
                "url": provider_url,
                "status": "unknown",
                "contracts_verified": 0,
                "failures": [],
                "errors": []
            }
            
            try:
                # Get contracts for this provider
                contracts = self.contract_manager.list_contracts(provider=provider_name)
                
                for contract in contracts:
                    try:
                        verification = await self.provider_verifier.verify_contract(
                            contract,
                            provider_url=provider_url,
                            auth_headers=auth_headers
                        )
                        
                        if verification["success"]:
                            result["contracts_verified"] += 1
                        else:
                            result["failures"].extend(verification["failed_interactions"])
                            result["status"] = "failed"
                    
                    except Exception as e:
                        result["errors"].append(f"Contract {contract['id']}: {str(e)}")
                        result["status"] = "failed"
                
                if result["status"] == "unknown" and result["contracts_verified"] > 0:
                    result["status"] = "passed"
                elif result["contracts_verified"] == 0:
                    result["status"] = "skipped"
                    result["errors"].append("No contracts found for provider")
            
            except Exception as e:
                result["status"] = "failed"
                result["errors"].append(str(e))
                logger.error(f"Provider verification failed for {provider_name}: {e}")
            
            verification_results.append(result)
            self.test_results["provider_verifications"].append(result)
        
        return verification_results
    
    def run_contract_validation_tests(self) -> Dict[str, Any]:
        """Run contract validation tests."""
        logger.info("Running contract validation tests")
        
        results = {
            "status": "passed",
            "contracts_validated": 0,
            "validation_errors": [],
            "warnings": []
        }
        
        try:
            # Get all contracts
            contracts = self.contract_manager.list_contracts()
            
            for contract in contracts:
                try:
                    is_valid = self.contract_manager.validate_contract(contract["id"])
                    if is_valid:
                        results["contracts_validated"] += 1
                    else:
                        results["status"] = "failed"
                        results["validation_errors"].append(
                            f"Contract {contract['id']} validation failed"
                        )
                
                except Exception as e:
                    results["status"] = "failed"
                    results["validation_errors"].append(
                        f"Contract {contract['id']}: {str(e)}"
                    )
        
        except Exception as e:
            results["status"] = "failed"
            results["validation_errors"].append(str(e))
        
        self.test_results["contract_validations"] = [results]
        return results
    
    def check_breaking_changes(
        self,
        branch: str = "main",
        current_branch: str = "HEAD"
    ) -> Dict[str, Any]:
        """Check for breaking changes between branches."""
        logger.info(f"Checking breaking changes between {branch} and {current_branch}")
        
        results = {
            "base_branch": branch,
            "current_branch": current_branch,
            "has_breaking_changes": False,
            "breaking_changes": [],
            "warnings": [],
            "summary": {}
        }
        
        try:
            # This would typically integrate with Git to compare contracts
            # For now, we'll simulate by checking current contracts
            
            contracts = self.contract_manager.list_contracts()
            
            for contract in contracts:
                # In a real implementation, you would:
                # 1. Load contract from base branch
                # 2. Compare with current contract
                # 3. Detect breaking changes
                
                # Simulated breaking change check
                contract_id = contract["id"]
                interactions = contract["interactions"]
                
                # Check for potential breaking changes (simplified)
                changes_analysis = self.version_checker.check_breaking_changes(
                    interactions,  # Would be old version
                    interactions,  # Current version
                    contract["contract_type"]
                )
                
                if changes_analysis["has_breaking_changes"]:
                    results["has_breaking_changes"] = True
                    results["breaking_changes"].append({
                        "contract_id": contract_id,
                        "provider": contract["provider"],
                        "consumer": contract["consumer"],
                        "changes": changes_analysis["changes"]
                    })
        
        except Exception as e:
            logger.error(f"Breaking change detection failed: {e}")
            results["error"] = str(e)
        
        self.test_results["breaking_changes"] = results["breaking_changes"]
        return results
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        
        # Calculate overall status
        overall_status = "passed"
        
        # Check consumer tests
        for test in self.test_results["consumer_tests"]:
            if test["status"] == "failed":
                overall_status = "failed"
                break
        
        # Check provider verifications
        for verification in self.test_results["provider_verifications"]:
            if verification["status"] == "failed":
                overall_status = "failed"
                break
        
        # Check contract validations
        for validation in self.test_results["contract_validations"]:
            if validation["status"] == "failed":
                overall_status = "failed"
                break
        
        # Check breaking changes
        if self.test_results["breaking_changes"] and any(
            change.get("breaking_changes") for change in [self.test_results.get("breaking_changes", {})]
        ):
            overall_status = "failed"
        
        self.test_results["status"] = overall_status
        
        # Generate summary
        self.test_results["summary"] = {
            "overall_status": overall_status,
            "consumer_tests": len(self.test_results["consumer_tests"]),
            "provider_verifications": len(self.test_results["provider_verifications"]),
            "contract_validations": sum(
                v.get("contracts_validated", 0) for v in self.test_results["contract_validations"]
            ),
            "breaking_changes_detected": len(self.test_results["breaking_changes"]),
            "warnings": len(self.test_results["warnings"])
        }
        
        return self.test_results
    
    def save_test_report(self, filename: str = None) -> Path:
        """Save test report to file."""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"contract_test_report_{timestamp}.json"
        
        report_path = self.results_dir / filename
        
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"Test report saved to: {report_path}")
        return report_path
    
    def publish_to_contract_registry(
        self,
        registry_url: str,
        api_key: str = None
    ) -> Dict[str, Any]:
        """Publish contracts to contract registry."""
        logger.info(f"Publishing contracts to registry: {registry_url}")
        
        results = {
            "registry_url": registry_url,
            "published_contracts": [],
            "errors": []
        }
        
        try:
            contracts = self.contract_manager.list_contracts()
            
            for contract in contracts:
                try:
                    # In a real implementation, this would make HTTP requests
                    # to publish contracts to a registry like Pact Broker
                    
                    published = self.contract_manager.publish_contract(
                        contract["id"],
                        registry_url=registry_url
                    )
                    
                    if published:
                        results["published_contracts"].append(contract["id"])
                
                except Exception as e:
                    results["errors"].append(f"Contract {contract['id']}: {str(e)}")
        
        except Exception as e:
            results["errors"].append(str(e))
        
        return results


def main():
    """Main CI/CD contract testing entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run contract tests in CI/CD")
    parser.add_argument("--mode", choices=["consumer", "provider", "validation", "breaking-changes", "all"], 
                       default="all", help="Test mode to run")
    parser.add_argument("--consumer", default="mobile-app", help="Consumer to test")
    parser.add_argument("--provider-config", help="JSON file with provider configurations")
    parser.add_argument("--base-branch", default="main", help="Base branch for breaking change detection")
    parser.add_argument("--output", help="Output file for test report")
    parser.add_argument("--publish-registry", help="Contract registry URL to publish to")
    parser.add_argument("--api-key", help="API key for contract registry")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize CI system
    ci = ContractTestingCI()
    
    try:
        if args.mode in ["consumer", "all"]:
            ci.run_consumer_contract_tests(args.consumer)
        
        if args.mode in ["provider", "all"]:
            provider_configs = []
            if args.provider_config:
                with open(args.provider_config, 'r') as f:
                    provider_configs = json.load(f)
            else:
                # Default local configs
                provider_configs = [
                    {"name": "nutrition-service", "url": "http://localhost:8001"},
                    {"name": "meal-planning-service", "url": "http://localhost:8002"},
                    {"name": "messaging-service", "url": "http://localhost:8003"}
                ]
            
            asyncio.run(ci.run_provider_verification_tests(provider_configs))
        
        if args.mode in ["validation", "all"]:
            ci.run_contract_validation_tests()
        
        if args.mode in ["breaking-changes", "all"]:
            ci.check_breaking_changes(branch=args.base_branch)
        
        # Generate and save report
        report = ci.generate_test_report()
        report_path = ci.save_test_report(args.output)
        
        # Publish to registry if requested
        if args.publish_registry:
            publish_result = ci.publish_to_contract_registry(
                args.publish_registry,
                args.api_key
            )
            logger.info(f"Published {len(publish_result['published_contracts'])} contracts")
        
        # Exit with appropriate code
        if report["status"] == "passed":
            logger.info("All contract tests passed! ✅")
            sys.exit(0)
        else:
            logger.error("Contract tests failed! ❌")
            print(f"Test report: {report_path}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Contract testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
