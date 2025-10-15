#!/usr/bin/env python3
"""
Service Generator for AI Nutritionist

Generates complete service classes with:
- Domain service implementation
- Interface definition
- Repository pattern
- Dependency injection
- Unit tests
- Integration tests
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ServiceConfig:
    """Configuration for service generation"""
    name: str
    domain: str
    description: str
    dependencies: List[str]
    has_repository: bool = True
    has_cache: bool = False
    has_events: bool = False
    has_validation: bool = True


class ServiceGenerator:
    """Generates complete service implementations"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.templates_dir = project_root / "dev-tools" / "templates"
        
    def generate_service(self, config: ServiceConfig) -> Dict[str, str]:
        """Generate complete service implementation"""
        files = {}
        
        # Generate service interface
        files[f"src/core/interfaces/{config.name.lower()}_interface.py"] = self._generate_interface(config)
        
        # Generate service implementation
        files[f"src/services/{config.domain}/{config.name.lower()}_service.py"] = self._generate_service_impl(config)
        
        # Generate repository if needed
        if config.has_repository:
            files[f"src/adapters/{config.name.lower()}_repository.py"] = self._generate_repository(config)
        
        # Generate unit tests
        files[f"tests/unit/test_{config.name.lower()}_service.py"] = self._generate_unit_tests(config)
        
        # Generate integration tests
        files[f"tests/integration/test_{config.name.lower()}_integration.py"] = self._generate_integration_tests(config)
        
        # Update domain __init__.py
        files[f"src/services/{config.domain}/__init__.py"] = self._update_domain_init(config)
        
        return files
    
    def _generate_interface(self, config: ServiceConfig) -> str:
        """Generate service interface"""
        return f'''"""
{config.name} Service Interface

{config.description}
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...models.base import BaseEntity


class {config.name}ServiceInterface(ABC):
    """Interface for {config.name.lower()} service operations"""
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> BaseEntity:
        """Create new {config.name.lower()} entity"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[BaseEntity]:
        """Get {config.name.lower()} by ID"""
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, data: Dict[str, Any]) -> BaseEntity:
        """Update {config.name.lower()} entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete {config.name.lower()} entity"""
        pass
    
    @abstractmethod
    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[BaseEntity]:
        """List {config.name.lower()} entities with optional filters"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Health check for {config.name.lower()} service"""
        pass
'''
    
    def _generate_service_impl(self, config: ServiceConfig) -> str:
        """Generate service implementation"""
        imports = [
            "import logging",
            "from typing import Any, Dict, List, Optional",
            "from datetime import datetime",
            "",
            f"from ...core.interfaces.{config.name.lower()}_interface import {config.name}ServiceInterface",
            "from ...models.base import BaseEntity",
        ]
        
        if config.has_repository:
            imports.append(f"from ...adapters.{config.name.lower()}_repository import {config.name}Repository")
        
        if config.has_cache:
            imports.append("from ...services.infrastructure.caching import AdvancedCachingService")
        
        if config.has_events:
            imports.append("from ...services.infrastructure.events import EventPublisher")
        
        if config.has_validation:
            imports.append("from ...utils.validation import validate_input")
        
        dependency_params = []
        dependency_inits = []
        
        if config.has_repository:
            dependency_params.append(f"{config.name.lower()}_repository: {config.name}Repository")
            dependency_inits.append(f"        self.repository = {config.name.lower()}_repository")
        
        if config.has_cache:
            dependency_params.append("cache_service: AdvancedCachingService")
            dependency_inits.append("        self.cache = cache_service")
        
        if config.has_events:
            dependency_params.append("event_publisher: EventPublisher")
            dependency_inits.append("        self.events = event_publisher")
        
        return f'''"""
{config.name} Service Implementation

{config.description}
"""

{chr(10).join(imports)}

logger = logging.getLogger(__name__)


class {config.name}Service({config.name}ServiceInterface):
    """
    {config.name} service implementation
    
    Provides {config.description.lower()}
    """
    
    def __init__(
        self,
        {f",{chr(10)}        ".join(dependency_params)}
    ):
        """Initialize {config.name.lower()} service"""
        self.logger = logger
{chr(10).join(dependency_inits)}
    
    async def create(self, data: Dict[str, Any]) -> BaseEntity:
        """Create new {config.name.lower()} entity"""
        try:
            self.logger.info(f"Creating new {config.name.lower()}", extra={{"data_keys": list(data.keys())}})
            
            {'# Validate input' if config.has_validation else ''}
            {'validated_data = validate_input(data, self._get_creation_schema())' if config.has_validation else 'validated_data = data'}
            
            {'# Create in repository' if config.has_repository else ''}
            {'entity = await self.repository.create(validated_data)' if config.has_repository else 'entity = BaseEntity(**validated_data)'}
            
            {'# Cache if enabled' if config.has_cache else ''}
            {'await self.cache.set(f"{config.name.lower()}_{{entity.id}}", entity)' if config.has_cache else ''}
            
            {'# Publish event if enabled' if config.has_events else ''}
            {'await self.events.publish("{config.name.lower()}.created", entity)' if config.has_events else ''}
            
            self.logger.info(f"{config.name} created successfully", extra={{"entity_id": entity.id}})
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to create {config.name.lower()}", extra={{"error": str(e)}})
            raise
    
    async def get_by_id(self, entity_id: str) -> Optional[BaseEntity]:
        """Get {config.name.lower()} by ID"""
        try:
            {'# Check cache first' if config.has_cache else ''}
            {'cached = await self.cache.get(f"{config.name.lower()}_{{entity_id}}")' if config.has_cache else ''}
            {'if cached:' if config.has_cache else ''}
            {'    return cached' if config.has_cache else ''}
            
            {'# Get from repository' if config.has_repository else ''}
            {'entity = await self.repository.get_by_id(entity_id)' if config.has_repository else 'entity = None'}
            
            {'# Cache result' if config.has_cache else ''}
            {'if entity:' if config.has_cache else ''}
            {'    await self.cache.set(f"{config.name.lower()}_{{entity_id}}", entity)' if config.has_cache else ''}
            
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to get {config.name.lower()}", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def update(self, entity_id: str, data: Dict[str, Any]) -> BaseEntity:
        """Update {config.name.lower()} entity"""
        try:
            self.logger.info(f"Updating {config.name.lower()}", extra={{"entity_id": entity_id}})
            
            {'# Validate input' if config.has_validation else ''}
            {'validated_data = validate_input(data, self._get_update_schema())' if config.has_validation else 'validated_data = data'}
            
            {'# Update in repository' if config.has_repository else ''}
            {'entity = await self.repository.update(entity_id, validated_data)' if config.has_repository else 'entity = BaseEntity(**validated_data)'}
            
            {'# Invalidate cache' if config.has_cache else ''}
            {'await self.cache.delete(f"{config.name.lower()}_{{entity_id}}")' if config.has_cache else ''}
            
            {'# Publish event' if config.has_events else ''}
            {'await self.events.publish("{config.name.lower()}.updated", entity)' if config.has_events else ''}
            
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to update {config.name.lower()}", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def delete(self, entity_id: str) -> bool:
        """Delete {config.name.lower()} entity"""
        try:
            self.logger.info(f"Deleting {config.name.lower()}", extra={{"entity_id": entity_id}})
            
            {'# Delete from repository' if config.has_repository else ''}
            {'success = await self.repository.delete(entity_id)' if config.has_repository else 'success = True'}
            
            {'# Invalidate cache' if config.has_cache else ''}
            {'await self.cache.delete(f"{config.name.lower()}_{{entity_id}}")' if config.has_cache else ''}
            
            {'# Publish event' if config.has_events else ''}
            {'if success:' if config.has_events else ''}
            {'    await self.events.publish("{config.name.lower()}.deleted", {{"entity_id": entity_id}})' if config.has_events else ''}
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete {config.name.lower()}", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[BaseEntity]:
        """List {config.name.lower()} entities with optional filters"""
        try:
            self.logger.info(f"Listing {config.name.lower()} entities", extra={{"filters": filters}})
            
            {'# Get from repository' if config.has_repository else ''}
            {'entities = await self.repository.list(filters)' if config.has_repository else 'entities = []'}
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to list {config.name.lower()}", extra={{"error": str(e)}})
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for {config.name.lower()} service"""
        checks = {{}}
        
        {'# Check repository health' if config.has_repository else ''}
        {'try:' if config.has_repository else ''}
        {'    await self.repository.health_check()' if config.has_repository else ''}
        {'    checks["repository"] = "healthy"' if config.has_repository else ''}
        {'except:' if config.has_repository else ''}
        {'    checks["repository"] = "unhealthy"' if config.has_repository else ''}
        
        {'# Check cache health' if config.has_cache else ''}
        {'try:' if config.has_cache else ''}
        {'    await self.cache.health_check()' if config.has_cache else ''}
        {'    checks["cache"] = "healthy"' if config.has_cache else ''}
        {'except:' if config.has_cache else ''}
        {'    checks["cache"] = "unhealthy"' if config.has_cache else ''}
        
        overall_status = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
        
        return {{
            "service": "{config.name.lower()}",
            "status": overall_status,
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        }}
    
    {'def _get_creation_schema(self) -> Dict[str, Any]:' if config.has_validation else ''}
    {'    """Get validation schema for creation"""' if config.has_validation else ''}
    {'    return {{' if config.has_validation else ''}
    {'        "type": "object",' if config.has_validation else ''}
    {'        "properties": {{' if config.has_validation else ''}
    {'            # Add your validation schema here' if config.has_validation else ''}
    {'        }},' if config.has_validation else ''}
    {'        "required": []' if config.has_validation else ''}
    {'    }}' if config.has_validation else ''}
    {'    ' if config.has_validation else ''}
    {'def _get_update_schema(self) -> Dict[str, Any]:' if config.has_validation else ''}
    {'    """Get validation schema for updates"""' if config.has_validation else ''}
    {'    return {{' if config.has_validation else ''}
    {'        "type": "object",' if config.has_validation else ''}
    {'        "properties": {{' if config.has_validation else ''}
    {'            # Add your validation schema here' if config.has_validation else ''}
    {'        }}' if config.has_validation else ''}
    {'    }}' if config.has_validation else ''}
'''
    
    def _generate_repository(self, config: ServiceConfig) -> str:
        """Generate repository implementation"""
        return f'''"""
{config.name} Repository Implementation

DynamoDB repository for {config.name.lower()} entities
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key, Attr

from ..models.base import BaseEntity
from ..config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class {config.name}Repository:
    """
    DynamoDB repository for {config.name} entities
    
    Table Design:
    - PK: {config.name.upper()}_{{entity_id}}
    - SK: {config.name.upper()}_{{entity_id}}
    - GSI1: type#{config.name.lower()}
    """
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
        self.logger = logger
    
    async def create(self, data: Dict[str, Any]) -> BaseEntity:
        """Create new {config.name.lower()} entity"""
        try:
            entity_id = data.get('id') or f"{config.name.lower()}_{{datetime.now().timestamp()}}"
            
            item = {{
                'PK': f'{config.name.upper()}_{{entity_id}}',
                'SK': f'{config.name.upper()}_{{entity_id}}',
                'GSI1PK': f'type#{config.name.lower()}',
                'GSI1SK': entity_id,
                'entity_type': '{config.name.lower()}',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                **data
            }}
            
            self.table.put_item(Item=item)
            
            entity = BaseEntity(**item)
            self.logger.info(f"{config.name} created in DynamoDB", extra={{"entity_id": entity_id}})
            
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to create {config.name.lower()} in DynamoDB", extra={{"error": str(e)}})
            raise
    
    async def get_by_id(self, entity_id: str) -> Optional[BaseEntity]:
        """Get {config.name.lower()} by ID"""
        try:
            response = self.table.get_item(
                Key={{
                    'PK': f'{config.name.upper()}_{{entity_id}}',
                    'SK': f'{config.name.upper()}_{{entity_id}}'
                }}
            )
            
            if 'Item' not in response:
                return None
            
            return BaseEntity(**response['Item'])
            
        except Exception as e:
            self.logger.error(f"Failed to get {config.name.lower()} from DynamoDB", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def update(self, entity_id: str, data: Dict[str, Any]) -> BaseEntity:
        """Update {config.name.lower()} entity"""
        try:
            # Build update expression
            update_expression = "SET updated_at = :updated_at"
            expression_values = {{":updated_at": datetime.now().isoformat()}}
            
            for key, value in data.items():
                if key not in ['PK', 'SK', 'entity_type', 'created_at']:
                    update_expression += f", {key} = :{key}"
                    expression_values[f":{key}"] = value
            
            response = self.table.update_item(
                Key={{
                    'PK': f'{config.name.upper()}_{{entity_id}}',
                    'SK': f'{config.name.upper()}_{{entity_id}}'
                }},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            return BaseEntity(**response['Attributes'])
            
        except Exception as e:
            self.logger.error(f"Failed to update {config.name.lower()} in DynamoDB", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def delete(self, entity_id: str) -> bool:
        """Delete {config.name.lower()} entity"""
        try:
            self.table.delete_item(
                Key={{
                    'PK': f'{config.name.upper()}_{{entity_id}}',
                    'SK': f'{config.name.upper()}_{{entity_id}}'
                }}
            )
            
            self.logger.info(f"{config.name} deleted from DynamoDB", extra={{"entity_id": entity_id}})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete {config.name.lower()} from DynamoDB", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[BaseEntity]:
        """List {config.name.lower()} entities with optional filters"""
        try:
            # Query by GSI to get all entities of this type
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=Key('GSI1PK').eq(f'type#{config.name.lower()}')
            )
            
            entities = [BaseEntity(**item) for item in response['Items']]
            
            # Apply filters if provided
            if filters:
                entities = self._apply_filters(entities, filters)
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to list {config.name.lower()} from DynamoDB", extra={{"error": str(e)}})
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for repository"""
        try:
            # Try to describe table
            self.table.load()
            return {{"status": "healthy", "table": self.table.table_name}}
        except Exception as e:
            return {{"status": "unhealthy", "error": str(e)}}
    
    def _apply_filters(self, entities: List[BaseEntity], filters: Dict[str, Any]) -> List[BaseEntity]:
        """Apply filters to entity list"""
        filtered = entities
        
        for key, value in filters.items():
            filtered = [e for e in filtered if getattr(e, key, None) == value]
        
        return filtered
'''
    
    def _generate_unit_tests(self, config: ServiceConfig) -> str:
        """Generate unit tests"""
        return f'''"""
Unit tests for {config.name} Service
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.services.{config.domain}.{config.name.lower()}_service import {config.name}Service
from src.models.base import BaseEntity


class Test{config.name}Service:
    """Test suite for {config.name}Service"""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository"""
        return Mock()
    
    {'@pytest.fixture' if config.has_cache else ''}
    {'def mock_cache(self):' if config.has_cache else ''}
    {'    """Mock cache service"""' if config.has_cache else ''}
    {'    return Mock()' if config.has_cache else ''}
    
    {'@pytest.fixture' if config.has_events else ''}
    {'def mock_events(self):' if config.has_events else ''}
    {'    """Mock event publisher"""' if config.has_events else ''}
    {'    return Mock()' if config.has_events else ''}
    
    @pytest.fixture
    def service(self, mock_repository{', mock_cache' if config.has_cache else ''}{', mock_events' if config.has_events else ''}):
        """Create service instance"""
        return {config.name}Service(
            {config.name.lower()}_repository=mock_repository{f',{chr(10)}            cache_service=mock_cache' if config.has_cache else ''}{f',{chr(10)}            event_publisher=mock_events' if config.has_events else ''}
        )
    
    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_repository):
        """Test successful entity creation"""
        # Arrange
        test_data = {{"name": "test_{config.name.lower()}", "description": "Test description"}}
        expected_entity = BaseEntity(id="test_id", **test_data)
        mock_repository.create = AsyncMock(return_value=expected_entity)
        
        # Act
        result = await service.create(test_data)
        
        # Assert
        assert result == expected_entity
        mock_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, service, mock_repository):
        """Test successful entity retrieval"""
        # Arrange
        entity_id = "test_id"
        expected_entity = BaseEntity(id=entity_id, name="test_{config.name.lower()}")
        mock_repository.get_by_id = AsyncMock(return_value=expected_entity)
        
        # Act
        result = await service.get_by_id(entity_id)
        
        # Assert
        assert result == expected_entity
        mock_repository.get_by_id.assert_called_once_with(entity_id)
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_repository):
        """Test entity not found"""
        # Arrange
        entity_id = "nonexistent_id"
        mock_repository.get_by_id = AsyncMock(return_value=None)
        
        # Act
        result = await service.get_by_id(entity_id)
        
        # Assert
        assert result is None
        mock_repository.get_by_id.assert_called_once_with(entity_id)
    
    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_repository):
        """Test successful entity update"""
        # Arrange
        entity_id = "test_id"
        update_data = {{"name": "updated_name"}}
        expected_entity = BaseEntity(id=entity_id, **update_data)
        mock_repository.update = AsyncMock(return_value=expected_entity)
        
        # Act
        result = await service.update(entity_id, update_data)
        
        # Assert
        assert result == expected_entity
        mock_repository.update.assert_called_once_with(entity_id, update_data)
    
    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_repository):
        """Test successful entity deletion"""
        # Arrange
        entity_id = "test_id"
        mock_repository.delete = AsyncMock(return_value=True)
        
        # Act
        result = await service.delete(entity_id)
        
        # Assert
        assert result is True
        mock_repository.delete.assert_called_once_with(entity_id)
    
    @pytest.mark.asyncio
    async def test_list_success(self, service, mock_repository):
        """Test successful entity listing"""
        # Arrange
        expected_entities = [
            BaseEntity(id="1", name="entity_1"),
            BaseEntity(id="2", name="entity_2")
        ]
        mock_repository.list = AsyncMock(return_value=expected_entities)
        
        # Act
        result = await service.list()
        
        # Assert
        assert result == expected_entities
        mock_repository.list.assert_called_once_with(None)
    
    @pytest.mark.asyncio
    async def test_list_with_filters(self, service, mock_repository):
        """Test entity listing with filters"""
        # Arrange
        filters = {{"status": "active"}}
        expected_entities = [BaseEntity(id="1", name="entity_1", status="active")]
        mock_repository.list = AsyncMock(return_value=expected_entities)
        
        # Act
        result = await service.list(filters)
        
        # Assert
        assert result == expected_entities
        mock_repository.list.assert_called_once_with(filters)
    
    @pytest.mark.asyncio
    async def test_health_check(self, service, mock_repository):
        """Test service health check"""
        # Arrange
        mock_repository.health_check = AsyncMock(return_value={{"status": "healthy"}})
        
        # Act
        result = await service.health_check()
        
        # Assert
        assert result["service"] == "{config.name.lower()}"
        assert "status" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_create_repository_error(self, service, mock_repository):
        """Test repository error handling"""
        # Arrange
        test_data = {{"name": "test_{config.name.lower()}"}}
        mock_repository.create = AsyncMock(side_effect=Exception("Repository error"))
        
        # Act & Assert
        with pytest.raises(Exception, match="Repository error"):
            await service.create(test_data)
'''
    
    def _generate_integration_tests(self, config: ServiceConfig) -> str:
        """Generate integration tests"""
        return f'''"""
Integration tests for {config.name} Service
"""

import pytest
import boto3
from moto import mock_dynamodb
from datetime import datetime

from src.services.{config.domain}.{config.name.lower()}_service import {config.name}Service
from src.adapters.{config.name.lower()}_repository import {config.name}Repository
from src.config.settings import get_settings


@mock_dynamodb
class Test{config.name}ServiceIntegration:
    """Integration test suite for {config.name}Service"""
    
    @pytest.fixture(autouse=True)
    def setup_dynamodb(self):
        """Setup DynamoDB table for testing"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        table = dynamodb.create_table(
            TableName=get_settings().DYNAMODB_TABLE_NAME,
            KeySchema=[
                {{'AttributeName': 'PK', 'KeyType': 'HASH'}},
                {{'AttributeName': 'SK', 'KeyType': 'RANGE'}}
            ],
            AttributeDefinitions=[
                {{'AttributeName': 'PK', 'AttributeType': 'S'}},
                {{'AttributeName': 'SK', 'AttributeType': 'S'}},
                {{'AttributeName': 'GSI1PK', 'AttributeType': 'S'}},
                {{'AttributeName': 'GSI1SK', 'AttributeType': 'S'}}
            ],
            GlobalSecondaryIndexes=[
                {{
                    'IndexName': 'GSI1',
                    'KeySchema': [
                        {{'AttributeName': 'GSI1PK', 'KeyType': 'HASH'}},
                        {{'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}}
                    ],
                    'Projection': {{'ProjectionType': 'ALL'}},
                    'ProvisionedThroughput': {{
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }}
                }}
            ],
            ProvisionedThroughput={{
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }}
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        
        self.table = table
        
        # Create service with real repository
        repository = {config.name}Repository()
        self.service = {config.name}Service(
            {config.name.lower()}_repository=repository
        )
    
    @pytest.mark.asyncio
    async def test_full_crud_workflow(self):
        """Test complete CRUD workflow"""
        # Create
        create_data = {{
            "name": "integration_test_{config.name.lower()}",
            "description": "Integration test description",
            "status": "active"
        }}
        
        created_entity = await self.service.create(create_data)
        assert created_entity.name == create_data["name"]
        assert created_entity.status == "active"
        entity_id = created_entity.id
        
        # Read
        retrieved_entity = await self.service.get_by_id(entity_id)
        assert retrieved_entity is not None
        assert retrieved_entity.name == create_data["name"]
        
        # Update
        update_data = {{"status": "updated", "description": "Updated description"}}
        updated_entity = await self.service.update(entity_id, update_data)
        assert updated_entity.status == "updated"
        assert updated_entity.description == "Updated description"
        
        # List
        entities = await self.service.list()
        assert len(entities) >= 1
        assert any(e.id == entity_id for e in entities)
        
        # List with filters
        active_entities = await self.service.list({{"status": "updated"}})
        assert len(active_entities) >= 1
        
        # Delete
        delete_result = await self.service.delete(entity_id)
        assert delete_result is True
        
        # Verify deletion
        deleted_entity = await self.service.get_by_id(entity_id)
        assert deleted_entity is None
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent operations"""
        import asyncio
        
        # Create multiple entities concurrently
        tasks = []
        for i in range(5):
            data = {{
                "name": f"concurrent_test_{{i}}",
                "description": f"Concurrent test {{i}}",
                "status": "active"
            }}
            tasks.append(self.service.create(data))
        
        entities = await asyncio.gather(*tasks)
        assert len(entities) == 5
        
        # Verify all were created
        all_entities = await self.service.list()
        concurrent_entities = [e for e in all_entities if e.name.startswith("concurrent_test_")]
        assert len(concurrent_entities) == 5
    
    @pytest.mark.asyncio
    async def test_service_health_check(self):
        """Test service health check"""
        health = await self.service.health_check()
        
        assert health["service"] == "{config.name.lower()}"
        assert health["status"] in ["healthy", "degraded"]
        assert "timestamp" in health
        assert "checks" in health
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling scenarios"""
        # Test getting non-existent entity
        result = await self.service.get_by_id("non_existent_id")
        assert result is None
        
        # Test updating non-existent entity
        with pytest.raises(Exception):
            await self.service.update("non_existent_id", {{"name": "updated"}})
    
    @pytest.mark.asyncio
    async def test_large_dataset_operations(self):
        """Test operations with larger datasets"""
        # Create multiple entities
        entities = []
        for i in range(20):
            data = {{
                "name": f"bulk_test_{{i}}",
                "description": f"Bulk test entity {{i}}",
                "status": "active" if i % 2 == 0 else "inactive"
            }}
            entity = await self.service.create(data)
            entities.append(entity)
        
        # Test listing all
        all_entities = await self.service.list()
        bulk_entities = [e for e in all_entities if e.name.startswith("bulk_test_")]
        assert len(bulk_entities) == 20
        
        # Test filtering
        active_entities = await self.service.list({{"status": "active"}})
        active_bulk = [e for e in active_entities if e.name.startswith("bulk_test_")]
        assert len(active_bulk) == 10
        
        # Cleanup
        for entity in entities:
            await self.service.delete(entity.id)
'''
    
    def _update_domain_init(self, config: ServiceConfig) -> str:
        """Generate domain __init__.py update"""
        return f'''"""
{config.domain.title()} Domain Services
"""

from .{config.name.lower()}_service import {config.name}Service

__all__ = [
    '{config.name}Service'
]
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
    parser = argparse.ArgumentParser(description="Generate service implementation")
    parser.add_argument("name", help="Service name (e.g., UserProfile)")
    parser.add_argument("domain", help="Domain name (e.g., nutrition)")
    parser.add_argument("--description", default="Service description", help="Service description")
    parser.add_argument("--dependencies", nargs="*", default=[], help="Service dependencies")
    parser.add_argument("--no-repository", action="store_true", help="Skip repository generation")
    parser.add_argument("--cache", action="store_true", help="Include caching")
    parser.add_argument("--events", action="store_true", help="Include event publishing")
    parser.add_argument("--no-validation", action="store_true", help="Skip input validation")
    
    args = parser.parse_args()
    
    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir
    while project_root.parent != project_root:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent
    
    # Create service configuration
    config = ServiceConfig(
        name=args.name,
        domain=args.domain,
        description=args.description,
        dependencies=args.dependencies,
        has_repository=not args.no_repository,
        has_cache=args.cache,
        has_events=args.events,
        has_validation=not args.no_validation
    )
    
    # Generate service
    generator = ServiceGenerator(project_root)
    files = generator.generate_service(config)
    generator.create_files(files)
    
    print(f"\\n🚀 Generated {args.name} service in {args.domain} domain!")
    print(f"📁 Files created: {len(files)}")
    print("\\n📝 Next steps:")
    print(f"1. Review and customize the generated service: src/services/{args.domain}/{args.name.lower()}_service.py")
    print(f"2. Run the tests: pytest tests/unit/test_{args.name.lower()}_service.py")
    print(f"3. Add the service to your dependency injection container")
    print(f"4. Update the API layer to use the new service")


if __name__ == "__main__":
    main()
