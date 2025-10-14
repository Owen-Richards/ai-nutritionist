"""Common type definitions and aliases.

This module provides type aliases and generic types used throughout the application.
"""

from __future__ import annotations

import sys
from decimal import Decimal as StdDecimal
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
    Protocol,
    runtime_checkable,
    TYPE_CHECKING,
)
from uuid import UUID as StdUUID
from datetime import datetime as StdDateTime, date as StdDate

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

# Basic type aliases
UUID: TypeAlias = StdUUID
DateTime: TypeAlias = StdDateTime
Date: TypeAlias = StdDate
Decimal: TypeAlias = StdDecimal

# JSON-compatible types
JSONPrimitive: TypeAlias = Union[str, int, float, bool, None]
JSONValue: TypeAlias = Union[JSONPrimitive, Dict[str, Any], List[Any]]
JSONDict: TypeAlias = Dict[str, JSONValue]
JSONList: TypeAlias = List[JSONValue]

# Generic type variables
T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')

# Domain-specific type variables
TUser = TypeVar('TUser')
TMeal = TypeVar('TMeal')
TPlan = TypeVar('TPlan')
TEvent = TypeVar('TEvent')

# Protocol type variables  
TComparable = TypeVar('TComparable', bound='Comparable')

# Numeric types
Numeric: TypeAlias = Union[int, float, Decimal]
PositiveInt: TypeAlias = int  # Should be > 0 (validated at runtime)
NonNegativeInt: TypeAlias = int  # Should be >= 0 (validated at runtime)
PositiveFloat: TypeAlias = float  # Should be > 0.0 (validated at runtime)
NonNegativeFloat: TypeAlias = float  # Should be >= 0.0 (validated at runtime)

# String types
NonEmptyStr: TypeAlias = str  # Should be non-empty (validated at runtime)
EmailStr: TypeAlias = str  # Should be valid email (validated at runtime)
PhoneStr: TypeAlias = str  # Should be valid phone (validated at runtime)
URLStr: TypeAlias = str  # Should be valid URL (validated at runtime)

# ID types
UserID: TypeAlias = str
PlanID: TypeAlias = str
MealID: TypeAlias = str
CrewID: TypeAlias = str
ReflectionID: TypeAlias = str
EventID: TypeAlias = str
SessionID: TypeAlias = str
RequestID: TypeAlias = str

# Percentage type (0-100)
Percentage: TypeAlias = float  # Should be 0.0-100.0 (validated at runtime)
Rate: TypeAlias = float  # Should be 0.0-1.0 (validated at runtime)

# Common protocols
@runtime_checkable
class Comparable(Protocol):
    """Protocol for comparable types."""
    
    def __lt__(self, other: Any) -> bool: ...
    def __le__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...
    def __ge__(self, other: Any) -> bool: ...

@runtime_checkable
class Hashable(Protocol):
    """Protocol for hashable types."""
    
    def __hash__(self) -> int: ...

@runtime_checkable
class Serializable(Protocol):
    """Protocol for serializable types."""
    
    def to_dict(self) -> JSONDict: ...
    
    @classmethod
    def from_dict(cls, data: JSONDict) -> Self: ...

@runtime_checkable
class Identifiable(Protocol):
    """Protocol for objects with an ID."""
    
    @property
    def id(self) -> str: ...

@runtime_checkable
class Timestamped(Protocol):
    """Protocol for objects with timestamps."""
    
    @property
    def created_at(self) -> DateTime: ...
    
    @property
    def updated_at(self) -> Optional[DateTime]: ...

@runtime_checkable
class Versioned(Protocol):
    """Protocol for versioned objects."""
    
    @property
    def version(self) -> int: ...

# Configuration types
ConfigValue: TypeAlias = Union[str, int, float, bool, List[str], Dict[str, Any]]
ConfigDict: TypeAlias = Dict[str, ConfigValue]

# Error types
ErrorCode: TypeAlias = str
ErrorMessage: TypeAlias = str
ErrorDetails: TypeAlias = Dict[str, Any]

# Pagination types
PageSize: TypeAlias = PositiveInt
PageNumber: TypeAlias = PositiveInt
TotalCount: TypeAlias = NonNegativeInt
Offset: TypeAlias = NonNegativeInt
Limit: TypeAlias = PositiveInt

# Authentication types
Token: TypeAlias = str
RefreshToken: TypeAlias = str
APIKey: TypeAlias = str
Secret: TypeAlias = str

# HTTP types
HTTPMethod: TypeAlias = str
HTTPStatus: TypeAlias = int
HTTPHeaders: TypeAlias = Dict[str, str]
QueryParams: TypeAlias = Dict[str, Union[str, List[str]]]

# File types
FilePath: TypeAlias = str
FileName: TypeAlias = str
FileContent: TypeAlias = bytes
FileSize: TypeAlias = NonNegativeInt
MimeType: TypeAlias = str

# Geolocation types
Latitude: TypeAlias = float  # Should be -90.0 to 90.0
Longitude: TypeAlias = float  # Should be -180.0 to 180.0
Coordinates: TypeAlias = tuple[Latitude, Longitude]

# Business domain types
Currency: TypeAlias = str  # ISO 4217 currency code
MoneyAmount: TypeAlias = Decimal
Price: TypeAlias = MoneyAmount
Cost: TypeAlias = MoneyAmount
Budget: TypeAlias = MoneyAmount

# Nutrition types
CalorieCount: TypeAlias = NonNegativeFloat
MacroGrams: TypeAlias = NonNegativeFloat
Protein: TypeAlias = MacroGrams
Carbs: TypeAlias = MacroGrams
Fat: TypeAlias = MacroGrams
Fiber: TypeAlias = MacroGrams
Sugar: TypeAlias = MacroGrams
Sodium: TypeAlias = MacroGrams

# Time types
Duration: TypeAlias = int  # seconds
Minutes: TypeAlias = NonNegativeInt
Hours: TypeAlias = NonNegativeFloat
Days: TypeAlias = NonNegativeInt
Weeks: TypeAlias = NonNegativeInt

# Rating types
Rating: TypeAlias = int  # 1-5 scale
Score: TypeAlias = float  # 0.0-1.0 scale
Confidence: TypeAlias = float  # 0.0-1.0 scale

# Collection types
StringList: TypeAlias = List[str]
StringSet: TypeAlias = set[str]
StringDict: TypeAlias = Dict[str, str]
IntList: TypeAlias = List[int]
FloatList: TypeAlias = List[float]

# Optional variants
OptionalStr: TypeAlias = Optional[str]
OptionalInt: TypeAlias = Optional[int]
OptionalFloat: TypeAlias = Optional[float]
OptionalBool: TypeAlias = Optional[bool]
OptionalDateTime: TypeAlias = Optional[DateTime]
OptionalUUID: TypeAlias = Optional[UUID]

# Type guards
def is_non_empty_string(value: Any) -> bool:
    """Type guard for non-empty strings."""
    return isinstance(value, str) and len(value.strip()) > 0

def is_positive_number(value: Any) -> bool:
    """Type guard for positive numbers."""
    return isinstance(value, (int, float)) and value > 0

def is_valid_email(value: Any) -> bool:
    """Type guard for valid email addresses."""
    import re
    if not isinstance(value, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, value))

def is_valid_phone(value: Any) -> bool:
    """Type guard for valid phone numbers."""
    import re
    if not isinstance(value, str):
        return False
    # Basic phone validation - adjust regex as needed
    pattern = r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'
    return bool(re.match(pattern, value.replace(' ', '')))

def is_valid_uuid(value: Any) -> bool:
    """Type guard for valid UUIDs."""
    try:
        if isinstance(value, str):
            UUID(value)
            return True
        elif isinstance(value, UUID):
            return True
        return False
    except (ValueError, TypeError):
        return False

def is_percentage(value: Any) -> bool:
    """Type guard for percentage values (0-100)."""
    return isinstance(value, (int, float)) and 0 <= value <= 100

def is_rate(value: Any) -> bool:
    """Type guard for rate values (0-1)."""
    return isinstance(value, (int, float)) and 0 <= value <= 1

# Export all public types
__all__ = [
    # Basic types
    'UUID', 'DateTime', 'Date', 'Decimal',
    
    # JSON types
    'JSONPrimitive', 'JSONValue', 'JSONDict', 'JSONList',
    
    # Type variables
    'T', 'U', 'V', 'TUser', 'TMeal', 'TPlan', 'TEvent', 'TComparable',
    
    # Numeric types
    'Numeric', 'PositiveInt', 'NonNegativeInt', 'PositiveFloat', 'NonNegativeFloat',
    
    # String types
    'NonEmptyStr', 'EmailStr', 'PhoneStr', 'URLStr',
    
    # ID types
    'UserID', 'PlanID', 'MealID', 'CrewID', 'ReflectionID', 'EventID',
    'SessionID', 'RequestID',
    
    # Rate types
    'Percentage', 'Rate',
    
    # Protocols
    'Comparable', 'Hashable', 'Serializable', 'Identifiable', 'Timestamped', 'Versioned',
    
    # Configuration types
    'ConfigValue', 'ConfigDict',
    
    # Error types
    'ErrorCode', 'ErrorMessage', 'ErrorDetails',
    
    # Pagination types
    'PageSize', 'PageNumber', 'TotalCount', 'Offset', 'Limit',
    
    # Authentication types
    'Token', 'RefreshToken', 'APIKey', 'Secret',
    
    # HTTP types
    'HTTPMethod', 'HTTPStatus', 'HTTPHeaders', 'QueryParams',
    
    # File types
    'FilePath', 'FileName', 'FileContent', 'FileSize', 'MimeType',
    
    # Geolocation types
    'Latitude', 'Longitude', 'Coordinates',
    
    # Business types
    'Currency', 'MoneyAmount', 'Price', 'Cost', 'Budget',
    
    # Nutrition types
    'CalorieCount', 'MacroGrams', 'Protein', 'Carbs', 'Fat', 'Fiber', 'Sugar', 'Sodium',
    
    # Time types
    'Duration', 'Minutes', 'Hours', 'Days', 'Weeks',
    
    # Rating types
    'Rating', 'Score', 'Confidence',
    
    # Collection types
    'StringList', 'StringSet', 'StringDict', 'IntList', 'FloatList',
    
    # Optional types
    'OptionalStr', 'OptionalInt', 'OptionalFloat', 'OptionalBool',
    'OptionalDateTime', 'OptionalUUID',
    
    # Type guards
    'is_non_empty_string', 'is_positive_number', 'is_valid_email', 'is_valid_phone',
    'is_valid_uuid', 'is_percentage', 'is_rate',
]
