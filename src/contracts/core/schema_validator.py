"""
Schema Validator - Validates API schemas and data formats.

Supports validation for:
- JSON Schema
- OpenAPI specifications
- AsyncAPI specifications  
- GraphQL schemas
- Protocol Buffers
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    jsonschema = None
    ValidationError = Exception

try:
    from openapi_spec_validator import validate_spec
    from openapi_spec_validator.exceptions import OpenAPIValidationError
except ImportError:
    validate_spec = None
    OpenAPIValidationError = Exception

try:
    import yaml
except ImportError:
    yaml = None

from ..exceptions import SchemaValidationError


logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates various schema formats used in contract testing."""
    
    def __init__(self):
        """Initialize schema validator."""
        self._check_dependencies()
    
    def validate_json_schema(self, data: Dict, schema: Dict) -> bool:
        """
        Validate data against JSON schema.
        
        Args:
            data: Data to validate
            schema: JSON schema
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        if not jsonschema:
            raise SchemaValidationError("jsonschema library not available")
        
        try:
            validate(instance=data, schema=schema)
            return True
        except ValidationError as e:
            raise SchemaValidationError(
                f"JSON schema validation failed: {e.message}",
                schema_type="json_schema",
                validation_errors=[str(e)]
            )
    
    def validate_openapi_spec(self, spec: Union[Dict, str, Path]) -> bool:
        """
        Validate OpenAPI specification.
        
        Args:
            spec: OpenAPI spec as dict, JSON string, or file path
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        if not validate_spec:
            raise SchemaValidationError("openapi-spec-validator library not available")
        
        # Convert spec to dict if needed
        if isinstance(spec, (str, Path)):
            spec_dict = self._load_spec_file(spec)
        else:
            spec_dict = spec
        
        try:
            validate_spec(spec_dict)
            return True
        except OpenAPIValidationError as e:
            raise SchemaValidationError(
                f"OpenAPI validation failed: {str(e)}",
                schema_type="openapi",
                validation_errors=[str(e)]
            )
    
    def validate_asyncapi_spec(self, spec: Union[Dict, str, Path]) -> bool:
        """
        Validate AsyncAPI specification.
        
        Args:
            spec: AsyncAPI spec as dict, JSON string, or file path
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        # Convert spec to dict if needed
        if isinstance(spec, (str, Path)):
            spec_dict = self._load_spec_file(spec)
        else:
            spec_dict = spec
        
        # Basic AsyncAPI validation
        required_fields = ["asyncapi", "info", "channels"]
        missing_fields = []
        
        for field in required_fields:
            if field not in spec_dict:
                missing_fields.append(field)
        
        if missing_fields:
            raise SchemaValidationError(
                f"AsyncAPI spec missing required fields: {missing_fields}",
                schema_type="asyncapi",
                validation_errors=missing_fields
            )
        
        # Validate AsyncAPI version
        version = spec_dict.get("asyncapi", "")
        if not version.startswith(("2.", "3.")):
            raise SchemaValidationError(
                f"Unsupported AsyncAPI version: {version}",
                schema_type="asyncapi"
            )
        
        return True
    
    def validate_graphql_schema(self, schema: str) -> bool:
        """
        Validate GraphQL schema.
        
        Args:
            schema: GraphQL schema string
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        try:
            # Basic GraphQL schema validation
            # Check for required elements
            if "type Query" not in schema and "type Mutation" not in schema and "type Subscription" not in schema:
                raise SchemaValidationError(
                    "GraphQL schema must contain at least one root type (Query, Mutation, or Subscription)",
                    schema_type="graphql"
                )
            
            # Check for balanced braces
            open_braces = schema.count('{')
            close_braces = schema.count('}')
            if open_braces != close_braces:
                raise SchemaValidationError(
                    f"Unbalanced braces in GraphQL schema: {open_braces} open, {close_braces} close",
                    schema_type="graphql"
                )
            
            return True
            
        except Exception as e:
            raise SchemaValidationError(
                f"GraphQL schema validation failed: {str(e)}",
                schema_type="graphql",
                validation_errors=[str(e)]
            )
    
    def validate_protobuf_schema(self, proto_content: str) -> bool:
        """
        Validate Protocol Buffers schema.
        
        Args:
            proto_content: .proto file content
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        try:
            # Basic proto file validation
            if "syntax" not in proto_content:
                raise SchemaValidationError(
                    "Protocol Buffers schema must specify syntax",
                    schema_type="protobuf"
                )
            
            # Check for service or message definitions
            if "message" not in proto_content and "service" not in proto_content:
                raise SchemaValidationError(
                    "Protocol Buffers schema must contain at least one message or service",
                    schema_type="protobuf"
                )
            
            return True
            
        except Exception as e:
            raise SchemaValidationError(
                f"Protocol Buffers validation failed: {str(e)}",
                schema_type="protobuf",
                validation_errors=[str(e)]
            )
    
    def validate_response_format(
        self,
        response: Dict,
        expected_schema: Dict,
        schema_type: str = "json_schema"
    ) -> bool:
        """
        Validate API response format.
        
        Args:
            response: API response data
            expected_schema: Expected schema
            schema_type: Type of schema validation
            
        Returns:
            True if valid
        """
        if schema_type == "json_schema":
            return self.validate_json_schema(response, expected_schema)
        else:
            raise SchemaValidationError(f"Unsupported schema type: {schema_type}")
    
    def validate_request_format(
        self,
        request: Dict,
        expected_schema: Dict,
        schema_type: str = "json_schema"
    ) -> bool:
        """
        Validate API request format.
        
        Args:
            request: API request data
            expected_schema: Expected schema
            schema_type: Type of schema validation
            
        Returns:
            True if valid
        """
        if schema_type == "json_schema":
            return self.validate_json_schema(request, expected_schema)
        else:
            raise SchemaValidationError(f"Unsupported schema type: {schema_type}")
    
    def extract_schema_from_openapi(self, openapi_spec: Dict, endpoint: str, method: str) -> Dict:
        """
        Extract schema for specific endpoint from OpenAPI spec.
        
        Args:
            openapi_spec: OpenAPI specification
            endpoint: API endpoint path
            method: HTTP method
            
        Returns:
            Schema definition
        """
        try:
            path_spec = openapi_spec["paths"][endpoint]
            method_spec = path_spec[method.lower()]
            
            # Extract request schema
            request_schema = None
            if "requestBody" in method_spec:
                content = method_spec["requestBody"]["content"]
                if "application/json" in content:
                    request_schema = content["application/json"]["schema"]
            
            # Extract response schema
            response_schema = None
            if "responses" in method_spec:
                for status_code, response_spec in method_spec["responses"].items():
                    if "content" in response_spec and "application/json" in response_spec["content"]:
                        response_schema = response_spec["content"]["application/json"]["schema"]
                        break
            
            return {
                "request_schema": request_schema,
                "response_schema": response_schema
            }
            
        except KeyError as e:
            raise SchemaValidationError(
                f"Schema not found for {method} {endpoint}: {str(e)}",
                schema_type="openapi"
            )
    
    def _load_spec_file(self, file_path: Union[str, Path]) -> Dict:
        """Load specification file (JSON or YAML)."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise SchemaValidationError(f"Spec file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    if not yaml:
                        raise SchemaValidationError("PyYAML library not available for YAML files")
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        except Exception as e:
            raise SchemaValidationError(f"Failed to load spec file {file_path}: {str(e)}")
    
    def _check_dependencies(self) -> None:
        """Check if required dependencies are available."""
        missing_deps = []
        
        if not jsonschema:
            missing_deps.append("jsonschema")
        if not validate_spec:
            missing_deps.append("openapi-spec-validator")
        if not yaml:
            missing_deps.append("PyYAML")
        
        if missing_deps:
            logger.warning(f"Optional dependencies missing: {missing_deps}")
            logger.warning("Some validation features may not be available")
