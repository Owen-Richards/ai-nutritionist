#!/usr/bin/env python3
"""
Entity Generator for AI Nutritionist

Generates complete domain entities with:
- Pydantic model definitions
- Validation schemas
- Factory methods
- Unit tests
- Migration scripts
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FieldConfig:
    """Configuration for entity fields"""
    name: str
    type: str
    required: bool = True
    default: Optional[Any] = None
    description: str = ""
    validation: Optional[Dict[str, Any]] = None


@dataclass
class EntityConfig:
    """Configuration for entity generation"""
    name: str
    description: str
    fields: List[FieldConfig]
    table_name: Optional[str] = None
    has_timestamps: bool = True
    has_soft_delete: bool = False
    has_audit: bool = False


class EntityGenerator:
    """Generates complete entity implementations"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    def generate_entity(self, config: EntityConfig) -> Dict[str, str]:
        """Generate complete entity implementation"""
        files = {}
        
        # Generate Pydantic model
        files[f"src/models/{config.name.lower()}.py"] = self._generate_model(config)
        
        # Generate validation schemas
        files[f"src/schemas/{config.name.lower()}_schemas.py"] = self._generate_schemas(config)
        
        # Generate factory
        files[f"src/factories/{config.name.lower()}_factory.py"] = self._generate_factory(config)
        
        # Generate unit tests
        files[f"tests/unit/test_{config.name.lower()}_model.py"] = self._generate_tests(config)
        
        # Generate migration if table specified
        if config.table_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            files[f"migrations/{timestamp}_create_{config.name.lower()}_table.py"] = self._generate_migration(config)
        
        return files
    
    def _generate_model(self, config: EntityConfig) -> str:
        """Generate Pydantic model"""
        imports = [
            "from __future__ import annotations",
            "",
            "from datetime import datetime",
            "from typing import Optional, Dict, Any, List",
            "from uuid import UUID, uuid4",
            "from decimal import Decimal",
            "",
            "from pydantic import BaseModel, Field, validator, root_validator",
            "from enum import Enum",
        ]
        
        # Generate field definitions
        field_definitions = []
        validators = []
        
        for field in config.fields:
            field_def = self._generate_field_definition(field)
            field_definitions.append(field_def)
            
            if field.validation:
                validator_def = self._generate_field_validator(field)
                validators.append(validator_def)
        
        # Add standard fields
        if config.has_timestamps:
            field_definitions.extend([
                '    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")',
                '    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")'
            ])
        
        if config.has_soft_delete:
            field_definitions.append('    deleted_at: Optional[datetime] = Field(None, description="Soft deletion timestamp")')
        
        if config.has_audit:
            field_definitions.extend([
                '    created_by: Optional[str] = Field(None, description="Created by user ID")',
                '    updated_by: Optional[str] = Field(None, description="Last updated by user ID")'
            ])
        
        return f'''"""
{config.name} Domain Entity

{config.description}
"""

{chr(10).join(imports)}


class {config.name}(BaseModel):
    """
    {config.name} entity
    
    {config.description}
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier")
{chr(10).join(field_definitions)}
    
    class Config:
        """Pydantic model configuration"""
        json_encoders = {{
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
            UUID: lambda v: str(v)
        }}
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"
    
    {chr(10).join(validators) if validators else ""}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.dict(by_alias=True, exclude_none=True)
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        item = self.to_dict()
        
        # Add DynamoDB keys
        item.update({{
            'PK': f'{config.name.upper()}_{{self.id}}',
            'SK': f'{config.name.upper()}_{{self.id}}',
            'GSI1PK': f'type#{config.name.lower()}',
            'GSI1SK': self.id,
            'entity_type': '{config.name.lower()}'
        }})
        
        # Convert datetime to ISO string
        for key, value in item.items():
            if isinstance(value, datetime):
                item[key] = value.isoformat()
        
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> '{config.name}':
        """Create from DynamoDB item"""
        # Remove DynamoDB keys
        entity_data = {{k: v for k, v in item.items() 
                      if k not in ['PK', 'SK', 'GSI1PK', 'GSI1SK', 'entity_type']}}
        
        # Convert ISO strings back to datetime
        for key, value in entity_data.items():
            if isinstance(value, str) and key.endswith('_at'):
                try:
                    entity_data[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
        
        return cls(**entity_data)
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        {'if hasattr(self, "updated_at"):' if config.has_timestamps else ''}
        {'    self.updated_at = datetime.now()' if config.has_timestamps else ''}
    
    {'def mark_deleted(self, deleted_by: Optional[str] = None) -> None:' if config.has_soft_delete else ''}
    {'    """Mark entity as soft deleted"""' if config.has_soft_delete else ''}
    {'    self.deleted_at = datetime.now()' if config.has_soft_delete else ''}
    {'    if deleted_by and hasattr(self, "updated_by"):' if config.has_soft_delete and config.has_audit else ''}
    {'        self.updated_by = deleted_by' if config.has_soft_delete and config.has_audit else ''}
    {'        self.update_timestamp()' if config.has_soft_delete and config.has_timestamps else ''}
    
    {'@property' if config.has_soft_delete else ''}
    {'def is_deleted(self) -> bool:' if config.has_soft_delete else ''}
    {'    """Check if entity is soft deleted"""' if config.has_soft_delete else ''}
    {'    return self.deleted_at is not None' if config.has_soft_delete else ''}
    
    def __str__(self) -> str:
        """String representation"""
        return f"{config.name}(id={{self.id}})"
    
    def __repr__(self) -> str:
        """Developer representation"""
        return f"{config.name}(id='{{self.id}}')"


# Create type aliases for convenience
{config.name}Dict = Dict[str, Any]
{config.name}List = List[{config.name}]
{config.name}Optional = Optional[{config.name}]
'''
    
    def _generate_field_definition(self, field: FieldConfig) -> str:
        """Generate field definition"""
        field_type = field.type
        if not field.required:
            field_type = f"Optional[{field_type}]"
        
        default_value = "..." if field.required and field.default is None else field.default
        if not field.required and field.default is None:
            default_value = "None"
        
        description = field.description or f"{field.name} field"
        
        return f'    {field.name}: {field_type} = Field({default_value}, description="{description}")'
    
    def _generate_field_validator(self, field: FieldConfig) -> str:
        """Generate field validator"""
        validators = []
        
        if field.validation:
            if "min_length" in field.validation or "max_length" in field.validation:
                min_len = field.validation.get("min_length", 0)
                max_len = field.validation.get("max_length", 1000)
                validators.append(f"""
    @validator('{field.name}')
    def validate_{field.name}_length(cls, v):
        if v and (len(v) < {min_len} or len(v) > {max_len}):
            raise ValueError(f'{field.name} must be between {min_len} and {max_len} characters')
        return v""")
            
            if "pattern" in field.validation:
                pattern = field.validation["pattern"]
                validators.append(f"""
    @validator('{field.name}')
    def validate_{field.name}_pattern(cls, v):
        import re
        if v and not re.match(r'{pattern}', v):
            raise ValueError(f'{field.name} does not match required pattern')
        return v""")
            
            if "min_value" in field.validation or "max_value" in field.validation:
                min_val = field.validation.get("min_value")
                max_val = field.validation.get("max_value")
                validators.append(f"""
    @validator('{field.name}')
    def validate_{field.name}_range(cls, v):
        if v is not None:
            {f'if v < {min_val}: raise ValueError(f"{field.name} must be at least {min_val}")' if min_val else ''}
            {f'if v > {max_val}: raise ValueError(f"{field.name} must be at most {max_val}")' if max_val else ''}
        return v""")
        
        return chr(10).join(validators)
    
    def _generate_schemas(self, config: EntityConfig) -> str:
        """Generate validation schemas"""
        return f'''"""
{config.name} Validation Schemas

Pydantic schemas for {config.name.lower()} validation
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from ..models.{config.name.lower()} import {config.name}


class {config.name}CreateSchema(BaseModel):
    """Schema for creating {config.name.lower()} entities"""
    {chr(10).join([f'    {field.name}: {field.type if field.required else f"Optional[{field.type}]"} = Field(..., description="{field.description or field.name}")' for field in config.fields if field.name != 'id'])}
    
    class Config:
        schema_extra = {{
            "example": {{
                {chr(10).join([f'                "{field.name}": {self._get_example_value(field)},' for field in config.fields if field.name != 'id'])}
            }}
        }}


class {config.name}UpdateSchema(BaseModel):
    """Schema for updating {config.name.lower()} entities"""
    {chr(10).join([f'    {field.name}: Optional[{field.type}] = Field(None, description="{field.description or field.name}")' for field in config.fields if field.name != 'id'])}
    
    class Config:
        schema_extra = {{
            "example": {{
                {chr(10).join([f'                "{field.name}": {self._get_example_value(field)},' for field in config.fields[:3] if field.name != 'id'])}
            }}
        }}


class {config.name}ResponseSchema(BaseModel):
    """Schema for {config.name.lower()} responses"""
    id: str
    {chr(10).join([f'    {field.name}: {field.type if field.required else f"Optional[{field.type}]"}' for field in config.fields if field.name != 'id'])}
    {'created_at: datetime' if config.has_timestamps else ''}
    {'updated_at: datetime' if config.has_timestamps else ''}
    {'deleted_at: Optional[datetime] = None' if config.has_soft_delete else ''}
    {'created_by: Optional[str] = None' if config.has_audit else ''}
    {'updated_by: Optional[str] = None' if config.has_audit else ''}
    
    class Config:
        orm_mode = True
        json_encoders = {{
            datetime: lambda v: v.isoformat()
        }}


class {config.name}ListResponseSchema(BaseModel):
    """Schema for {config.name.lower()} list responses"""
    items: list[{config.name}ResponseSchema]
    total: int
    page: int = 1
    size: int = 10
    pages: int


class {config.name}FilterSchema(BaseModel):
    """Schema for {config.name.lower()} filtering"""
    {chr(10).join([f'    {field.name}: Optional[{field.type}] = None' for field in config.fields[:5]])}
    {'deleted: Optional[bool] = Field(False, description="Include deleted items")' if config.has_soft_delete else ''}
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(10, ge=1, le=100, description="Page size")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order (asc/desc)")
'''
    
    def _get_example_value(self, field: FieldConfig) -> str:
        """Get example value for field"""
        if field.type == "str":
            return f'"example_{field.name}"'
        elif field.type == "int":
            return "42"
        elif field.type == "float":
            return "3.14"
        elif field.type == "bool":
            return "true"
        elif field.type == "datetime":
            return '"2023-01-01T00:00:00"'
        else:
            return f'"example_{field.name}"'
    
    def _generate_factory(self, config: EntityConfig) -> str:
        """Generate factory class"""
        return f'''"""
{config.name} Factory

Factory for creating {config.name.lower()} entities in tests and development
"""

from datetime import datetime
from typing import Dict, Any, Optional
from faker import Faker
import random

from ..models.{config.name.lower()} import {config.name}

fake = Faker()


class {config.name}Factory:
    """Factory for creating {config.name} entities"""
    
    @staticmethod
    def create(**kwargs) -> {config.name}:
        """Create a {config.name.lower()} entity with fake data"""
        defaults = {config.name}Factory.get_defaults()
        defaults.update(kwargs)
        return {config.name}(**defaults)
    
    @staticmethod
    def create_batch(count: int, **kwargs) -> list[{config.name}]:
        """Create multiple {config.name.lower()} entities"""
        return [{config.name}Factory.create(**kwargs) for _ in range(count)]
    
    @staticmethod
    def get_defaults() -> Dict[str, Any]:
        """Get default values for {config.name.lower()} creation"""
        return {{
            {chr(10).join([f'            "{field.name}": {config.name}Factory._generate_{field.name}(),' for field in config.fields if field.name != 'id'])}
        }}
    
    {chr(10).join([f'    @staticmethod{chr(10)}    def _generate_{field.name}() -> {field.type}:{chr(10)}        """Generate fake {field.name}"""{chr(10)}        {self._get_fake_generator(field)}{chr(10)}' for field in config.fields if field.name != 'id'])}
    
    @staticmethod
    def create_for_testing() -> {config.name}:
        """Create entity optimized for testing"""
        return {config.name}Factory.create(
            {chr(10).join([f'            {field.name}="test_{field.name}",' for field in config.fields[:3] if field.name != 'id' and field.type == 'str'])}
        )
    
    @staticmethod
    def create_minimal() -> {config.name}:
        """Create entity with minimal required fields"""
        required_fields = {{}}
        {chr(10).join([f'        required_fields["{field.name}"] = {config.name}Factory._generate_{field.name}()' for field in config.fields if field.required and field.name != 'id'])}
        
        return {config.name}(**required_fields)
    
    @staticmethod
    def create_with_validation_errors() -> Dict[str, Any]:
        """Create data that will fail validation (for testing)"""
        return {{
            {chr(10).join([f'            "{field.name}": {self._get_invalid_value(field)},' for field in config.fields[:3] if field.name != 'id'])}
        }}
'''
    
    def _get_fake_generator(self, field: FieldConfig) -> str:
        """Get faker generator for field"""
        if field.type == "str":
            if "email" in field.name.lower():
                return "return fake.email()"
            elif "name" in field.name.lower():
                return "return fake.name()"
            elif "description" in field.name.lower():
                return "return fake.text(max_nb_chars=200)"
            else:
                return "return fake.word()"
        elif field.type == "int":
            return "return fake.random_int(min=1, max=1000)"
        elif field.type == "float":
            return "return round(fake.random.uniform(0.1, 100.0), 2)"
        elif field.type == "bool":
            return "return fake.boolean()"
        elif field.type == "datetime":
            return "return fake.date_time_this_year()"
        else:
            return f'return "fake_{field.name}"'
    
    def _get_invalid_value(self, field: FieldConfig) -> str:
        """Get invalid value for testing"""
        if field.type == "str":
            return '""'  # Empty string
        elif field.type == "int":
            return '""'  # String instead of int
        elif field.type == "float":
            return '"not_a_float"'
        elif field.type == "bool":
            return '"not_a_bool"'
        else:
            return "None"
    
    def _generate_tests(self, config: EntityConfig) -> str:
        """Generate unit tests"""
        return f'''"""
Unit tests for {config.name} Entity
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.{config.name.lower()} import {config.name}
from src.factories.{config.name.lower()}_factory import {config.name}Factory


class Test{config.name}:
    """Test suite for {config.name} entity"""
    
    def test_create_valid_entity(self):
        """Test creating valid entity"""
        entity = {config.name}Factory.create()
        
        assert isinstance(entity, {config.name})
        assert entity.id is not None
        {chr(10).join([f'        assert entity.{field.name} is not None' for field in config.fields if field.required and field.name != 'id'])}
    
    def test_entity_with_minimal_fields(self):
        """Test creating entity with minimal required fields"""
        entity = {config.name}Factory.create_minimal()
        
        assert isinstance(entity, {config.name})
        assert entity.id is not None
    
    def test_entity_validation_errors(self):
        """Test validation errors"""
        invalid_data = {config.name}Factory.create_with_validation_errors()
        
        with pytest.raises(ValidationError):
            {config.name}(**invalid_data)
    
    def test_to_dict_conversion(self):
        """Test converting entity to dictionary"""
        entity = {config.name}Factory.create()
        entity_dict = entity.to_dict()
        
        assert isinstance(entity_dict, dict)
        assert "id" in entity_dict
        {chr(10).join([f'        assert "{field.name}" in entity_dict' for field in config.fields if field.required])}
    
    def test_dynamodb_conversion(self):
        """Test DynamoDB conversion"""
        entity = {config.name}Factory.create()
        
        # Test to DynamoDB format
        dynamo_item = entity.to_dynamodb_item()
        assert "PK" in dynamo_item
        assert "SK" in dynamo_item
        assert "GSI1PK" in dynamo_item
        assert "GSI1SK" in dynamo_item
        assert dynamo_item["entity_type"] == "{config.name.lower()}"
        
        # Test from DynamoDB format
        restored_entity = {config.name}.from_dynamodb_item(dynamo_item)
        assert restored_entity.id == entity.id
        {chr(10).join([f'        assert restored_entity.{field.name} == entity.{field.name}' for field in config.fields[:3] if field.name != 'id'])}
    
    {'def test_timestamp_updates(self):' if config.has_timestamps else ''}
    {'    """Test timestamp functionality"""' if config.has_timestamps else ''}
    {'    entity = {config.name}Factory.create()' if config.has_timestamps else ''}
    {'    original_updated = entity.updated_at' if config.has_timestamps else ''}
    {'    ' if config.has_timestamps else ''}
    {'    # Update timestamp' if config.has_timestamps else ''}
    {'    entity.update_timestamp()' if config.has_timestamps else ''}
    {'    ' if config.has_timestamps else ''}
    {'    assert entity.updated_at > original_updated' if config.has_timestamps else ''}
    
    {'def test_soft_delete(self):' if config.has_soft_delete else ''}
    {'    """Test soft delete functionality"""' if config.has_soft_delete else ''}
    {'    entity = {config.name}Factory.create()' if config.has_soft_delete else ''}
    {'    assert not entity.is_deleted' if config.has_soft_delete else ''}
    {'    ' if config.has_soft_delete else ''}
    {'    entity.mark_deleted()' if config.has_soft_delete else ''}
    {'    assert entity.is_deleted' if config.has_soft_delete else ''}
    {'    assert entity.deleted_at is not None' if config.has_soft_delete else ''}
    
    def test_string_representations(self):
        """Test string representations"""
        entity = {config.name}Factory.create()
        
        str_repr = str(entity)
        assert "{config.name}" in str_repr
        assert entity.id in str_repr
        
        repr_str = repr(entity)
        assert "{config.name}" in repr_str
        assert entity.id in repr_str
    
    def test_field_validation(self):
        """Test individual field validation"""
        {chr(10).join([self._generate_field_test(field, config) for field in config.fields if field.validation])}
    
    def test_batch_creation(self):
        """Test creating multiple entities"""
        entities = {config.name}Factory.create_batch(5)
        
        assert len(entities) == 5
        assert all(isinstance(e, {config.name}) for e in entities)
        assert len(set(e.id for e in entities)) == 5  # All unique IDs
    
    def test_config_settings(self):
        """Test Pydantic config settings"""
        entity = {config.name}Factory.create()
        
        # Test JSON encoding
        json_dict = entity.dict()
        assert isinstance(json_dict, dict)
        
        # Test validation on assignment
        {'with pytest.raises(ValidationError):' if config.fields else ''}
        {'    entity.{} = "invalid_value"'.format(config.fields[0].name) if config.fields and config.fields[0].type != 'str' else ''}
'''
    
    def _generate_field_test(self, field: FieldConfig, config: EntityConfig) -> str:
        """Generate test for field validation"""
        if not field.validation:
            return ""
        
        test_lines = []
        if "min_length" in field.validation:
            min_len = field.validation["min_length"]
            test_lines.append(f'''        # Test {field.name} minimum length
        with pytest.raises(ValidationError):
            {config.name}({field.name}="{'x' * (min_len - 1)}")''')
        
        if "pattern" in field.validation:
            test_lines.append(f'''        # Test {field.name} pattern validation
        with pytest.raises(ValidationError):
            {config.name}({field.name}="invalid_pattern")''')
        
        return chr(10).join(test_lines)
    
    def _generate_migration(self, config: EntityConfig) -> str:
        """Generate database migration"""
        return f'''"""
Migration: Create {config.name} table

Generated on: {datetime.now().isoformat()}
"""

from datetime import datetime
from typing import Dict, Any


class Create{config.name}Table:
    """Migration to create {config.name.lower()} table"""
    
    def up(self) -> Dict[str, Any]:
        """Apply migration"""
        return {{
            "TableName": "{config.table_name or config.name.lower()}",
            "KeySchema": [
                {{"AttributeName": "PK", "KeyType": "HASH"}},
                {{"AttributeName": "SK", "KeyType": "RANGE"}}
            ],
            "AttributeDefinitions": [
                {{"AttributeName": "PK", "AttributeType": "S"}},
                {{"AttributeName": "SK", "AttributeType": "S"}},
                {{"AttributeName": "GSI1PK", "AttributeType": "S"}},
                {{"AttributeName": "GSI1SK", "AttributeType": "S"}}
            ],
            "GlobalSecondaryIndexes": [
                {{
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {{"AttributeName": "GSI1PK", "KeyType": "HASH"}},
                        {{"AttributeName": "GSI1SK", "KeyType": "RANGE"}}
                    ],
                    "Projection": {{"ProjectionType": "ALL"}},
                    "ProvisionedThroughput": {{
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }}
                }}
            ],
            "ProvisionedThroughput": {{
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            }},
            "Tags": [
                {{"Key": "Entity", "Value": "{config.name}"}},
                {{"Key": "Environment", "Value": "development"}},
                {{"Key": "CreatedBy", "Value": "EntityGenerator"}}
            ]
        }}
    
    def down(self) -> str:
        """Rollback migration"""
        return "{config.table_name or config.name.lower()}"
    
    def description(self) -> str:
        """Migration description"""
        return "Create {config.name.lower()} table with standard schema"


# Export migration class
migration = Create{config.name}Table()
'''
    
    def create_files(self, files: Dict[str, str]) -> None:
        """Create the generated files"""
        for file_path, content in files.items():
            full_path = self.project_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            print(f"✅ Created: {file_path}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Generate entity implementation")
    parser.add_argument("name", help="Entity name (e.g., UserProfile)")
    parser.add_argument("--description", default="Entity description", help="Entity description")
    parser.add_argument("--table", help="DynamoDB table name")
    parser.add_argument("--fields", required=True, help="Fields as JSON: [{'name':'field1','type':'str','required':true}]")
    parser.add_argument("--no-timestamps", action="store_true", help="Skip timestamp fields")
    parser.add_argument("--soft-delete", action="store_true", help="Include soft delete")
    parser.add_argument("--audit", action="store_true", help="Include audit fields")
    
    args = parser.parse_args()
    
    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir
    while project_root.parent != project_root:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent
    
    # Parse fields
    import json
    try:
        fields_data = json.loads(args.fields)
        fields = [FieldConfig(**field) for field in fields_data]
    except Exception as e:
        print(f"❌ Error parsing fields: {e}")
        print("Example: '[{\"name\":\"title\",\"type\":\"str\",\"required\":true,\"description\":\"Title field\"}]'")
        return
    
    # Create entity configuration
    config = EntityConfig(
        name=args.name,
        description=args.description,
        fields=fields,
        table_name=args.table,
        has_timestamps=not args.no_timestamps,
        has_soft_delete=args.soft_delete,
        has_audit=args.audit
    )
    
    # Generate entity
    generator = EntityGenerator(project_root)
    files = generator.generate_entity(config)
    generator.create_files(files)
    
    print(f"\\n🚀 Generated {args.name} entity!")
    print(f"📁 Files created: {len(files)}")
    print("\\n📝 Next steps:")
    print(f"1. Review the generated model: src/models/{args.name.lower()}.py")
    print(f"2. Run the tests: pytest tests/unit/test_{args.name.lower()}_model.py")
    print(f"3. If you created a migration, run it to create the table")
    print(f"4. Add the entity to your service layer")


if __name__ == "__main__":
    main()
