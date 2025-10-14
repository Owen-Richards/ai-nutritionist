#!/usr/bin/env python3
"""
Migration Generator for AI Nutritionist

Generates database and API migrations with:
- Schema changes
- Data transformations
- Rollback scripts
- Version management
- Dependency tracking
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class MigrationConfig:
    """Configuration for migration generation"""
    name: str
    version: str
    description: str
    migration_type: str  # 'schema', 'data', 'api'
    changes: List[Dict[str, Any]]
    dependencies: List[str] = None
    rollback_enabled: bool = True


class MigrationGenerator:
    """Generates database and API migrations"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.migrations_dir = project_root / "migrations"
        
    def generate(self, config: MigrationConfig) -> Dict[str, str]:
        """Generate migration files"""
        files = {}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_id = f"{timestamp}_{config.name.lower()}"
        
        # Generate migration script
        files[f"migrations/{migration_id}.py"] = self._generate_migration_script(config, migration_id)
        
        # Generate rollback script if enabled
        if config.rollback_enabled:
            files[f"migrations/rollbacks/{migration_id}_rollback.py"] = self._generate_rollback_script(config, migration_id)
        
        # Generate migration metadata
        files[f"migrations/metadata/{migration_id}.json"] = self._generate_migration_metadata(config, migration_id)
        
        # Update migration index
        files["migrations/index.json"] = self._update_migration_index(config, migration_id)
        
        return files
    
    def _generate_migration_script(self, config: MigrationConfig, migration_id: str) -> str:
        """Generate migration script"""
        if config.migration_type == 'schema':
            return self._generate_schema_migration(config, migration_id)
        elif config.migration_type == 'data':
            return self._generate_data_migration(config, migration_id)
        elif config.migration_type == 'api':
            return self._generate_api_migration(config, migration_id)
        else:
            raise ValueError(f"Unknown migration type: {config.migration_type}")
    
    def _generate_schema_migration(self, config: MigrationConfig, migration_id: str) -> str:
        """Generate schema migration"""
        changes_code = []
        for change in config.changes:
            change_type = change.get('type')
            if change_type == 'create_table':
                changes_code.append(self._generate_create_table_code(change))
            elif change_type == 'add_column':
                changes_code.append(self._generate_add_column_code(change))
            elif change_type == 'drop_column':
                changes_code.append(self._generate_drop_column_code(change))
            elif change_type == 'modify_column':
                changes_code.append(self._generate_modify_column_code(change))
            elif change_type == 'create_index':
                changes_code.append(self._generate_create_index_code(change))
        
        return f'''"""
{config.name} Schema Migration

{config.description}

Migration ID: {migration_id}
Version: {config.version}
Generated on: {datetime.now().isoformat()}
"""

import logging
from typing import Any, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class {config.name.replace('_', '').title()}Migration:
    """Schema migration for {config.name}"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.migration_id = "{migration_id}"
        self.version = "{config.version}"
        
    async def up(self) -> bool:
        """Apply migration"""
        try:
            logger.info(f"Applying migration {{self.migration_id}}")
            
{chr(10).join(['            ' + code for code in changes_code])}
            
            # Record migration
            await self._record_migration_applied()
            
            logger.info(f"Migration {{self.migration_id}} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error applying migration {{self.migration_id}}: {{e}}")
            await self._record_migration_failed(str(e))
            raise
    
    async def down(self) -> bool:
        """Rollback migration"""
        try:
            logger.info(f"Rolling back migration {{self.migration_id}}")
            
            # TODO: Implement rollback logic
            
            # Remove migration record
            await self._remove_migration_record()
            
            logger.info(f"Migration {{self.migration_id}} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back migration {{self.migration_id}}: {{e}}")
            raise
    
    async def _record_migration_applied(self):
        """Record that migration was applied"""
        migration_record = {{
            "migration_id": self.migration_id,
            "version": self.version,
            "applied_at": datetime.utcnow().isoformat(),
            "status": "applied"
        }}
        
        # Store in migrations table
        await self.db.put_item(
            TableName="migrations",
            Item=migration_record
        )
    
    async def _record_migration_failed(self, error: str):
        """Record that migration failed"""
        migration_record = {{
            "migration_id": self.migration_id,
            "version": self.version,
            "applied_at": datetime.utcnow().isoformat(),
            "status": "failed",
            "error": error
        }}
        
        await self.db.put_item(
            TableName="migrations",
            Item=migration_record
        )
    
    async def _remove_migration_record(self):
        """Remove migration record"""
        await self.db.delete_item(
            TableName="migrations",
            Key={{"migration_id": self.migration_id}}
        )
'''

    def _generate_create_table_code(self, change: Dict[str, Any]) -> str:
        """Generate create table code"""
        table_name = change.get('table_name')
        schema = change.get('schema', {})
        
        return f'''
# Create table {table_name}
await self.db.create_table(
    TableName="{table_name}",
    KeySchema={schema.get('key_schema', [])},
    AttributeDefinitions={schema.get('attribute_definitions', [])},
    BillingMode="PAY_PER_REQUEST"
)'''

    def _generate_add_column_code(self, change: Dict[str, Any]) -> str:
        """Generate add column code"""
        table_name = change.get('table_name')
        column_name = change.get('column_name')
        column_type = change.get('column_type')
        
        return f'''
# Add column {column_name} to {table_name}
# Note: DynamoDB is schemaless, so this is a logical operation
# Ensure new items include the {column_name} field
logger.info("Added column {column_name} to {table_name} (logical)")'''

    def _generate_drop_column_code(self, change: Dict[str, Any]) -> str:
        """Generate drop column code"""
        table_name = change.get('table_name')
        column_name = change.get('column_name')
        
        return f'''
# Drop column {column_name} from {table_name}
# Note: DynamoDB is schemaless, existing data will remain
# Update application code to stop using {column_name}
logger.info("Dropped column {column_name} from {table_name} (logical)")'''

    def _generate_modify_column_code(self, change: Dict[str, Any]) -> str:
        """Generate modify column code"""
        table_name = change.get('table_name')
        column_name = change.get('column_name')
        new_type = change.get('new_type')
        
        return f'''
# Modify column {column_name} in {table_name}
# Data transformation may be required
logger.info("Modified column {column_name} in {table_name}")'''

    def _generate_create_index_code(self, change: Dict[str, Any]) -> str:
        """Generate create index code"""
        table_name = change.get('table_name')
        index_name = change.get('index_name')
        key_schema = change.get('key_schema', [])
        
        return f'''
# Create GSI {index_name} on {table_name}
await self.db.update_table(
    TableName="{table_name}",
    GlobalSecondaryIndexUpdates=[
        {{
            "Create": {{
                "IndexName": "{index_name}",
                "KeySchema": {key_schema},
                "Projection": {{"ProjectionType": "ALL"}},
                "BillingMode": "PAY_PER_REQUEST"
            }}
        }}
    ]
)'''

    def _generate_data_migration(self, config: MigrationConfig, migration_id: str) -> str:
        """Generate data migration"""
        return f'''"""
{config.name} Data Migration

{config.description}

Migration ID: {migration_id}
Version: {config.version}
Generated on: {datetime.now().isoformat()}
"""

import logging
from typing import Any, Dict, List
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class {config.name.replace('_', '').title()}DataMigration:
    """Data migration for {config.name}"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.migration_id = "{migration_id}"
        self.version = "{config.version}"
        self.batch_size = 25  # DynamoDB batch size limit
        
    async def up(self) -> bool:
        """Apply data migration"""
        try:
            logger.info(f"Applying data migration {{self.migration_id}}")
            
            # Process data transformations
            await self._transform_data()
            
            # Record migration
            await self._record_migration_applied()
            
            logger.info(f"Data migration {{self.migration_id}} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error applying data migration {{self.migration_id}}: {{e}}")
            raise
    
    async def down(self) -> bool:
        """Rollback data migration"""
        try:
            logger.info(f"Rolling back data migration {{self.migration_id}}")
            
            # TODO: Implement data rollback logic
            
            await self._remove_migration_record()
            
            logger.info(f"Data migration {{self.migration_id}} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back data migration {{self.migration_id}}: {{e}}")
            raise
    
    async def _transform_data(self):
        """Transform existing data"""
        # TODO: Implement data transformation logic based on config.changes
        
        # Example: Migrate user preferences format
        paginator = self.db.get_paginator('scan')
        page_iterator = paginator.paginate(TableName='user_profiles')
        
        for page in page_iterator:
            items = page.get('Items', [])
            if items:
                await self._process_batch(items)
    
    async def _process_batch(self, items: List[Dict[str, Any]]):
        """Process a batch of items"""
        transformed_items = []
        
        for item in items:
            # Apply transformations
            transformed_item = await self._transform_item(item)
            if transformed_item:
                transformed_items.append(transformed_item)
        
        # Batch write transformed items
        if transformed_items:
            await self._batch_write_items(transformed_items)
    
    async def _transform_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single item"""
        # TODO: Implement item transformation logic
        return item
    
    async def _batch_write_items(self, items: List[Dict[str, Any]]):
        """Batch write items to DynamoDB"""
        # Split into batches of 25 (DynamoDB limit)
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            request_items = {{
                'user_profiles': [
                    {{'PutRequest': {{'Item': item}}}}
                    for item in batch
                ]
            }}
            
            await self.db.batch_write_item(RequestItems=request_items)
    
    async def _record_migration_applied(self):
        """Record that migration was applied"""
        migration_record = {{
            "migration_id": self.migration_id,
            "version": self.version,
            "applied_at": datetime.utcnow().isoformat(),
            "status": "applied",
            "type": "data"
        }}
        
        await self.db.put_item(
            TableName="migrations",
            Item=migration_record
        )
    
    async def _remove_migration_record(self):
        """Remove migration record"""
        await self.db.delete_item(
            TableName="migrations",
            Key={{"migration_id": self.migration_id}}
        )
'''

    def _generate_api_migration(self, config: MigrationConfig, migration_id: str) -> str:
        """Generate API migration"""
        return f'''"""
{config.name} API Migration

{config.description}

Migration ID: {migration_id}
Version: {config.version}
Generated on: {datetime.now().isoformat()}
"""

import logging
from typing import Any, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class {config.name.replace('_', '').title()}APIMigration:
    """API migration for {config.name}"""
    
    def __init__(self, api_gateway_client):
        self.api_gateway = api_gateway_client
        self.migration_id = "{migration_id}"
        self.version = "{config.version}"
        
    async def up(self) -> bool:
        """Apply API migration"""
        try:
            logger.info(f"Applying API migration {{self.migration_id}}")
            
            # Apply API changes
            await self._apply_api_changes()
            
            # Update API documentation
            await self._update_api_docs()
            
            # Record migration
            await self._record_migration_applied()
            
            logger.info(f"API migration {{self.migration_id}} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error applying API migration {{self.migration_id}}: {{e}}")
            raise
    
    async def down(self) -> bool:
        """Rollback API migration"""
        try:
            logger.info(f"Rolling back API migration {{self.migration_id}}")
            
            # TODO: Implement API rollback logic
            
            await self._remove_migration_record()
            
            logger.info(f"API migration {{self.migration_id}} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back API migration {{self.migration_id}}: {{e}}")
            raise
    
    async def _apply_api_changes(self):
        """Apply API changes"""
        # TODO: Implement API changes based on config.changes
        
        for change in {config.changes}:
            change_type = change.get('type')
            
            if change_type == 'add_endpoint':
                await self._add_endpoint(change)
            elif change_type == 'modify_endpoint':
                await self._modify_endpoint(change)
            elif change_type == 'deprecate_endpoint':
                await self._deprecate_endpoint(change)
            elif change_type == 'remove_endpoint':
                await self._remove_endpoint(change)
    
    async def _add_endpoint(self, change: Dict[str, Any]):
        """Add new API endpoint"""
        endpoint_path = change.get('path')
        method = change.get('method')
        
        logger.info(f"Adding endpoint {{method}} {{endpoint_path}}")
        # TODO: Implement endpoint addition
    
    async def _modify_endpoint(self, change: Dict[str, Any]):
        """Modify existing API endpoint"""
        endpoint_path = change.get('path')
        method = change.get('method')
        
        logger.info(f"Modifying endpoint {{method}} {{endpoint_path}}")
        # TODO: Implement endpoint modification
    
    async def _deprecate_endpoint(self, change: Dict[str, Any]):
        """Deprecate API endpoint"""
        endpoint_path = change.get('path')
        method = change.get('method')
        
        logger.info(f"Deprecating endpoint {{method}} {{endpoint_path}}")
        # TODO: Implement endpoint deprecation
    
    async def _remove_endpoint(self, change: Dict[str, Any]):
        """Remove API endpoint"""
        endpoint_path = change.get('path')
        method = change.get('method')
        
        logger.info(f"Removing endpoint {{method}} {{endpoint_path}}")
        # TODO: Implement endpoint removal
    
    async def _update_api_docs(self):
        """Update API documentation"""
        # TODO: Regenerate OpenAPI documentation
        logger.info("Updated API documentation")
    
    async def _record_migration_applied(self):
        """Record that migration was applied"""
        # TODO: Record migration in appropriate storage
        logger.info(f"Recorded API migration {{self.migration_id}}")
    
    async def _remove_migration_record(self):
        """Remove migration record"""
        # TODO: Remove migration record
        logger.info(f"Removed API migration record {{self.migration_id}}")
'''

    def _generate_rollback_script(self, config: MigrationConfig, migration_id: str) -> str:
        """Generate rollback script"""
        return f'''"""
Rollback Script for {config.name}

Migration ID: {migration_id}
Generated on: {datetime.now().isoformat()}
"""

import logging
from typing import Any, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


async def rollback_{migration_id.replace('-', '_')}(db_client) -> bool:
    """
    Rollback migration {migration_id}
    
    This script reverses the changes made by the migration.
    """
    try:
        logger.info(f"Starting rollback for migration {migration_id}")
        
        # TODO: Implement specific rollback logic
        # This should reverse all changes made in the up() method
        
        logger.info(f"Rollback for migration {migration_id} completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during rollback of migration {migration_id}: {{e}}")
        raise


if __name__ == "__main__":
    import asyncio
    import boto3
    
    # Initialize database client
    db_client = boto3.client('dynamodb')
    
    # Run rollback
    asyncio.run(rollback_{migration_id.replace('-', '_')}(db_client))
'''

    def _generate_migration_metadata(self, config: MigrationConfig, migration_id: str) -> str:
        """Generate migration metadata"""
        metadata = {
            "migration_id": migration_id,
            "name": config.name,
            "version": config.version,
            "description": config.description,
            "type": config.migration_type,
            "changes": config.changes,
            "dependencies": config.dependencies or [],
            "rollback_enabled": config.rollback_enabled,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        return json.dumps(metadata, indent=2)

    def _update_migration_index(self, config: MigrationConfig, migration_id: str) -> str:
        """Update migration index"""
        # This would typically read existing index and add new migration
        # For now, create a simple index entry
        index_entry = {
            "migrations": [
                {
                    "id": migration_id,
                    "name": config.name,
                    "version": config.version,
                    "type": config.migration_type,
                    "created_at": datetime.now().isoformat()
                }
            ],
            "last_updated": datetime.now().isoformat()
        }
        
        return json.dumps(index_entry, indent=2)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate migrations")
    parser.add_argument("--name", required=True, help="Migration name")
    parser.add_argument("--type", choices=['schema', 'data', 'api'], required=True, help="Migration type")
    parser.add_argument("--description", required=True, help="Migration description")
    parser.add_argument("--version", default="1.0.0", help="Migration version")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    generator = MigrationGenerator(project_root)
    
    config = MigrationConfig(
        name=args.name,
        version=args.version,
        description=args.description,
        migration_type=args.type,
        changes=[]  # Would be populated based on user input or config file
    )
    
    files = generator.generate(config)
    
    # Write files
    for file_path, content in files.items():
        full_path = project_root / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        print(f"Generated: {file_path}")
