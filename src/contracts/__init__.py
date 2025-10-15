"""
Contract Testing Framework

A comprehensive contract testing system for the AI Nutritionist application
that provides consumer-driven contracts, schema validation, and provider verification.

Features:
- Consumer-driven contracts using Pact
- REST API contract validation
- AsyncAPI for event-driven architecture
- GraphQL schema validation
- gRPC contract testing
- Automated CI/CD integration
- Breaking change detection
- Version compatibility checks
"""

from .core.contract_manager import ContractManager
from .core.schema_validator import SchemaValidator
from .core.provider_verifier import ProviderVerifier
from .core.consumer_tester import ConsumerTester
from .core.version_compatibility import VersionCompatibilityChecker
from .exceptions import ContractValidationError, ProviderVerificationError, ConsumerTestError

__all__ = [
    "ContractManager",
    "SchemaValidator", 
    "ProviderVerifier",
    "ConsumerTester",
    "VersionCompatibilityChecker",
    "ContractValidationError",
    "ProviderVerificationError", 
    "ConsumerTestError"
]

__version__ = "1.0.0"
