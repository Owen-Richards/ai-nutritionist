"""
Provider Verifier - Verifies that providers implement their contracts correctly.

Runs contract tests against provider implementations to ensure
they fulfill their contract obligations.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from urllib.parse import urljoin

try:
    import aiohttp
    import requests
except ImportError:
    aiohttp = None
    requests = None

from ..exceptions import ProviderVerificationError
from .schema_validator import SchemaValidator


logger = logging.getLogger(__name__)


class ProviderVerifier:
    """Verifies provider implementations against contracts."""
    
    def __init__(self, base_url: str = None):
        """
        Initialize provider verifier.
        
        Args:
            base_url: Base URL for provider service
        """
        self.base_url = base_url
        self.schema_validator = SchemaValidator()
        self._verification_results = []
    
    async def verify_contract(
        self,
        contract: Dict,
        provider_url: str = None,
        auth_headers: Dict = None
    ) -> Dict[str, Any]:
        """
        Verify provider implementation against contract.
        
        Args:
            contract: Contract definition
            provider_url: Provider service URL (overrides base_url)
            auth_headers: Authentication headers
            
        Returns:
            Verification results
        """
        provider_url = provider_url or self.base_url
        if not provider_url:
            raise ProviderVerificationError("Provider URL not specified")
        
        contract_type = contract.get("contract_type", "rest")
        
        if contract_type == "rest":
            return await self._verify_rest_contract(contract, provider_url, auth_headers)
        elif contract_type == "graphql":
            return await self._verify_graphql_contract(contract, provider_url, auth_headers)
        elif contract_type == "grpc":
            return await self._verify_grpc_contract(contract, provider_url, auth_headers)
        else:
            raise ProviderVerificationError(f"Unsupported contract type: {contract_type}")
    
    async def _verify_rest_contract(
        self,
        contract: Dict,
        provider_url: str,
        auth_headers: Dict = None
    ) -> Dict[str, Any]:
        """Verify REST API contract."""
        if not aiohttp:
            raise ProviderVerificationError("aiohttp library required for REST verification")
        
        results = {
            "contract_id": contract["id"],
            "provider": contract["provider"],
            "verified_at": datetime.utcnow().isoformat(),
            "success": True,
            "failed_interactions": [],
            "interaction_results": []
        }
        
        async with aiohttp.ClientSession() as session:
            for interaction in contract["interactions"]:
                try:
                    interaction_result = await self._verify_rest_interaction(
                        session, interaction, provider_url, auth_headers
                    )
                    results["interaction_results"].append(interaction_result)
                    
                    if not interaction_result["success"]:
                        results["success"] = False
                        results["failed_interactions"].append(interaction_result)
                        
                except Exception as e:
                    error_result = {
                        "description": interaction.get("description", "Unknown"),
                        "success": False,
                        "error": str(e),
                        "request": interaction.get("request", {}),
                        "expected_response": interaction.get("response", {})
                    }
                    results["interaction_results"].append(error_result)
                    results["failed_interactions"].append(error_result)
                    results["success"] = False
        
        if not results["success"]:
            raise ProviderVerificationError(
                f"Provider verification failed for {contract['provider']}",
                provider=contract["provider"],
                failed_interactions=results["failed_interactions"]
            )
        
        return results
    
    async def _verify_rest_interaction(
        self,
        session: Any,  # aiohttp.ClientSession
        interaction: Dict,
        provider_url: str,
        auth_headers: Dict = None
    ) -> Dict[str, Any]:
        """Verify a single REST interaction."""
        request = interaction["request"]
        expected_response = interaction["response"]
        
        # Build request URL
        url = urljoin(provider_url, request["path"])
        
        # Prepare headers
        headers = request.get("headers", {})
        if auth_headers:
            headers.update(auth_headers)
        
        # Prepare request data
        method = request["method"].upper()
        data = request.get("body")
        params = request.get("query_params", {})
        
        # Make request
        async with session.request(
            method=method,
            url=url,
            headers=headers,
            json=data if data else None,
            params=params
        ) as response:
            
            # Get response data
            response_data = {}
            try:
                response_data = await response.json()
            except:
                response_data = {"text": await response.text()}
            
            # Verify status code
            expected_status = expected_response["status"]
            actual_status = response.status
            
            status_match = actual_status == expected_status
            
            # Verify response schema if specified
            schema_match = True
            schema_errors = []
            
            if "schema" in expected_response:
                try:
                    self.schema_validator.validate_json_schema(
                        response_data,
                        expected_response["schema"]
                    )
                except Exception as e:
                    schema_match = False
                    schema_errors.append(str(e))
            
            # Verify response headers if specified
            headers_match = True
            header_errors = []
            
            if "headers" in expected_response:
                for header, expected_value in expected_response["headers"].items():
                    actual_value = response.headers.get(header)
                    if actual_value != expected_value:
                        headers_match = False
                        header_errors.append(
                            f"Header {header}: expected {expected_value}, got {actual_value}"
                        )
            
            success = status_match and schema_match and headers_match
            
            return {
                "description": interaction.get("description", "Unknown"),
                "success": success,
                "request": {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "body": data,
                    "params": params
                },
                "expected_response": expected_response,
                "actual_response": {
                    "status": actual_status,
                    "headers": dict(response.headers),
                    "body": response_data
                },
                "verification_details": {
                    "status_match": status_match,
                    "schema_match": schema_match,
                    "headers_match": headers_match,
                    "schema_errors": schema_errors,
                    "header_errors": header_errors
                }
            }
    
    async def _verify_graphql_contract(
        self,
        contract: Dict,
        provider_url: str,
        auth_headers: Dict = None
    ) -> Dict[str, Any]:
        """Verify GraphQL contract."""
        if not aiohttp:
            raise ProviderVerificationError("aiohttp library required for GraphQL verification")
        
        results = {
            "contract_id": contract["id"],
            "provider": contract["provider"],
            "verified_at": datetime.utcnow().isoformat(),
            "success": True,
            "failed_interactions": [],
            "interaction_results": []
        }
        
        async with aiohttp.ClientSession() as session:
            for interaction in contract["interactions"]:
                try:
                    interaction_result = await self._verify_graphql_interaction(
                        session, interaction, provider_url, auth_headers
                    )
                    results["interaction_results"].append(interaction_result)
                    
                    if not interaction_result["success"]:
                        results["success"] = False
                        results["failed_interactions"].append(interaction_result)
                        
                except Exception as e:
                    error_result = {
                        "description": interaction.get("description", "Unknown"),
                        "success": False,
                        "error": str(e)
                    }
                    results["interaction_results"].append(error_result)
                    results["failed_interactions"].append(error_result)
                    results["success"] = False
        
        return results
    
    async def _verify_graphql_interaction(
        self,
        session: Any,  # aiohttp.ClientSession
        interaction: Dict,
        provider_url: str,
        auth_headers: Dict = None
    ) -> Dict[str, Any]:
        """Verify a single GraphQL interaction."""
        query = interaction["query"]
        expected_response = interaction["response"]
        variables = interaction.get("variables", {})
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if auth_headers:
            headers.update(auth_headers)
        
        # Prepare GraphQL request
        graphql_request = {
            "query": query,
            "variables": variables
        }
        
        # Make request
        async with session.post(
            url=provider_url,
            headers=headers,
            json=graphql_request
        ) as response:
            
            response_data = await response.json()
            
            # Verify response structure
            success = True
            errors = []
            
            # Check for GraphQL errors
            if "errors" in response_data:
                if not expected_response.get("errors"):
                    success = False
                    errors.append("Unexpected GraphQL errors in response")
            
            # Verify data if expected
            if "data" in expected_response:
                if "data" not in response_data:
                    success = False
                    errors.append("Missing data in GraphQL response")
                else:
                    # Validate response schema if specified
                    if "schema" in expected_response:
                        try:
                            self.schema_validator.validate_json_schema(
                                response_data["data"],
                                expected_response["schema"]
                            )
                        except Exception as e:
                            success = False
                            errors.append(f"Schema validation failed: {str(e)}")
            
            return {
                "description": interaction.get("description", "Unknown"),
                "success": success,
                "query": query,
                "variables": variables,
                "expected_response": expected_response,
                "actual_response": response_data,
                "errors": errors
            }
    
    async def _verify_grpc_contract(
        self,
        contract: Dict,
        provider_url: str,
        auth_headers: Dict = None
    ) -> Dict[str, Any]:
        """Verify gRPC contract."""
        # gRPC verification would require grpcio client
        # This is a placeholder implementation
        
        results = {
            "contract_id": contract["id"],
            "provider": contract["provider"],
            "verified_at": datetime.utcnow().isoformat(),
            "success": True,
            "message": "gRPC verification not yet implemented",
            "interaction_results": []
        }
        
        logger.warning("gRPC contract verification not yet implemented")
        return results
    
    def verify_contract_sync(
        self,
        contract: Dict,
        provider_url: str = None,
        auth_headers: Dict = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for contract verification.
        
        Args:
            contract: Contract definition
            provider_url: Provider service URL
            auth_headers: Authentication headers
            
        Returns:
            Verification results
        """
        return asyncio.run(self.verify_contract(contract, provider_url, auth_headers))
    
    def get_verification_history(self) -> List[Dict]:
        """Get history of verification results."""
        return self._verification_results.copy()
    
    def clear_verification_history(self) -> None:
        """Clear verification history."""
        self._verification_results.clear()
