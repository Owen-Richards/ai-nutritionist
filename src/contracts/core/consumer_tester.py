"""
Consumer Tester - Tests consumer expectations and generates contracts.

Helps consumers define their expectations of providers and generates
Pact contracts from consumer tests.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
from pathlib import Path

try:
    from pact import Consumer, Provider, Like, EachLike, Term
    PACT_AVAILABLE = True
except ImportError:
    Consumer = Provider = Like = EachLike = Term = None
    PACT_AVAILABLE = False

from ..exceptions import ConsumerTestError
from .schema_validator import SchemaValidator


logger = logging.getLogger(__name__)


class ConsumerTester:
    """Tests consumer expectations and generates contracts."""
    
    def __init__(self, consumer_name: str, pact_dir: Union[str, Path] = None):
        """
        Initialize consumer tester.
        
        Args:
            consumer_name: Name of the consumer service
            pact_dir: Directory to store Pact files (defaults to ./pacts)
        """
        self.consumer_name = consumer_name
        self.pact_dir = Path(pact_dir or "pacts")
        self.pact_dir.mkdir(exist_ok=True)
        
        self.schema_validator = SchemaValidator()
        self._expectations = []
        self._pact_consumers = {}
    
    def create_pact_consumer(
        self,
        provider_name: str,
        host_name: str = "localhost",
        port: int = 1234,
        version: str = "1.0.0"
    ) -> Any:
        """
        Create a Pact consumer for testing against a provider.
        
        Args:
            provider_name: Name of the provider service
            host_name: Mock server hostname
            port: Mock server port
            version: Consumer version
            
        Returns:
            Pact consumer instance
        """
        if not PACT_AVAILABLE:
            raise ConsumerTestError("pact-python library not available")
        
        pact = Consumer(self.consumer_name, version=version).has_pact_with(
            Provider(provider_name),
            host_name=host_name,
            port=port,
            pact_dir=str(self.pact_dir)
        )
        
        self._pact_consumers[provider_name] = pact
        return pact
    
    def define_rest_expectation(
        self,
        provider_name: str,
        description: str,
        method: str,
        path: str,
        request_body: Dict = None,
        request_headers: Dict = None,
        response_status: int = 200,
        response_body: Dict = None,
        response_headers: Dict = None,
        query_params: Dict = None
    ) -> Dict[str, Any]:
        """
        Define REST API expectation.
        
        Args:
            provider_name: Provider service name
            description: Interaction description
            method: HTTP method
            path: Request path
            request_body: Request body
            request_headers: Request headers
            response_status: Expected response status
            response_body: Expected response body
            response_headers: Expected response headers
            query_params: Query parameters
            
        Returns:
            Expectation definition
        """
        expectation = {
            "provider": provider_name,
            "description": description,
            "contract_type": "rest",
            "request": {
                "method": method.upper(),
                "path": path,
                "headers": request_headers or {},
                "body": request_body,
                "query_params": query_params or {}
            },
            "response": {
                "status": response_status,
                "headers": response_headers or {},
                "body": response_body
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._expectations.append(expectation)
        logger.info(f"Defined REST expectation: {description}")
        return expectation
    
    def define_graphql_expectation(
        self,
        provider_name: str,
        description: str,
        query: str,
        variables: Dict = None,
        response_data: Dict = None,
        response_errors: List = None
    ) -> Dict[str, Any]:
        """
        Define GraphQL expectation.
        
        Args:
            provider_name: Provider service name
            description: Interaction description
            query: GraphQL query
            variables: Query variables
            response_data: Expected response data
            response_errors: Expected response errors
            
        Returns:
            Expectation definition
        """
        expectation = {
            "provider": provider_name,
            "description": description,
            "contract_type": "graphql",
            "query": query,
            "variables": variables or {},
            "response": {
                "data": response_data,
                "errors": response_errors
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._expectations.append(expectation)
        logger.info(f"Defined GraphQL expectation: {description}")
        return expectation
    
    def define_grpc_expectation(
        self,
        provider_name: str,
        description: str,
        service: str,
        method: str,
        request_message: Dict,
        response_message: Dict
    ) -> Dict[str, Any]:
        """
        Define gRPC expectation.
        
        Args:
            provider_name: Provider service name
            description: Interaction description
            service: gRPC service name
            method: gRPC method name
            request_message: Request message
            response_message: Response message
            
        Returns:
            Expectation definition
        """
        expectation = {
            "provider": provider_name,
            "description": description,
            "contract_type": "grpc",
            "service": service,
            "method": method,
            "request": request_message,
            "response": response_message,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._expectations.append(expectation)
        logger.info(f"Defined gRPC expectation: {description}")
        return expectation
    
    def define_event_expectation(
        self,
        provider_name: str,
        description: str,
        event_type: str,
        channel: str,
        message_schema: Dict,
        message_example: Dict = None
    ) -> Dict[str, Any]:
        """
        Define event-driven expectation.
        
        Args:
            provider_name: Provider service name
            description: Interaction description
            event_type: Event type
            channel: Message channel/topic
            message_schema: Message schema
            message_example: Example message
            
        Returns:
            Expectation definition
        """
        expectation = {
            "provider": provider_name,
            "description": description,
            "contract_type": "event",
            "event_type": event_type,
            "channel": channel,
            "schema": message_schema,
            "example": message_example,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._expectations.append(expectation)
        logger.info(f"Defined event expectation: {description}")
        return expectation
    
    def run_consumer_test(
        self,
        test_function: Callable,
        provider_name: str,
        setup_expectations: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run consumer test with expectations.
        
        Args:
            test_function: Test function to run
            provider_name: Provider service name
            setup_expectations: Expectations to set up before test
            
        Returns:
            Test results
        """
        if provider_name not in self._pact_consumers:
            raise ConsumerTestError(f"No Pact consumer configured for provider: {provider_name}")
        
        pact = self._pact_consumers[provider_name]
        
        # Set up expectations
        if setup_expectations:
            for expectation in setup_expectations:
                self._setup_pact_expectation(pact, expectation)
        
        # Run test
        try:
            with pact:
                test_result = test_function()
            
            # Generate Pact file
            pact.write_pact()
            
            return {
                "success": True,
                "provider": provider_name,
                "test_result": test_result,
                "pact_file": f"{self.pact_dir}/{self.consumer_name}-{provider_name}.json"
            }
            
        except Exception as e:
            raise ConsumerTestError(
                f"Consumer test failed: {str(e)}",
                consumer=self.consumer_name,
                missing_expectations=[str(e)]
            )
    
    def generate_contract_from_expectations(self, provider_name: str) -> Dict[str, Any]:
        """
        Generate contract from defined expectations.
        
        Args:
            provider_name: Provider service name
            
        Returns:
            Generated contract
        """
        provider_expectations = [
            exp for exp in self._expectations 
            if exp["provider"] == provider_name
        ]
        
        if not provider_expectations:
            raise ConsumerTestError(
                f"No expectations defined for provider: {provider_name}",
                consumer=self.consumer_name
            )
        
        contract = {
            "consumer": self.consumer_name,
            "provider": provider_name,
            "interactions": [],
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "expectations_count": len(provider_expectations)
            }
        }
        
        # Convert expectations to contract interactions
        for expectation in provider_expectations:
            interaction = self._expectation_to_interaction(expectation)
            contract["interactions"].append(interaction)
        
        # Save contract
        contract_file = self.pact_dir / f"{self.consumer_name}-{provider_name}-contract.json"
        with open(contract_file, 'w') as f:
            json.dump(contract, f, indent=2)
        
        logger.info(f"Generated contract: {contract_file}")
        return contract
    
    def validate_consumer_expectations(self, provider_name: str) -> Dict[str, Any]:
        """
        Validate consumer expectations for completeness.
        
        Args:
            provider_name: Provider service name
            
        Returns:
            Validation results
        """
        provider_expectations = [
            exp for exp in self._expectations 
            if exp["provider"] == provider_name
        ]
        
        validation_results = {
            "provider": provider_name,
            "valid": True,
            "issues": [],
            "expectations_validated": len(provider_expectations)
        }
        
        for expectation in provider_expectations:
            issues = self._validate_single_expectation(expectation)
            if issues:
                validation_results["valid"] = False
                validation_results["issues"].extend(issues)
        
        if not validation_results["valid"]:
            raise ConsumerTestError(
                f"Consumer expectations validation failed",
                consumer=self.consumer_name,
                missing_expectations=validation_results["issues"]
            )
        
        return validation_results
    
    def get_expectations(self, provider_name: str = None) -> List[Dict]:
        """
        Get defined expectations.
        
        Args:
            provider_name: Filter by provider (optional)
            
        Returns:
            List of expectations
        """
        if provider_name:
            return [exp for exp in self._expectations if exp["provider"] == provider_name]
        return self._expectations.copy()
    
    def clear_expectations(self, provider_name: str = None) -> None:
        """
        Clear expectations.
        
        Args:
            provider_name: Clear only for specific provider (optional)
        """
        if provider_name:
            self._expectations = [
                exp for exp in self._expectations 
                if exp["provider"] != provider_name
            ]
        else:
            self._expectations.clear()
    
    def _setup_pact_expectation(self, pact: Any, expectation: Dict) -> None:
        """Set up Pact expectation."""
        if not PACT_AVAILABLE:
            return
        
        if expectation["contract_type"] == "rest":
            request = expectation["request"]
            response = expectation["response"]
            
            pact.given(expectation["description"]).upon_receiving(
                expectation["description"]
            ).with_request(
                method=request["method"],
                path=request["path"],
                headers=request.get("headers"),
                body=request.get("body"),
                query=request.get("query_params")
            ).will_respond_with(
                status=response["status"],
                headers=response.get("headers"),
                body=response.get("body")
            )
    
    def _expectation_to_interaction(self, expectation: Dict) -> Dict[str, Any]:
        """Convert expectation to contract interaction."""
        interaction = {
            "description": expectation["description"],
            "contract_type": expectation["contract_type"]
        }
        
        if expectation["contract_type"] == "rest":
            interaction.update({
                "request": expectation["request"],
                "response": expectation["response"]
            })
        elif expectation["contract_type"] == "graphql":
            interaction.update({
                "query": expectation["query"],
                "variables": expectation["variables"],
                "response": expectation["response"]
            })
        elif expectation["contract_type"] == "grpc":
            interaction.update({
                "service": expectation["service"],
                "method": expectation["method"],
                "request": expectation["request"],
                "response": expectation["response"]
            })
        elif expectation["contract_type"] == "event":
            interaction.update({
                "event_type": expectation["event_type"],
                "channel": expectation["channel"],
                "schema": expectation["schema"],
                "example": expectation.get("example")
            })
        
        return interaction
    
    def _validate_single_expectation(self, expectation: Dict) -> List[str]:
        """Validate a single expectation."""
        issues = []
        
        # Check required fields
        required_fields = ["provider", "description", "contract_type"]
        for field in required_fields:
            if field not in expectation:
                issues.append(f"Missing required field: {field}")
        
        # Validate based on contract type
        contract_type = expectation.get("contract_type")
        
        if contract_type == "rest":
            if "request" not in expectation:
                issues.append("REST expectation missing request")
            elif "method" not in expectation["request"] or "path" not in expectation["request"]:
                issues.append("REST request must have method and path")
            
            if "response" not in expectation:
                issues.append("REST expectation missing response")
            elif "status" not in expectation["response"]:
                issues.append("REST response must have status")
        
        elif contract_type == "graphql":
            if "query" not in expectation:
                issues.append("GraphQL expectation missing query")
            if "response" not in expectation:
                issues.append("GraphQL expectation missing response")
        
        elif contract_type == "grpc":
            required = ["service", "method", "request", "response"]
            for field in required:
                if field not in expectation:
                    issues.append(f"gRPC expectation missing: {field}")
        
        elif contract_type == "event":
            required = ["event_type", "channel", "schema"]
            for field in required:
                if field not in expectation:
                    issues.append(f"Event expectation missing: {field}")
        
        return issues
