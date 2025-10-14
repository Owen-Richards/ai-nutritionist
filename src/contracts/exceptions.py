"""
Contract testing exceptions.
"""


class ContractTestingError(Exception):
    """Base exception for contract testing errors."""
    pass


class ContractValidationError(ContractTestingError):
    """Raised when contract validation fails."""
    
    def __init__(self, message: str, contract_type: str = None, details: dict = None):
        super().__init__(message)
        self.contract_type = contract_type
        self.details = details or {}


class ProviderVerificationError(ContractTestingError):
    """Raised when provider verification fails."""
    
    def __init__(self, message: str, provider: str = None, failed_interactions: list = None):
        super().__init__(message)
        self.provider = provider
        self.failed_interactions = failed_interactions or []


class ConsumerTestError(ContractTestingError):
    """Raised when consumer tests fail."""
    
    def __init__(self, message: str, consumer: str = None, missing_expectations: list = None):
        super().__init__(message)
        self.consumer = consumer
        self.missing_expectations = missing_expectations or []


class SchemaValidationError(ContractTestingError):
    """Raised when schema validation fails."""
    
    def __init__(self, message: str, schema_type: str = None, validation_errors: list = None):
        super().__init__(message)
        self.schema_type = schema_type
        self.validation_errors = validation_errors or []


class VersionCompatibilityError(ContractTestingError):
    """Raised when version compatibility checks fail."""
    
    def __init__(self, message: str, version_from: str = None, version_to: str = None, breaking_changes: list = None):
        super().__init__(message)
        self.version_from = version_from
        self.version_to = version_to
        self.breaking_changes = breaking_changes or []
