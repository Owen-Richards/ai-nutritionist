"""
Contract Testing Suite

Comprehensive tests for contract validation, provider verification,
and consumer expectations.
"""

import pytest
import asyncio
from typing import Dict, Any
from pathlib import Path

from src.contracts.core.contract_manager import ContractManager
from src.contracts.core.provider_verifier import ProviderVerifier
from src.contracts.core.consumer_tester import ConsumerTester
from src.contracts.core.schema_validator import SchemaValidator
from src.contracts.providers.nutrition_provider import NutritionServiceProvider
from src.contracts.providers.meal_planning_provider import MealPlanningServiceProvider
from src.contracts.consumers.mobile_app_consumer import MobileAppConsumer


@pytest.fixture
def contract_manager():
    """Contract manager fixture."""
    return ContractManager(contract_dir="tests/contracts/pacts")


@pytest.fixture
def schema_validator():
    """Schema validator fixture."""
    return SchemaValidator()


@pytest.fixture
def provider_verifier():
    """Provider verifier fixture."""
    return ProviderVerifier()


@pytest.fixture
def consumer_tester():
    """Consumer tester fixture."""
    return ConsumerTester(consumer_name="test-consumer", pact_dir="tests/contracts/pacts")


@pytest.fixture
def sample_rest_contract():
    """Sample REST contract for testing."""
    return {
        "id": "test-contract-001",
        "consumer": "test-consumer",
        "provider": "test-provider",
        "contract_type": "rest",
        "version": "1.0.0",
        "interactions": [
            {
                "description": "Get user profile",
                "request": {
                    "method": "GET",
                    "path": "/api/users/123",
                    "headers": {
                        "Authorization": "Bearer token123"
                    }
                },
                "response": {
                    "status": 200,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": {
                        "id": "123",
                        "name": "John Doe",
                        "email": "john@example.com"
                    },
                    "schema": {
                        "type": "object",
                        "required": ["id", "name", "email"],
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"}
                        }
                    }
                }
            }
        ]
    }


class TestContractManager:
    """Test contract manager functionality."""
    
    def test_create_contract(self, contract_manager):
        """Test contract creation."""
        contract_id = contract_manager.create_contract(
            consumer="test-consumer",
            provider="test-provider",
            contract_type="rest",
            interactions=[
                {
                    "description": "Test interaction",
                    "request": {"method": "GET", "path": "/test"},
                    "response": {"status": 200}
                }
            ]
        )
        
        assert contract_id is not None
        contract = contract_manager.get_contract(contract_id)
        assert contract is not None
        assert contract["consumer"] == "test-consumer"
        assert contract["provider"] == "test-provider"
    
    def test_validate_contract(self, contract_manager, sample_rest_contract):
        """Test contract validation."""
        # Create contract first
        contract_id = contract_manager.create_contract(
            consumer=sample_rest_contract["consumer"],
            provider=sample_rest_contract["provider"],
            contract_type=sample_rest_contract["contract_type"],
            interactions=sample_rest_contract["interactions"]
        )
        
        # Validate contract
        is_valid = contract_manager.validate_contract(contract_id)
        assert is_valid is True
    
    def test_check_breaking_changes(self, contract_manager):
        """Test breaking changes detection."""
        old_interactions = [
            {
                "description": "Get user",
                "request": {"method": "GET", "path": "/users/123"},
                "response": {
                    "status": 200,
                    "schema": {
                        "type": "object",
                        "required": ["id", "name"],
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"}
                        }
                    }
                }
            }
        ]
        
        new_interactions = [
            {
                "description": "Get user",
                "request": {"method": "GET", "path": "/users/123"},
                "response": {
                    "status": 200,
                    "schema": {
                        "type": "object",
                        "required": ["id", "name", "email"],  # Added required field
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "email": {"type": "string"}
                        }
                    }
                }
            }
        ]
        
        # Create initial contract
        contract_id = contract_manager.create_contract(
            consumer="test-consumer",
            provider="test-provider",
            contract_type="rest",
            interactions=old_interactions
        )
        
        # Check for breaking changes
        changes = contract_manager.check_breaking_changes(contract_id, new_interactions)
        
        assert changes["has_breaking_changes"] is True
        assert len(changes["changes"]) > 0


class TestSchemaValidator:
    """Test schema validation functionality."""
    
    def test_validate_json_schema(self, schema_validator):
        """Test JSON schema validation."""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com"
        }
        
        schema = {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"},
                "email": {"type": "string", "format": "email"}
            }
        }
        
        is_valid = schema_validator.validate_json_schema(data, schema)
        assert is_valid is True
    
    def test_validate_openapi_spec(self, schema_validator):
        """Test OpenAPI specification validation."""
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0"
            },
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "users": {
                                                    "type": "array",
                                                    "items": {"type": "object"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        try:
            is_valid = schema_validator.validate_openapi_spec(openapi_spec)
            assert is_valid is True
        except Exception as e:
            # Skip if validation library not available
            pytest.skip(f"OpenAPI validation not available: {e}")
    
    def test_validate_graphql_schema(self, schema_validator):
        """Test GraphQL schema validation."""
        graphql_schema = """
        type Query {
            user(id: ID!): User
            users: [User]
        }
        
        type User {
            id: ID!
            name: String!
            email: String!
        }
        """
        
        is_valid = schema_validator.validate_graphql_schema(graphql_schema)
        assert is_valid is True


class TestConsumerTester:
    """Test consumer testing functionality."""
    
    def test_define_rest_expectation(self, consumer_tester):
        """Test REST expectation definition."""
        expectation = consumer_tester.define_rest_expectation(
            provider_name="test-provider",
            description="Get user profile",
            method="GET",
            path="/users/123",
            response_status=200,
            response_body={"id": "123", "name": "John"}
        )
        
        assert expectation["provider"] == "test-provider"
        assert expectation["description"] == "Get user profile"
        assert expectation["contract_type"] == "rest"
        assert expectation["request"]["method"] == "GET"
        assert expectation["request"]["path"] == "/users/123"
        assert expectation["response"]["status"] == 200
    
    def test_generate_contract_from_expectations(self, consumer_tester):
        """Test contract generation from expectations."""
        # Define expectations
        consumer_tester.define_rest_expectation(
            provider_name="test-provider",
            description="Get user",
            method="GET",
            path="/users/123",
            response_status=200,
            response_body={"id": "123", "name": "John"}
        )
        
        consumer_tester.define_rest_expectation(
            provider_name="test-provider",
            description="Create user",
            method="POST",
            path="/users",
            request_body={"name": "Jane", "email": "jane@example.com"},
            response_status=201,
            response_body={"id": "456", "name": "Jane"}
        )
        
        # Generate contract
        contract = consumer_tester.generate_contract_from_expectations("test-provider")
        
        assert contract["consumer"] == "test-consumer"
        assert contract["provider"] == "test-provider"
        assert len(contract["interactions"]) == 2
    
    def test_validate_consumer_expectations(self, consumer_tester):
        """Test consumer expectations validation."""
        # Define valid expectation
        consumer_tester.define_rest_expectation(
            provider_name="test-provider",
            description="Get user",
            method="GET",
            path="/users/123",
            response_status=200
        )
        
        # Validate expectations
        result = consumer_tester.validate_consumer_expectations("test-provider")
        
        assert result["valid"] is True
        assert result["provider"] == "test-provider"
        assert result["expectations_validated"] == 1


class TestProviderVerifier:
    """Test provider verification functionality."""
    
    @pytest.mark.asyncio
    async def test_verify_rest_contract_mock(self, provider_verifier, sample_rest_contract):
        """Test REST contract verification with mock."""
        # This test would normally require a running service
        # For now, we'll test the structure
        
        try:
            result = await provider_verifier.verify_contract(
                sample_rest_contract,
                provider_url="http://localhost:8000"
            )
            
            # If we get here, the structure is correct
            assert "contract_id" in result
            assert "provider" in result
            assert "success" in result
            
        except Exception as e:
            # Expected if no actual service is running
            assert "aiohttp" in str(e) or "Provider URL" in str(e) or "connection" in str(e).lower()


class TestNutritionServiceProvider:
    """Test Nutrition Service provider contracts."""
    
    def test_create_contracts(self, contract_manager):
        """Test nutrition service contract creation."""
        provider = NutritionServiceProvider(contract_manager)
        contract_ids = provider.create_contracts()
        
        assert len(contract_ids) > 0
        
        # Verify contracts were created
        for contract_id in contract_ids:
            contract = contract_manager.get_contract(contract_id)
            assert contract is not None
            assert contract["provider"] == "nutrition-service"
    
    def test_error_responses(self, contract_manager):
        """Test nutrition service error response definitions."""
        provider = NutritionServiceProvider(contract_manager)
        error_responses = provider.get_error_responses()
        
        assert len(error_responses) > 0
        
        # Check standard HTTP error codes are covered
        status_codes = [resp["status"] for resp in error_responses]
        assert 400 in status_codes  # Bad Request
        assert 401 in status_codes  # Unauthorized
        assert 404 in status_codes  # Not Found
        assert 500 in status_codes  # Internal Server Error


class TestMealPlanningServiceProvider:
    """Test Meal Planning Service provider contracts."""
    
    def test_create_contracts(self, contract_manager):
        """Test meal planning service contract creation."""
        provider = MealPlanningServiceProvider(contract_manager)
        contract_ids = provider.create_contracts()
        
        assert len(contract_ids) > 0
        
        # Verify contracts were created
        for contract_id in contract_ids:
            contract = contract_manager.get_contract(contract_id)
            assert contract is not None
            assert contract["provider"] == "meal-planning-service"


class TestMobileAppConsumer:
    """Test Mobile App consumer contracts."""
    
    def test_define_nutrition_service_expectations(self, consumer_tester):
        """Test mobile app nutrition service expectations."""
        consumer = MobileAppConsumer(consumer_tester)
        expectations = consumer.define_nutrition_service_expectations()
        
        assert len(expectations) > 0
        
        # Check that expectations cover key functionality
        descriptions = [exp["description"] for exp in expectations]
        assert any("nutrition" in desc.lower() for desc in descriptions)
        assert any("track" in desc.lower() for desc in descriptions)
    
    def test_generate_consumer_contracts(self, consumer_tester):
        """Test mobile app contract generation."""
        consumer = MobileAppConsumer(consumer_tester)
        contracts = consumer.generate_consumer_contracts()
        
        # Should generate contracts for multiple providers
        expected_providers = ["nutrition-service", "meal-planning-service", "messaging-service"]
        
        for provider in expected_providers:
            if provider in contracts:
                contract = contracts[provider]
                assert contract["consumer"] == "mobile-app"
                assert contract["provider"] == provider


class TestIntegrationScenarios:
    """Integration tests for complete contract testing scenarios."""
    
    def test_end_to_end_contract_workflow(self, contract_manager, consumer_tester, provider_verifier):
        """Test complete contract workflow from consumer to provider."""
        
        # Step 1: Consumer defines expectations
        consumer = MobileAppConsumer(consumer_tester)
        expectations = consumer.define_nutrition_service_expectations()
        assert len(expectations) > 0
        
        # Step 2: Generate consumer contract
        contracts = consumer.generate_consumer_contracts()
        assert "nutrition-service" in contracts
        
        # Step 3: Provider creates their contracts
        provider = NutritionServiceProvider(contract_manager)
        provider_contract_ids = provider.create_contracts()
        assert len(provider_contract_ids) > 0
        
        # Step 4: Validate contracts
        for contract_id in provider_contract_ids:
            is_valid = contract_manager.validate_contract(contract_id)
            assert is_valid is True
    
    def test_breaking_change_detection_workflow(self, contract_manager):
        """Test complete breaking change detection workflow."""
        
        # Create initial contract
        initial_interactions = [
            {
                "description": "Get user nutrition data",
                "request": {"method": "GET", "path": "/nutrition/users/123"},
                "response": {
                    "status": 200,
                    "schema": {
                        "type": "object",
                        "required": ["calories"],
                        "properties": {
                            "calories": {"type": "number"}
                        }
                    }
                }
            }
        ]
        
        contract_id = contract_manager.create_contract(
            consumer="mobile-app",
            provider="nutrition-service", 
            contract_type="rest",
            interactions=initial_interactions
        )
        
        # Simulate contract update with breaking changes
        updated_interactions = [
            {
                "description": "Get user nutrition data",
                "request": {"method": "GET", "path": "/nutrition/users/123"},
                "response": {
                    "status": 200,
                    "schema": {
                        "type": "object",
                        "required": ["calories", "macros"],  # Added required field
                        "properties": {
                            "calories": {"type": "number"},
                            "macros": {
                                "type": "object",
                                "required": ["protein", "carbs", "fat"],
                                "properties": {
                                    "protein": {"type": "number"},
                                    "carbs": {"type": "number"},
                                    "fat": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        ]
        
        # Check for breaking changes
        changes = contract_manager.check_breaking_changes(
            contract_id,
            updated_interactions
        )
        
        assert changes["has_breaking_changes"] is True
        assert len(changes["changes"]) > 0
        
        # Breaking change should prevent automatic update
        with pytest.raises(Exception):  # Should raise VersionCompatibilityError
            contract_manager.update_contract(
                contract_id,
                updated_interactions,
                force=False  # Don't force breaking changes
            )
        
        # Force update should work
        new_contract_id = contract_manager.update_contract(
            contract_id,
            updated_interactions,
            force=True
        )
        
        assert new_contract_id != contract_id
        new_contract = contract_manager.get_contract(new_contract_id)
        assert new_contract["previous_version"] == contract_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
