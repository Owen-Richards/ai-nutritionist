"""
Data Validation Components

Schema validation, data type checking, constraint validation,
and referential integrity validation.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union, Type, Set, Tuple
from datetime import datetime, date
from uuid import UUID
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from pydantic import BaseModel, ValidationError, Field
from src.models.analytics import PIILevel, ConsentType
from src.models.user_profile import DietaryPreference, ActivityLevel, HealthGoal
from src.models.user import UserGoal, NutritionTargets, UserPreferences

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge another validation result."""
        combined = ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            metadata={**self.metadata, **other.metadata}
        )
        return combined


class SchemaValidator:
    """Validates data against predefined schemas."""
    
    def __init__(self):
        self.schemas = {}
        self.registered_models = {}
        self._register_default_schemas()
    
    def _register_default_schemas(self):
        """Register default Pydantic models as schemas."""
        from src.models.user_profile import (
            FoodAllergy, HealthMetrics, MacroTargets, 
            FamilyMember, BudgetPreferences
        )
        from src.models.meal_plan import MealPlan
        from src.models.analytics import BaseEvent, UserProfile, UserPII
        
        # Register core models
        self.registered_models.update({
            'user_goal': UserGoal,
            'nutrition_targets': NutritionTargets,
            'user_preferences': UserPreferences,
            'food_allergy': FoodAllergy,
            'health_metrics': HealthMetrics,
            'macro_targets': MacroTargets,
            'family_member': FamilyMember,
            'budget_preferences': BudgetPreferences,
            'base_event': BaseEvent,
            'user_profile': UserProfile,
            'user_pii': UserPII
        })
    
    def register_schema(self, name: str, schema: Union[BaseModel, Dict[str, Any]]):
        """Register a custom schema."""
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            self.registered_models[name] = schema
        else:
            self.schemas[name] = schema
    
    def validate_against_schema(self, data: Any, schema_name: str) -> ValidationResult:
        """Validate data against a registered schema."""
        result = ValidationResult(is_valid=True)
        
        try:
            # Check if it's a Pydantic model
            if schema_name in self.registered_models:
                model_class = self.registered_models[schema_name]
                if isinstance(data, dict):
                    validated = model_class(**data)
                else:
                    validated = model_class.parse_obj(data)
                result.metadata['validated_data'] = validated
                
            # Check if it's a custom JSON schema
            elif schema_name in self.schemas:
                schema = self.schemas[schema_name]
                self._validate_json_schema(data, schema, result)
            
            else:
                result.add_error(f"Schema '{schema_name}' not found")
                
        except ValidationError as e:
            for error in e.errors():
                field_path = '.'.join(str(loc) for loc in error['loc'])
                result.add_error(f"Field '{field_path}': {error['msg']}")
        except Exception as e:
            result.add_error(f"Schema validation error: {str(e)}")
        
        return result
    
    def _validate_json_schema(self, data: Any, schema: Dict[str, Any], result: ValidationResult):
        """Validate against a JSON schema."""
        try:
            import jsonschema
            jsonschema.validate(data, schema)
        except ImportError:
            result.add_warning("jsonschema not available, skipping JSON schema validation")
        except Exception as e:
            result.add_error(f"JSON schema validation failed: {str(e)}")
    
    def validate_nested_structure(self, data: Dict[str, Any], expected_structure: Dict[str, Any]) -> ValidationResult:
        """Validate nested data structure."""
        result = ValidationResult(is_valid=True)
        
        def _validate_recursive(actual: Any, expected: Any, path: str = ""):
            if isinstance(expected, dict):
                if not isinstance(actual, dict):
                    result.add_error(f"Expected dict at {path}, got {type(actual).__name__}")
                    return
                
                for key, expected_value in expected.items():
                    current_path = f"{path}.{key}" if path else key
                    if key not in actual:
                        result.add_error(f"Missing required field: {current_path}")
                    else:
                        _validate_recursive(actual[key], expected_value, current_path)
            
            elif isinstance(expected, list) and expected:
                if not isinstance(actual, list):
                    result.add_error(f"Expected list at {path}, got {type(actual).__name__}")
                    return
                
                if actual:  # Only validate if list is not empty
                    _validate_recursive(actual[0], expected[0], f"{path}[0]")
            
            elif isinstance(expected, type):
                if not isinstance(actual, expected):
                    result.add_error(f"Expected {expected.__name__} at {path}, got {type(actual).__name__}")
        
        _validate_recursive(data, expected_structure)
        return result


class DataTypeValidator:
    """Validates data types and formats."""
    
    def __init__(self):
        self.type_validators = {
            'email': self._validate_email,
            'phone': self._validate_phone,
            'uuid': self._validate_uuid,
            'datetime': self._validate_datetime,
            'url': self._validate_url,
            'json': self._validate_json,
            'enum': self._validate_enum,
            'numeric_range': self._validate_numeric_range,
            'string_length': self._validate_string_length
        }
    
    def validate_field_type(self, value: Any, field_type: str, **kwargs) -> ValidationResult:
        """Validate a field against its expected type."""
        result = ValidationResult(is_valid=True)
        
        if field_type in self.type_validators:
            validator = self.type_validators[field_type]
            if not validator(value, result, **kwargs):
                result.is_valid = False
        else:
            result.add_error(f"Unknown field type: {field_type}")
        
        return result
    
    def _validate_email(self, value: Any, result: ValidationResult, **kwargs) -> bool:
        """Validate email format."""
        if not isinstance(value, str):
            result.add_error("Email must be a string")
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            result.add_error("Invalid email format")
            return False
        
        return True
    
    def _validate_phone(self, value: Any, result: ValidationResult, **kwargs) -> bool:
        """Validate phone number format."""
        if not isinstance(value, str):
            result.add_error("Phone number must be a string")
            return False
        
        # Basic phone validation - can be extended
        phone_pattern = r'^\+?[\d\s\-\(\)]{10,15}$'
        if not re.match(phone_pattern, value):
            result.add_error("Invalid phone number format")
            return False
        
        return True
    
    def _validate_uuid(self, value: Any, result: ValidationResult, **kwargs) -> bool:
        """Validate UUID format."""
        try:
            if isinstance(value, str):
                UUID(value)
            elif not isinstance(value, UUID):
                result.add_error("UUID must be a string or UUID object")
                return False
        except ValueError:
            result.add_error("Invalid UUID format")
            return False
        
        return True
    
    def _validate_datetime(self, value: Any, result: ValidationResult, **kwargs) -> bool:
        """Validate datetime format."""
        if isinstance(value, datetime):
            return True
        
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except ValueError:
                result.add_error("Invalid datetime format")
                return False
        
        result.add_error("Datetime must be datetime object or ISO string")
        return False
    
    def _validate_url(self, value: Any, result: ValidationResult, **kwargs) -> bool:
        """Validate URL format."""
        if not isinstance(value, str):
            result.add_error("URL must be a string")
            return False
        
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, value):
            result.add_error("Invalid URL format")
            return False
        
        return True
    
    def _validate_json(self, value: Any, result: ValidationResult, **kwargs) -> bool:
        """Validate JSON format."""
        if isinstance(value, str):
            try:
                json.loads(value)
                return True
            except json.JSONDecodeError:
                result.add_error("Invalid JSON format")
                return False
        elif isinstance(value, (dict, list)):
            return True
        
        result.add_error("Value must be JSON string or dict/list")
        return False
    
    def _validate_enum(self, value: Any, result: ValidationResult, enum_class=None, **kwargs) -> bool:
        """Validate enum value."""
        if enum_class is None:
            result.add_error("Enum class not specified")
            return False
        
        try:
            if isinstance(value, str):
                enum_class(value)
            elif not isinstance(value, enum_class):
                result.add_error(f"Value must be {enum_class.__name__} or valid string")
                return False
        except ValueError:
            valid_values = [e.value for e in enum_class]
            result.add_error(f"Invalid enum value. Must be one of: {valid_values}")
            return False
        
        return True
    
    def _validate_numeric_range(self, value: Any, result: ValidationResult, 
                              min_val=None, max_val=None, **kwargs) -> bool:
        """Validate numeric value within range."""
        if not isinstance(value, (int, float)):
            result.add_error("Value must be numeric")
            return False
        
        if min_val is not None and value < min_val:
            result.add_error(f"Value {value} is below minimum {min_val}")
            return False
        
        if max_val is not None and value > max_val:
            result.add_error(f"Value {value} is above maximum {max_val}")
            return False
        
        return True
    
    def _validate_string_length(self, value: Any, result: ValidationResult,
                               min_length=None, max_length=None, **kwargs) -> bool:
        """Validate string length."""
        if not isinstance(value, str):
            result.add_error("Value must be a string")
            return False
        
        length = len(value)
        
        if min_length is not None and length < min_length:
            result.add_error(f"String length {length} is below minimum {min_length}")
            return False
        
        if max_length is not None and length > max_length:
            result.add_error(f"String length {length} is above maximum {max_length}")
            return False
        
        return True


class ConstraintValidator:
    """Validates business rules and constraints."""
    
    def __init__(self):
        self.constraints = {}
        self._register_default_constraints()
    
    def _register_default_constraints(self):
        """Register default business constraints."""
        self.constraints.update({
            'user_age_range': lambda age: 13 <= age <= 120,
            'weight_range_kg': lambda weight: 20 <= weight <= 300,
            'height_range_cm': lambda height: 50 <= height <= 250,
            'calorie_range': lambda calories: 800 <= calories <= 5000,
            'macro_percentages': self._validate_macro_percentages,
            'budget_positive': lambda budget: budget > 0,
            'household_size_positive': lambda size: size > 0,
            'prep_time_reasonable': lambda time: 5 <= time <= 240,  # 5 min to 4 hours
        })
    
    def register_constraint(self, name: str, validator_func):
        """Register a custom constraint."""
        self.constraints[name] = validator_func
    
    def validate_constraint(self, value: Any, constraint_name: str) -> ValidationResult:
        """Validate a value against a constraint."""
        result = ValidationResult(is_valid=True)
        
        if constraint_name not in self.constraints:
            result.add_error(f"Unknown constraint: {constraint_name}")
            return result
        
        try:
            constraint_func = self.constraints[constraint_name]
            if not constraint_func(value):
                result.add_error(f"Constraint '{constraint_name}' failed for value: {value}")
        except Exception as e:
            result.add_error(f"Error validating constraint '{constraint_name}': {str(e)}")
        
        return result
    
    def validate_multiple_constraints(self, data: Dict[str, Any], 
                                    constraints: Dict[str, str]) -> ValidationResult:
        """Validate multiple fields against their constraints."""
        result = ValidationResult(is_valid=True)
        
        for field_name, constraint_name in constraints.items():
            if field_name in data:
                field_result = self.validate_constraint(data[field_name], constraint_name)
                result = result.merge(field_result)
        
        return result
    
    def _validate_macro_percentages(self, nutrition_targets: NutritionTargets) -> bool:
        """Validate that macro percentages add up correctly."""
        try:
            total_percent = (
                nutrition_targets.protein_percent + 
                nutrition_targets.carbs_percent + 
                nutrition_targets.fat_percent
            )
            return 95 <= total_percent <= 105  # Allow 5% tolerance
        except Exception:
            return False


class ReferentialIntegrityValidator:
    """Validates referential integrity across data entities."""
    
    def __init__(self):
        self.relationships = {}
        self.entity_stores = {}
    
    def register_relationship(self, parent_entity: str, child_entity: str, 
                            foreign_key: str, parent_key: str = 'id'):
        """Register a referential integrity relationship."""
        if parent_entity not in self.relationships:
            self.relationships[parent_entity] = []
        
        self.relationships[parent_entity].append({
            'child_entity': child_entity,
            'foreign_key': foreign_key,
            'parent_key': parent_key
        })
    
    def register_entity_store(self, entity_name: str, store_func):
        """Register a function to retrieve entities for validation."""
        self.entity_stores[entity_name] = store_func
    
    def validate_foreign_key(self, child_data: Dict[str, Any], 
                           parent_entity: str, foreign_key: str,
                           parent_key: str = 'id') -> ValidationResult:
        """Validate a foreign key reference."""
        result = ValidationResult(is_valid=True)
        
        if foreign_key not in child_data:
            result.add_error(f"Missing foreign key: {foreign_key}")
            return result
        
        foreign_key_value = child_data[foreign_key]
        
        if parent_entity not in self.entity_stores:
            result.add_warning(f"No store registered for entity: {parent_entity}")
            return result
        
        try:
            store_func = self.entity_stores[parent_entity]
            parent_exists = store_func(parent_key, foreign_key_value)
            
            if not parent_exists:
                result.add_error(f"Foreign key '{foreign_key}' references non-existent {parent_entity}")
        
        except Exception as e:
            result.add_error(f"Error validating foreign key: {str(e)}")
        
        return result
    
    def validate_entity_relationships(self, entity_name: str, 
                                    entity_data: Dict[str, Any]) -> ValidationResult:
        """Validate all relationships for an entity."""
        result = ValidationResult(is_valid=True)
        
        if entity_name not in self.relationships:
            return result  # No relationships to validate
        
        for relationship in self.relationships[entity_name]:
            rel_result = self.validate_foreign_key(
                entity_data,
                relationship['child_entity'],
                relationship['foreign_key'],
                relationship['parent_key']
            )
            result = result.merge(rel_result)
        
        return result
    
    def validate_circular_references(self, entity_graph: Dict[str, List[str]]) -> ValidationResult:
        """Validate that there are no circular references in the entity graph."""
        result = ValidationResult(is_valid=True)
        
        def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in entity_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for node in entity_graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    result.add_error(f"Circular reference detected involving entity: {node}")
        
        return result
