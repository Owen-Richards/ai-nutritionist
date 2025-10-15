#!/usr/bin/env python3
"""
Repository Generator for AI Nutritionist

Generates complete repository implementations with:
- DynamoDB repository implementation
- Repository interface
- Caching layer integration
- Query builders
- Unit tests
- Integration tests
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QueryConfig:
    """Configuration for repository queries"""
    name: str
    description: str
    parameters: List[str]
    return_type: str = "List[Entity]"
    is_single: bool = False


@dataclass
class RepositoryConfig:
    """Configuration for repository generation"""
    name: str
    entity_name: str
    description: str
    table_name: str
    has_cache: bool = True
    has_pagination: bool = True
    has_filtering: bool = True
    custom_queries: List[QueryConfig] = None


class RepositoryGenerator:
    """Generates complete repository implementations"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    def generate_repository(self, config: RepositoryConfig) -> Dict[str, str]:
        """Generate complete repository implementation"""
        files = {}
        
        # Generate repository interface
        files[f"src/core/interfaces/{config.name.lower()}_repository_interface.py"] = self._generate_interface(config)
        
        # Generate DynamoDB repository implementation
        files[f"src/adapters/{config.name.lower()}_repository.py"] = self._generate_implementation(config)
        
        # Generate query builders
        files[f"src/adapters/query_builders/{config.name.lower()}_queries.py"] = self._generate_query_builders(config)
        
        # Generate unit tests
        files[f"tests/unit/test_{config.name.lower()}_repository.py"] = self._generate_unit_tests(config)
        
        # Generate integration tests
        files[f"tests/integration/test_{config.name.lower()}_repository_integration.py"] = self._generate_integration_tests(config)
        
        return files
    
    def _generate_interface(self, config: RepositoryConfig) -> str:
        """Generate repository interface"""
        custom_methods = ""
        if config.custom_queries:
            custom_methods = chr(10).join([
                f'''    @abstractmethod
    async def {query.name}(self, {", ".join(f"{param}: Any" for param in query.parameters)}) -> {query.return_type}:
        """{query.description}"""
        pass
''' for query in config.custom_queries
            ])
        
        return f'''"""
{config.name} Repository Interface

Interface for {config.entity_name} data persistence operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...models.{config.entity_name.lower()} import {config.entity_name}


class {config.name}RepositoryInterface(ABC):
    """Interface for {config.entity_name} repository operations"""
    
    @abstractmethod
    async def create(self, entity: {config.entity_name}) -> {config.entity_name}:
        """Create new entity"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[{config.entity_name}]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> {config.entity_name}:
        """Update entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity"""
        pass
    
    @abstractmethod
    async def list(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        {'page: int = 1,' if config.has_pagination else ''}
        {'size: int = 10,' if config.has_pagination else ''}
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> {'Dict[str, Any]' if config.has_pagination else f'List[{config.entity_name}]'}:
        """List entities with optional filtering and pagination"""
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching filters"""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        pass
    
    @abstractmethod
    async def bulk_create(self, entities: List[{config.entity_name}]) -> List[{config.entity_name}]:
        """Create multiple entities in batch"""
        pass
    
    @abstractmethod
    async def bulk_delete(self, entity_ids: List[str]) -> int:
        """Delete multiple entities in batch"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Repository health check"""
        pass
    
{custom_methods}
'''
    
    def _generate_implementation(self, config: RepositoryConfig) -> str:
        """Generate DynamoDB repository implementation"""
        cache_imports = ""
        cache_init = ""
        cache_methods = ""
        
        if config.has_cache:
            cache_imports = "from ..services.infrastructure.caching import AdvancedCachingService"
            cache_init = """        self.cache = cache_service or AdvancedCachingService()"""
            cache_methods = f'''
    async def _get_from_cache(self, cache_key: str) -> Optional[{config.entity_name}]:
        """Get entity from cache"""
        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return {config.entity_name}.from_dynamodb_item(cached_data)
            return None
        except Exception as e:
            self.logger.warning(f"Cache get failed: {{e}}")
            return None
    
    async def _set_cache(self, cache_key: str, entity: {config.entity_name}) -> None:
        """Set entity in cache"""
        try:
            await self.cache.set(cache_key, entity.to_dynamodb_item(), ttl=3600)
        except Exception as e:
            self.logger.warning(f"Cache set failed: {{e}}")
    
    async def _invalidate_cache(self, cache_key: str) -> None:
        """Invalidate cache entry"""
        try:
            await self.cache.delete(cache_key)
        except Exception as e:
            self.logger.warning(f"Cache invalidation failed: {{e}}")
'''
        
        custom_implementations = ""
        if config.custom_queries:
            custom_implementations = chr(10).join([
                self._generate_custom_query_implementation(query, config) for query in config.custom_queries
            ])
        
        return f'''"""
{config.name} DynamoDB Repository Implementation

DynamoDB repository for {config.entity_name} entities
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

from ..models.{config.entity_name.lower()} import {config.entity_name}
from ..core.interfaces.{config.name.lower()}_repository_interface import {config.name}RepositoryInterface
from ..config.settings import get_settings
{cache_imports}
from .query_builders.{config.name.lower()}_queries import {config.name}QueryBuilder

logger = logging.getLogger(__name__)
settings = get_settings()


class {config.name}Repository({config.name}RepositoryInterface):
    """
    DynamoDB repository for {config.entity_name} entities
    
    Table Schema:
    - PK: {config.entity_name.upper()}_{{entity_id}}
    - SK: {config.entity_name.upper()}_{{entity_id}}
    - GSI1: type#{config.entity_name.lower()} (for type-based queries)
    - GSI2: status#{{status}} (for status-based queries)
    """
    
    def __init__(self, {'cache_service: Optional[AdvancedCachingService] = None' if config.has_cache else ''}):
        """Initialize repository"""
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
        self.logger = logger
        self.query_builder = {config.name}QueryBuilder()
        self.serializer = TypeSerializer()
        self.deserializer = TypeDeserializer()
{cache_init}
    
    async def create(self, entity: {config.entity_name}) -> {config.entity_name}:
        """Create new entity"""
        try:
            item = entity.to_dynamodb_item()
            
            # Add conditional check to prevent overwrites
            self.table.put_item(
                Item=item,
                ConditionExpression=Attr('PK').not_exists()
            )
            
            {'# Cache the entity' if config.has_cache else ''}
            {'cache_key = f"{config.entity_name.lower()}:{{entity.id}}"' if config.has_cache else ''}
            {'await self._set_cache(cache_key, entity)' if config.has_cache else ''}
            
            self.logger.info(f"{config.entity_name} created", extra={{"entity_id": entity.id}})
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to create {config.entity_name.lower()}", extra={{"error": str(e)}})
            raise
    
    async def get_by_id(self, entity_id: str) -> Optional[{config.entity_name}]:
        """Get entity by ID"""
        try:
            {'# Check cache first' if config.has_cache else ''}
            {'cache_key = f"{config.entity_name.lower()}:{{entity_id}}"' if config.has_cache else ''}
            {'cached_entity = await self._get_from_cache(cache_key)' if config.has_cache else ''}
            {'if cached_entity:' if config.has_cache else ''}
            {'    return cached_entity' if config.has_cache else ''}
            
            # Query DynamoDB
            response = self.table.get_item(
                Key={{
                    'PK': f'{config.entity_name.upper()}_{{entity_id}}',
                    'SK': f'{config.entity_name.upper()}_{{entity_id}}'
                }}
            )
            
            if 'Item' not in response:
                return None
            
            entity = {config.entity_name}.from_dynamodb_item(response['Item'])
            
            {'# Cache the result' if config.has_cache else ''}
            {'await self._set_cache(cache_key, entity)' if config.has_cache else ''}
            
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to get {config.entity_name.lower()}", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> {config.entity_name}:
        """Update entity"""
        try:
            # Build update expression
            update_expr, expr_values, expr_names = self.query_builder.build_update_expression(updates)
            
            response = self.table.update_item(
                Key={{
                    'PK': f'{config.entity_name.upper()}_{{entity_id}}',
                    'SK': f'{config.entity_name.upper()}_{{entity_id}}'
                }},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names,
                ReturnValues='ALL_NEW'
            )
            
            entity = {config.entity_name}.from_dynamodb_item(response['Attributes'])
            
            {'# Invalidate cache' if config.has_cache else ''}
            {'cache_key = f"{config.entity_name.lower()}:{{entity_id}}"' if config.has_cache else ''}
            {'await self._invalidate_cache(cache_key)' if config.has_cache else ''}
            
            self.logger.info(f"{config.entity_name} updated", extra={{"entity_id": entity_id}})
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to update {config.entity_name.lower()}", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def delete(self, entity_id: str) -> bool:
        """Delete entity"""
        try:
            self.table.delete_item(
                Key={{
                    'PK': f'{config.entity_name.upper()}_{{entity_id}}',
                    'SK': f'{config.entity_name.upper()}_{{entity_id}}'
                }}
            )
            
            {'# Invalidate cache' if config.has_cache else ''}
            {'cache_key = f"{config.entity_name.lower()}:{{entity_id}}"' if config.has_cache else ''}
            {'await self._invalidate_cache(cache_key)' if config.has_cache else ''}
            
            self.logger.info(f"{config.entity_name} deleted", extra={{"entity_id": entity_id}})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete {config.entity_name.lower()}", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def list(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        {'page: int = 1,' if config.has_pagination else ''}
        {'size: int = 10,' if config.has_pagination else ''}
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> {'Dict[str, Any]' if config.has_pagination else f'List[{config.entity_name}]'}:
        """List entities with optional filtering and pagination"""
        try:
            query_params = self.query_builder.build_list_query(
                filters=filters,
                {'page=page,' if config.has_pagination else ''}
                {'size=size,' if config.has_pagination else ''}
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            response = self.table.query(**query_params)
            entities = [
                {config.entity_name}.from_dynamodb_item(item) 
                for item in response['Items']
            ]
            
            {'if config.has_pagination:' if config.has_pagination else ''}
            {'    # Calculate pagination info' if config.has_pagination else ''}
            {'    total_count = await self.count(filters)' if config.has_pagination else ''}
            {'    total_pages = (total_count + size - 1) // size' if config.has_pagination else ''}
            {'    ' if config.has_pagination else ''}
            {'    return {{' if config.has_pagination else ''}
            {'        "items": entities,' if config.has_pagination else ''}
            {'        "total": total_count,' if config.has_pagination else ''}
            {'        "page": page,' if config.has_pagination else ''}
            {'        "size": size,' if config.has_pagination else ''}
            {'        "pages": total_pages' if config.has_pagination else ''}
            {'    }}' if config.has_pagination else ''}
            {'else:' if config.has_pagination else ''}
            {'    return entities' if config.has_pagination else ''}
            {'' if config.has_pagination else 'return entities'}
            
        except Exception as e:
            self.logger.error(f"Failed to list {config.entity_name.lower()}", extra={{"error": str(e)}})
            raise
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching filters"""
        try:
            query_params = self.query_builder.build_count_query(filters)
            response = self.table.query(**query_params, Select='COUNT')
            return response['Count']
            
        except Exception as e:
            self.logger.error(f"Failed to count {config.entity_name.lower()}", extra={{"error": str(e)}})
            raise
    
    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists"""
        try:
            response = self.table.get_item(
                Key={{
                    'PK': f'{config.entity_name.upper()}_{{entity_id}}',
                    'SK': f'{config.entity_name.upper()}_{{entity_id}}'
                }},
                ProjectionExpression='PK'
            )
            return 'Item' in response
            
        except Exception as e:
            self.logger.error(f"Failed to check existence of {config.entity_name.lower()}", extra={{"entity_id": entity_id, "error": str(e)}})
            raise
    
    async def bulk_create(self, entities: List[{config.entity_name}]) -> List[{config.entity_name}]:
        """Create multiple entities in batch"""
        try:
            # DynamoDB batch write limit is 25 items
            batch_size = 25
            created_entities = []
            
            for i in range(0, len(entities), batch_size):
                batch = entities[i:i + batch_size]
                
                with self.table.batch_writer() as batch_writer:
                    for entity in batch:
                        item = entity.to_dynamodb_item()
                        batch_writer.put_item(Item=item)
                        created_entities.append(entity)
            
            self.logger.info(f"Bulk created {{len(created_entities)}} {config.entity_name.lower()} entities")
            return created_entities
            
        except Exception as e:
            self.logger.error(f"Failed to bulk create {config.entity_name.lower()}", extra={{"count": len(entities), "error": str(e)}})
            raise
    
    async def bulk_delete(self, entity_ids: List[str]) -> int:
        """Delete multiple entities in batch"""
        try:
            # DynamoDB batch write limit is 25 items
            batch_size = 25
            deleted_count = 0
            
            for i in range(0, len(entity_ids), batch_size):
                batch = entity_ids[i:i + batch_size]
                
                with self.table.batch_writer() as batch_writer:
                    for entity_id in batch:
                        batch_writer.delete_item(
                            Key={{
                                'PK': f'{config.entity_name.upper()}_{{entity_id}}',
                                'SK': f'{config.entity_name.upper()}_{{entity_id}}'
                            }}
                        )
                        deleted_count += 1
            
            self.logger.info(f"Bulk deleted {{deleted_count}} {config.entity_name.lower()} entities")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to bulk delete {config.entity_name.lower()}", extra={{"count": len(entity_ids), "error": str(e)}})
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Repository health check"""
        try:
            # Try to describe table
            table_description = self.table.meta.client.describe_table(
                TableName=self.table.table_name
            )
            
            table_status = table_description['Table']['TableStatus']
            item_count = table_description['Table']['ItemCount']
            
            {'# Check cache health' if config.has_cache else ''}
            {'cache_health = await self.cache.health_check()' if config.has_cache else ''}
            
            return {{
                "status": "healthy" if table_status == "ACTIVE" else "degraded",
                "table_status": table_status,
                "item_count": item_count,
                {'"cache": cache_health,' if config.has_cache else ''}
                "timestamp": datetime.now().isoformat()
            }}
            
        except Exception as e:
            return {{
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }}
{cache_methods}
{custom_implementations}
'''
    
    def _generate_custom_query_implementation(self, query: QueryConfig, config: RepositoryConfig) -> str:
        """Generate custom query implementation"""
        return f'''
    async def {query.name}(self, {", ".join(f"{param}: Any" for param in query.parameters)}) -> {query.return_type}:
        """{query.description}"""
        try:
            # Custom query implementation
            query_params = self.query_builder.build_{query.name}_query({", ".join(query.parameters)})
            response = self.table.query(**query_params)
            
            entities = [
                {config.entity_name}.from_dynamodb_item(item) 
                for item in response['Items']
            ]
            
            {'return entities[0] if entities else None' if query.is_single else 'return entities'}
            
        except Exception as e:
            self.logger.error(f"Failed to execute {query.name}", extra={{"error": str(e)}})
            raise
'''
    
    def _generate_query_builders(self, config: RepositoryConfig) -> str:
        """Generate query builders"""
        custom_builders = ""
        if config.custom_queries:
            custom_builders = chr(10).join([
                f'''
    def build_{query.name}_query(self, {", ".join(query.parameters)}) -> Dict[str, Any]:
        """{query.description} query builder"""
        return {{
            'IndexName': 'GSI1',
            'KeyConditionExpression': Key('GSI1PK').eq(f'type#{config.entity_name.lower()}'),
            # Add custom query logic here based on parameters
        }}
''' for query in config.custom_queries
            ])
        
        return f'''"""
Query Builders for {config.name} Repository

Builds DynamoDB query expressions and parameters
"""

from typing import Any, Dict, List, Optional, Tuple
from boto3.dynamodb.conditions import Key, Attr


class {config.name}QueryBuilder:
    """Query builder for {config.entity_name} repository operations"""
    
    def build_list_query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        {'page: int = 1,' if config.has_pagination else ''}
        {'size: int = 10,' if config.has_pagination else ''}
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """Build query for listing entities"""
        query_params = {{
            'IndexName': 'GSI1',
            'KeyConditionExpression': Key('GSI1PK').eq('type#{config.entity_name.lower()}'),
            {'Limit': size,
            'ScanIndexForward': sort_order == "asc"' if config.has_pagination else 'ScanIndexForward': sort_order == "asc"}
        }}
        
        # Apply filters
        if filters:
            filter_expr, expr_values, expr_names = self._build_filter_expression(filters)
            if filter_expr:
                query_params['FilterExpression'] = filter_expr
                query_params.setdefault('ExpressionAttributeValues', {{}}).update(expr_values)
                query_params.setdefault('ExpressionAttributeNames', {{}}).update(expr_names)
        
        return query_params
    
    def build_count_query(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build query for counting entities"""
        query_params = {{
            'IndexName': 'GSI1',
            'KeyConditionExpression': Key('GSI1PK').eq('type#{config.entity_name.lower()}'),
            'Select': 'COUNT'
        }}
        
        # Apply filters
        if filters:
            filter_expr, expr_values, expr_names = self._build_filter_expression(filters)
            if filter_expr:
                query_params['FilterExpression'] = filter_expr
                query_params.setdefault('ExpressionAttributeValues', {{}}).update(expr_values)
                query_params.setdefault('ExpressionAttributeNames', {{}}).update(expr_names)
        
        return query_params
    
    def build_update_expression(self, updates: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Dict[str, str]]:
        """Build update expression for entity updates"""
        set_clauses = []
        expr_values = {{}}
        expr_names = {{}}
        
        # Always update the updated_at timestamp
        set_clauses.append("#updated_at = :updated_at")
        expr_names["#updated_at"] = "updated_at"
        expr_values[":updated_at"] = {"S": "{{datetime.now().isoformat()}}"}
        
        # Add other updates
        for key, value in updates.items():
            if key not in ['PK', 'SK', 'entity_type', 'created_at']:
                attr_name = f"#{key}"
                attr_value = f":{key}"
                
                set_clauses.append(f"{attr_name} = {attr_value}")
                expr_names[attr_name] = key
                expr_values[attr_value] = self._serialize_value(value)
        
        update_expression = f"SET {{', '.join(set_clauses)}}"
        return update_expression, expr_values, expr_names
    
    def _build_filter_expression(self, filters: Dict[str, Any]) -> Tuple[Any, Dict[str, Any], Dict[str, str]]:
        """Build filter expression from filters dict"""
        conditions = []
        expr_values = {{}}
        expr_names = {{}}
        
        for key, value in filters.items():
            if value is not None:
                attr_name = f"#{key}"
                attr_value = f":{key}"
                
                expr_names[attr_name] = key
                expr_values[attr_value] = self._serialize_value(value)
                
                # Handle different filter types
                if isinstance(value, list):
                    # IN condition
                    conditions.append(Attr(key).is_in(value))
                elif isinstance(value, dict) and 'range' in value:
                    # Range condition
                    if 'min' in value['range']:
                        conditions.append(Attr(key) >= value['range']['min'])
                    if 'max' in value['range']:
                        conditions.append(Attr(key) <= value['range']['max'])
                elif isinstance(value, str) and value.startswith('*') and value.endswith('*'):
                    # Contains condition
                    conditions.append(Attr(key).contains(value.strip('*')))
                else:
                    # Equality condition
                    conditions.append(Attr(key).eq(value))
        
        # Combine all conditions with AND
        if conditions:
            filter_expr = conditions[0]
            for condition in conditions[1:]:
                filter_expr = filter_expr & condition
            return filter_expr, expr_values, expr_names
        
        return None, {{}}, {{}}
    
    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """Serialize value for DynamoDB"""
        from boto3.dynamodb.types import TypeSerializer
        serializer = TypeSerializer()
        return serializer.serialize(value)
{custom_builders}
'''
    
    def _generate_unit_tests(self, config: RepositoryConfig) -> str:
        """Generate unit tests"""
        return f'''"""
Unit tests for {config.name} Repository
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.adapters.{config.name.lower()}_repository import {config.name}Repository
from src.models.{config.entity_name.lower()} import {config.entity_name}
from src.factories.{config.entity_name.lower()}_factory import {config.entity_name}Factory


class Test{config.name}Repository:
    """Test suite for {config.name}Repository"""
    
    @pytest.fixture
    def mock_table(self):
        """Mock DynamoDB table"""
        return Mock()
    
    {'@pytest.fixture' if config.has_cache else ''}
    {'def mock_cache(self):' if config.has_cache else ''}
    {'    """Mock cache service"""' if config.has_cache else ''}
    {'    return Mock()' if config.has_cache else ''}
    
    @pytest.fixture
    def repository(self, mock_table{', mock_cache' if config.has_cache else ''}):
        """Create repository instance with mocked dependencies"""
        with patch('boto3.resource') as mock_boto:
            mock_boto.return_value.Table.return_value = mock_table
            repo = {config.name}Repository({'cache_service=mock_cache' if config.has_cache else ''})
            repo.table = mock_table
            return repo
    
    @pytest.mark.asyncio
    async def test_create_success(self, repository, mock_table):
        """Test successful entity creation"""
        # Arrange
        entity = {config.entity_name}Factory.create()
        mock_table.put_item.return_value = None
        
        # Act
        result = await repository.create(entity)
        
        # Assert
        assert result == entity
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        assert 'Item' in call_args.kwargs
        assert 'ConditionExpression' in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repository, mock_table):
        """Test successful entity retrieval"""
        # Arrange
        entity = {config.entity_name}Factory.create()
        mock_table.get_item.return_value = {{'Item': entity.to_dynamodb_item()}}
        
        # Act
        result = await repository.get_by_id(entity.id)
        
        # Assert
        assert result is not None
        assert result.id == entity.id
        mock_table.get_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_table):
        """Test entity not found"""
        # Arrange
        mock_table.get_item.return_value = {{}}
        
        # Act
        result = await repository.get_by_id("nonexistent_id")
        
        # Assert
        assert result is None
        mock_table.get_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_table):
        """Test successful entity update"""
        # Arrange
        entity = {config.entity_name}Factory.create()
        updates = {{"name": "updated_name"}}
        mock_table.update_item.return_value = {{'Attributes': entity.to_dynamodb_item()}}
        
        # Act
        result = await repository.update(entity.id, updates)
        
        # Assert
        assert result is not None
        assert result.id == entity.id
        mock_table.update_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_table):
        """Test successful entity deletion"""
        # Arrange
        entity_id = "test_id"
        mock_table.delete_item.return_value = None
        
        # Act
        result = await repository.delete(entity_id)
        
        # Assert
        assert result is True
        mock_table.delete_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_entities(self, repository, mock_table):
        """Test listing entities"""
        # Arrange
        entities = {config.entity_name}Factory.create_batch(3)
        mock_table.query.return_value = {{
            'Items': [e.to_dynamodb_item() for e in entities]
        }}
        
        # Act
        result = await repository.list()
        
        # Assert
        {'assert "items" in result' if config.has_pagination else 'assert isinstance(result, list)'}
        {'assert len(result["items"]) == 3' if config.has_pagination else 'assert len(result) == 3'}
        mock_table.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_entities(self, repository, mock_table):
        """Test counting entities"""
        # Arrange
        mock_table.query.return_value = {{'Count': 5}}
        
        # Act
        result = await repository.count()
        
        # Assert
        assert result == 5
        mock_table.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_table):
        """Test entity exists"""
        # Arrange
        mock_table.get_item.return_value = {{'Item': {{'PK': 'test'}}}}
        
        # Act
        result = await repository.exists("test_id")
        
        # Assert
        assert result is True
        mock_table.get_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_table):
        """Test entity does not exist"""
        # Arrange
        mock_table.get_item.return_value = {{}}
        
        # Act
        result = await repository.exists("test_id")
        
        # Assert
        assert result is False
        mock_table.get_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_create(self, repository):
        """Test bulk entity creation"""
        # Arrange
        entities = {config.entity_name}Factory.create_batch(10)
        mock_batch_writer = Mock()
        repository.table.batch_writer.return_value.__enter__.return_value = mock_batch_writer
        
        # Act
        result = await repository.bulk_create(entities)
        
        # Assert
        assert len(result) == 10
        assert mock_batch_writer.put_item.call_count == 10
    
    @pytest.mark.asyncio
    async def test_bulk_delete(self, repository):
        """Test bulk entity deletion"""
        # Arrange
        entity_ids = ["id1", "id2", "id3"]
        mock_batch_writer = Mock()
        repository.table.batch_writer.return_value.__enter__.return_value = mock_batch_writer
        
        # Act
        result = await repository.bulk_delete(entity_ids)
        
        # Assert
        assert result == 3
        assert mock_batch_writer.delete_item.call_count == 3
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, repository, mock_table):
        """Test healthy repository"""
        # Arrange
        mock_table.meta.client.describe_table.return_value = {{
            'Table': {{
                'TableStatus': 'ACTIVE',
                'ItemCount': 100
            }}
        }}
        
        # Act
        result = await repository.health_check()
        
        # Assert
        assert result["status"] == "healthy"
        assert result["table_status"] == "ACTIVE"
        assert result["item_count"] == 100
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, repository, mock_table):
        """Test unhealthy repository"""
        # Arrange
        mock_table.meta.client.describe_table.side_effect = Exception("Connection failed")
        
        # Act
        result = await repository.health_check()
        
        # Assert
        assert result["status"] == "unhealthy"
        assert "error" in result
    
    {'@pytest.mark.asyncio' if config.has_cache else ''}
    {'async def test_cache_integration(self, repository, mock_cache):' if config.has_cache else ''}
    {'    """Test cache integration"""' if config.has_cache else ''}
    {'    # Arrange' if config.has_cache else ''}
    {'    entity = {config.entity_name}Factory.create()' if config.has_cache else ''}
    {'    mock_cache.get = AsyncMock(return_value=entity.to_dynamodb_item())' if config.has_cache else ''}
    {'    ' if config.has_cache else ''}
    {'    # Act' if config.has_cache else ''}
    {'    result = await repository._get_from_cache("test_key")' if config.has_cache else ''}
    {'    ' if config.has_cache else ''}
    {'    # Assert' if config.has_cache else ''}
    {'    assert result is not None' if config.has_cache else ''}
    {'    assert result.id == entity.id' if config.has_cache else ''}
    {'    mock_cache.get.assert_called_once_with("test_key")' if config.has_cache else ''}
'''
    
    def _generate_integration_tests(self, config: RepositoryConfig) -> str:
        """Generate integration tests"""
        return f'''"""
Integration tests for {config.name} Repository
"""

import pytest
import boto3
from moto import mock_dynamodb
from datetime import datetime

from src.adapters.{config.name.lower()}_repository import {config.name}Repository
from src.models.{config.entity_name.lower()} import {config.entity_name}
from src.factories.{config.entity_name.lower()}_factory import {config.entity_name}Factory
from src.config.settings import get_settings


@mock_dynamodb
class Test{config.name}RepositoryIntegration:
    """Integration test suite for {config.name}Repository"""
    
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
                {{'AttributeName': 'GSI1SK', 'AttributeType': 'S'}},
                {{'AttributeName': 'GSI2PK', 'AttributeType': 'S'}},
                {{'AttributeName': 'GSI2SK', 'AttributeType': 'S'}}
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
                }},
                {{
                    'IndexName': 'GSI2',
                    'KeySchema': [
                        {{'AttributeName': 'GSI2PK', 'KeyType': 'HASH'}},
                        {{'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}}
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
        self.repository = {config.name}Repository()
    
    @pytest.mark.asyncio
    async def test_full_crud_workflow(self):
        """Test complete CRUD workflow"""
        # Create
        entity = {config.entity_name}Factory.create()
        created_entity = await self.repository.create(entity)
        assert created_entity.id == entity.id
        
        # Read
        retrieved_entity = await self.repository.get_by_id(entity.id)
        assert retrieved_entity is not None
        assert retrieved_entity.id == entity.id
        
        # Update
        updates = {{"name": "updated_name"}}
        updated_entity = await self.repository.update(entity.id, updates)
        assert updated_entity.name == "updated_name"
        
        # Delete
        delete_result = await self.repository.delete(entity.id)
        assert delete_result is True
        
        # Verify deletion
        deleted_entity = await self.repository.get_by_id(entity.id)
        assert deleted_entity is None
    
    @pytest.mark.asyncio
    async def test_list_and_pagination(self):
        """Test listing with pagination"""
        # Create test entities
        entities = {config.entity_name}Factory.create_batch(15)
        for entity in entities:
            await self.repository.create(entity)
        
        {'# Test pagination' if config.has_pagination else ''}
        {'page1 = await self.repository.list(page=1, size=10)' if config.has_pagination else 'result = await self.repository.list()'}
        {'assert len(page1["items"]) == 10' if config.has_pagination else 'assert len(result) >= 15'}
        {'assert page1["page"] == 1' if config.has_pagination else ''}
        {'assert page1["total"] >= 15' if config.has_pagination else ''}
        {'assert page1["pages"] >= 2' if config.has_pagination else ''}
        {'    ' if config.has_pagination else ''}
        {'page2 = await self.repository.list(page=2, size=10)' if config.has_pagination else ''}
        {'assert len(page2["items"]) >= 5' if config.has_pagination else ''}
    
    @pytest.mark.asyncio
    async def test_filtering(self):
        """Test entity filtering"""
        # Create entities with different attributes
        active_entity = {config.entity_name}Factory.create()
        inactive_entity = {config.entity_name}Factory.create()
        
        await self.repository.create(active_entity)
        await self.repository.create(inactive_entity)
        
        # Test filtering (assuming status field exists)
        result = await self.repository.list()
        {'filtered_entities = result["items"]' if config.has_pagination else 'filtered_entities = result'}
        assert len(filtered_entities) >= 2
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self):
        """Test bulk create and delete operations"""
        # Bulk create
        entities = {config.entity_name}Factory.create_batch(30)
        created_entities = await self.repository.bulk_create(entities)
        assert len(created_entities) == 30
        
        # Verify creation
        count = await self.repository.count()
        assert count >= 30
        
        # Bulk delete
        entity_ids = [e.id for e in entities[:10]]
        deleted_count = await self.repository.bulk_delete(entity_ids)
        assert deleted_count == 10
        
        # Verify deletion
        new_count = await self.repository.count()
        assert new_count == count - 10
    
    @pytest.mark.asyncio
    async def test_exists_functionality(self):
        """Test entity existence checking"""
        # Test non-existent entity
        exists_before = await self.repository.exists("non_existent_id")
        assert exists_before is False
        
        # Create entity
        entity = {config.entity_name}Factory.create()
        await self.repository.create(entity)
        
        # Test existing entity
        exists_after = await self.repository.exists(entity.id)
        assert exists_after is True
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent repository operations"""
        import asyncio
        
        # Create multiple entities concurrently
        entities = {config.entity_name}Factory.create_batch(10)
        tasks = [self.repository.create(entity) for entity in entities]
        
        created_entities = await asyncio.gather(*tasks)
        assert len(created_entities) == 10
        
        # Verify all were created
        count = await self.repository.count()
        assert count >= 10
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling scenarios"""
        # Test duplicate creation (should fail with condition check)
        entity = {config.entity_name}Factory.create()
        await self.repository.create(entity)
        
        # Try to create the same entity again
        with pytest.raises(Exception):
            await self.repository.create(entity)
        
        # Test updating non-existent entity
        with pytest.raises(Exception):
            await self.repository.update("non_existent_id", {{"name": "updated"}})
    
    @pytest.mark.asyncio
    async def test_repository_health_check(self):
        """Test repository health check"""
        health = await self.repository.health_check()
        
        assert health["status"] == "healthy"
        assert health["table_status"] == "ACTIVE"
        assert "item_count" in health
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_query_builder_integration(self):
        """Test query builder integration"""
        # Create entities with different attributes for filtering
        entities = {config.entity_name}Factory.create_batch(5)
        for entity in entities:
            await self.repository.create(entity)
        
        # Test various query scenarios
        all_entities = await self.repository.list()
        {'assert len(all_entities["items"]) >= 5' if config.has_pagination else 'assert len(all_entities) >= 5'}
        
        # Test sorting
        sorted_entities = await self.repository.list(sort_order="desc")
        {'assert len(sorted_entities["items"]) >= 5' if config.has_pagination else 'assert len(sorted_entities) >= 5'}
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
    parser = argparse.ArgumentParser(description="Generate repository implementation")
    parser.add_argument("name", help="Repository name (e.g., UserProfile)")
    parser.add_argument("entity", help="Entity name (e.g., User)")
    parser.add_argument("--description", default="Repository description", help="Repository description")
    parser.add_argument("--table", required=True, help="DynamoDB table name")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache integration")
    parser.add_argument("--no-pagination", action="store_true", help="Skip pagination support")
    parser.add_argument("--no-filtering", action="store_true", help="Skip filtering support")
    parser.add_argument("--queries", help="Custom queries as JSON: [{'name':'findByStatus','description':'Find by status','parameters':['status'],'is_single':false}]")
    
    args = parser.parse_args()
    
    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir
    while project_root.parent != project_root:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent
    
    # Parse custom queries
    custom_queries = []
    if args.queries:
        import json
        try:
            queries_data = json.loads(args.queries)
            custom_queries = [QueryConfig(**query) for query in queries_data]
        except Exception as e:
            print(f"❌ Error parsing queries: {e}")
            return
    
    # Create repository configuration
    config = RepositoryConfig(
        name=args.name,
        entity_name=args.entity,
        description=args.description,
        table_name=args.table,
        has_cache=not args.no_cache,
        has_pagination=not args.no_pagination,
        has_filtering=not args.no_filtering,
        custom_queries=custom_queries
    )
    
    # Generate repository
    generator = RepositoryGenerator(project_root)
    files = generator.generate_repository(config)
    generator.create_files(files)
    
    print(f"\\n🚀 Generated {args.name} repository for {args.entity} entity!")
    print(f"📁 Files created: {len(files)}")
    print("\\n📝 Next steps:")
    print(f"1. Review the generated repository: src/adapters/{args.name.lower()}_repository.py")
    print(f"2. Run the tests: pytest tests/unit/test_{args.name.lower()}_repository.py")
    print(f"3. Add the repository to your dependency injection container")
    print(f"4. Use the repository in your service layer")


if __name__ == "__main__":
    main()
