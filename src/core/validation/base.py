"""Base validation models providing foundation for all data validation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, get_origin, get_args
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from pydantic.functional_validators import ValidationInfo
from pydantic._internal._model_construction import complete_model_class

from .errors import ValidationErrorHandler, FieldValidationError
from .performance import ValidationCache

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='BaseValidationModel')


class BaseValidationModel(BaseModel):
    """Enhanced base model with comprehensive validation features.
    
    Features:
    - Automatic validation error handling
    - Performance optimization
    - Cross-field validation
    - Conditional validation
    - Custom error messages
    """
    
    model_config = ConfigDict(
        # Validation settings
        validate_assignment=True,
        validate_default=True,
        validate_return=True,
        str_strip_whitespace=True,
        
        # Performance settings
        arbitrary_types_allowed=True,
        use_enum_values=True,
        
        # JSON settings
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            UUID: lambda v: str(v) if v else None,
        },
        
        # Security settings
        extra='forbid',
        frozen=False,
    )
    
    # Metadata fields
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Timestamp when the model was created"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Timestamp when the model was last updated"
    )
    version: str = Field(
        default="1.0",
        description="Model version for compatibility tracking"
    )
    
    def __init__(self, **data):
        """Initialize with enhanced error handling."""
        try:
            super().__init__(**data)
            self._post_init_validation()
        except Exception as e:
            ValidationErrorHandler.handle_init_error(e, self.__class__, data)
            raise
    
    def _post_init_validation(self) -> None:
        """Additional validation after model initialization."""
        self._validate_business_rules()
        self._validate_cross_field_dependencies()
    
    def _validate_business_rules(self) -> None:
        """Override to implement custom business rule validation."""
        pass
    
    def _validate_cross_field_dependencies(self) -> None:
        """Override to implement cross-field validation logic."""
        pass
    
    @model_validator(mode='after')
    def validate_model_integrity(self) -> 'BaseValidationModel':
        """Final model integrity validation."""
        self.updated_at = datetime.utcnow()
        return self
    
    def to_dict(self, 
                include_metadata: bool = True,
                exclude_none: bool = True) -> Dict[str, Any]:
        """Convert model to dictionary with options."""
        exclude_fields = set()
        if not include_metadata:
            exclude_fields.update({'created_at', 'updated_at', 'version'})
        
        return self.model_dump(
            exclude=exclude_fields,
            exclude_none=exclude_none,
            by_alias=True
        )
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create model instance from dictionary with validation."""
        return cls.model_validate(data)
    
    @classmethod
    def validate_partial(cls: Type[T], 
                        data: Dict[str, Any],
                        fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate only specified fields for partial updates."""
        if fields:
            filtered_data = {k: v for k, v in data.items() if k in fields}
        else:
            filtered_data = data
        
        # Create temporary instance for validation
        try:
            temp_instance = cls.model_validate(filtered_data)
            return temp_instance.to_dict(include_metadata=False)
        except Exception as e:
            ValidationErrorHandler.handle_partial_validation_error(e, cls, filtered_data)
            raise
    
    def merge_update(self, update_data: Dict[str, Any]) -> 'BaseValidationModel':
        """Merge update data with existing model."""
        current_data = self.to_dict(include_metadata=False)
        current_data.update(update_data)
        current_data['updated_at'] = datetime.utcnow()
        
        return self.__class__.from_dict(current_data)


class APIRequestModel(BaseValidationModel):
    """Base model for API request validation.
    
    Features:
    - Request ID tracking
    - Input sanitization
    - Rate limiting metadata
    - Request context validation
    """
    
    request_id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique request identifier for tracing"
    )
    client_version: Optional[str] = Field(
        default=None,
        description="Client application version"
    )
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User agent string"
    )
    
    @field_validator('user_agent')
    @classmethod
    def sanitize_user_agent(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize user agent string."""
        if v is None:
            return v
        # Remove potential injection attempts
        sanitized = ''.join(c for c in v if c.isprintable())
        return sanitized[:500]  # Truncate if too long


class APIResponseModel(BaseValidationModel):
    """Base model for API response validation.
    
    Features:
    - Response metadata
    - Performance metrics
    - Error context
    - Cache headers
    """
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for tracing"
    )
    response_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Response time in milliseconds"
    )
    cache_hit: bool = Field(
        default=False,
        description="Whether response was served from cache"
    )
    
    def set_performance_metrics(self, start_time: datetime) -> None:
        """Set performance metrics based on start time."""
        end_time = datetime.utcnow()
        self.response_time_ms = (end_time - start_time).total_seconds() * 1000


class DomainEntityModel(BaseValidationModel):
    """Base model for domain entities.
    
    Features:
    - Entity ID management
    - Domain-specific validation
    - Business rule enforcement
    - Audit trail
    """
    
    id: UUID = Field(
        default_factory=uuid4,
        description="Unique entity identifier"
    )
    
    def __eq__(self, other: object) -> bool:
        """Compare entities by ID."""
        if not isinstance(other, DomainEntityModel):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash by entity ID."""
        return hash(self.id)


class ConfigurationModel(BaseValidationModel):
    """Base model for configuration validation.
    
    Features:
    - Environment-specific validation
    - Secret detection
    - Configuration drift detection
    - Default value management
    """
    
    environment: str = Field(
        default="development",
        description="Environment this configuration applies to"
    )
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_secrets(cls, v: Any, info: ValidationInfo) -> Any:
        """Detect and flag potential secrets in configuration."""
        if isinstance(v, str):
            # Simple secret detection patterns
            secret_patterns = ['password', 'secret', 'key', 'token', 'credential']
            field_name = info.field_name.lower() if info.field_name else ''
            
            if any(pattern in field_name for pattern in secret_patterns):
                if len(v) > 20:  # Likely a secret
                    logger.warning(f"Potential secret detected in field: {field_name}")
        
        return v


class EventModel(BaseValidationModel):
    """Base model for event validation.
    
    Features:
    - Event metadata
    - Payload validation
    - Event versioning
    - Serialization optimization
    """
    
    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique event identifier"
    )
    event_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of event"
    )
    event_version: str = Field(
        default="1.0",
        description="Event schema version"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Event timestamp"
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Event source identifier"
    )
    
    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type format."""
        if not v.replace('_', '').replace('.', '').isalnum():
            raise ValueError("Event type must contain only alphanumeric characters, underscores, and dots")
        return v


# Validation model registry for dynamic access
class ValidationModelRegistry:
    """Registry for all validation models."""
    
    _models: Dict[str, Type[BaseValidationModel]] = {}
    
    @classmethod
    def register(cls, name: str, model_class: Type[BaseValidationModel]) -> None:
        """Register a validation model."""
        cls._models[name] = model_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseValidationModel]]:
        """Get a validation model by name."""
        return cls._models.get(name)
    
    @classmethod
    def list_models(cls) -> List[str]:
        """List all registered model names."""
        return list(cls._models.keys())


# Register base models
ValidationModelRegistry.register('base', BaseValidationModel)
ValidationModelRegistry.register('api_request', APIRequestModel)
ValidationModelRegistry.register('api_response', APIResponseModel)
ValidationModelRegistry.register('domain_entity', DomainEntityModel)
ValidationModelRegistry.register('configuration', ConfigurationModel)
ValidationModelRegistry.register('event', EventModel)
