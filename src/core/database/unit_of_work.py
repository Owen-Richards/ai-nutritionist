"""
Unit of Work implementation for coordinated database operations.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Type, TypeVar, Set
from datetime import datetime
from dataclasses import dataclass, field

from .abstractions import UnitOfWork, Repository, Entity, UnitOfWorkError
from .connection_pool import get_connection_pool, Connection
from .monitoring import get_query_monitor
from .repositories import UserProfileRepository, MealPlanRepository

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Entity)


@dataclass
class ChangeTracker:
    """Tracks changes to entities within a unit of work."""
    
    new_entities: Set[Any] = field(default_factory=set)
    dirty_entities: Set[Any] = field(default_factory=set)
    removed_entities: Set[Any] = field(default_factory=set)
    
    def mark_new(self, entity: Any):
        """Mark entity as new."""
        self.new_entities.add(entity)
        # Remove from other sets if present
        self.dirty_entities.discard(entity)
        self.removed_entities.discard(entity)
    
    def mark_dirty(self, entity: Any):
        """Mark entity as modified."""
        if entity not in self.new_entities:
            self.dirty_entities.add(entity)
        self.removed_entities.discard(entity)
    
    def mark_removed(self, entity: Any):
        """Mark entity as removed."""
        self.removed_entities.add(entity)
        self.new_entities.discard(entity)
        self.dirty_entities.discard(entity)
    
    def clear(self):
        """Clear all tracked changes."""
        self.new_entities.clear()
        self.dirty_entities.clear()
        self.removed_entities.clear()
    
    @property
    def has_changes(self) -> bool:
        """Check if there are any pending changes."""
        return bool(self.new_entities or self.dirty_entities or self.removed_entities)


class DynamoDBUnitOfWork(UnitOfWork):
    """
    DynamoDB-specific Unit of Work implementation.
    
    Features:
    - Transaction coordination across multiple tables
    - Change tracking
    - Rollback support via compensation
    - Performance monitoring
    - Optimistic concurrency control
    """
    
    def __init__(self):
        super().__init__()
        self._connection: Optional[Connection] = None
        self._change_tracker = ChangeTracker()
        self._savepoints: List[ChangeTracker] = []
        self._transaction_started = False
        self._transaction_items: List[Dict[str, Any]] = []
        
        # Initialize repositories
        self._repositories = {
            'users': UserProfileRepository(),
            'meal_plans': MealPlanRepository(),
        }
    
    async def begin(self) -> None:
        """Begin the unit of work transaction."""
        if self._transaction_started:
            raise UnitOfWorkError("Transaction already started")
        
        try:
            # Get connection from pool
            pool = await get_connection_pool()
            self._connection = await pool.get_connection().__aenter__()
            
            self._transaction_started = True
            self._change_tracker.clear()
            self._transaction_items.clear()
            
            logger.debug("Unit of work transaction started")
            
        except Exception as e:
            logger.error(f"Failed to begin transaction: {e}")
            raise UnitOfWorkError(f"Failed to begin transaction: {e}")
    
    async def commit(self) -> None:
        """Commit all changes in the unit of work."""
        if not self._transaction_started:
            raise UnitOfWorkError("No active transaction")
        
        if not self._change_tracker.has_changes:
            logger.debug("No changes to commit")
            return
        
        monitor = get_query_monitor()
        
        try:
            # Execute all changes as a DynamoDB transaction
            async with monitor.monitor_query(
                "transact_write", 
                "multiple_tables", 
                {"item_count": len(self._transaction_items)}
            ) as query_id:
                
                await self._execute_transaction()
            
            # Mark as committed
            self._is_committed = True
            self._change_tracker.clear()
            
            logger.debug(f"Unit of work committed successfully with {len(self._transaction_items)} items")
            
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            await self.rollback()
            raise UnitOfWorkError(f"Failed to commit transaction: {e}")
    
    async def rollback(self) -> None:
        """Rollback all changes."""
        if not self._transaction_started:
            return
        
        try:
            # For DynamoDB, we implement compensation-based rollback
            # since it doesn't support traditional ACID transactions across tables
            await self._execute_compensation()
            
            self._change_tracker.clear()
            self._transaction_items.clear()
            
            logger.debug("Unit of work rolled back")
            
        except Exception as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise UnitOfWorkError(f"Failed to rollback transaction: {e}")
        finally:
            self._transaction_started = False
            if self._connection:
                await self._connection.__aexit__(None, None, None)
                self._connection = None
    
    def create_savepoint(self) -> str:
        """Create a savepoint for partial rollback."""
        savepoint_id = f"sp_{len(self._savepoints)}"
        
        # Deep copy current change tracker state
        savepoint = ChangeTracker()
        savepoint.new_entities = self._change_tracker.new_entities.copy()
        savepoint.dirty_entities = self._change_tracker.dirty_entities.copy()
        savepoint.removed_entities = self._change_tracker.removed_entities.copy()
        
        self._savepoints.append(savepoint)
        
        logger.debug(f"Created savepoint {savepoint_id}")
        return savepoint_id
    
    async def rollback_to_savepoint(self, savepoint_id: str) -> None:
        """Rollback to a specific savepoint."""
        try:
            savepoint_index = int(savepoint_id.split('_')[1])
            
            if savepoint_index >= len(self._savepoints):
                raise UnitOfWorkError(f"Invalid savepoint: {savepoint_id}")
            
            # Restore state to savepoint
            savepoint = self._savepoints[savepoint_index]
            self._change_tracker.new_entities = savepoint.new_entities.copy()
            self._change_tracker.dirty_entities = savepoint.dirty_entities.copy()
            self._change_tracker.removed_entities = savepoint.removed_entities.copy()
            
            # Remove savepoints after this one
            self._savepoints = self._savepoints[:savepoint_index]
            
            logger.debug(f"Rolled back to savepoint {savepoint_id}")
            
        except Exception as e:
            logger.error(f"Failed to rollback to savepoint {savepoint_id}: {e}")
            raise UnitOfWorkError(f"Failed to rollback to savepoint: {e}")
    
    def register_new(self, entity: Any) -> None:
        """Register new entity for insertion."""
        self._change_tracker.mark_new(entity)
        self._prepare_transaction_item(entity, "Put")
    
    def register_dirty(self, entity: Any) -> None:
        """Register entity for update."""
        self._change_tracker.mark_dirty(entity)
        self._prepare_transaction_item(entity, "Update")
    
    def register_removed(self, entity: Any) -> None:
        """Register entity for deletion."""
        self._change_tracker.mark_removed(entity)
        self._prepare_transaction_item(entity, "Delete")
    
    def get_repository(self, entity_type: str) -> Repository:
        """Get repository for entity type."""
        if entity_type not in self._repositories:
            raise UnitOfWorkError(f"No repository registered for {entity_type}")
        return self._repositories[entity_type]
    
    def register_repository(self, entity_type: str, repository: Repository) -> None:
        """Register repository for entity type."""
        self._repositories[entity_type] = repository
    
    async def flush(self) -> None:
        """Flush pending changes without committing."""
        if not self._change_tracker.has_changes:
            return
        
        try:
            # Execute transaction items
            await self._execute_transaction()
            
            logger.debug(f"Flushed {len(self._transaction_items)} changes")
            
        except Exception as e:
            logger.error(f"Failed to flush changes: {e}")
            raise UnitOfWorkError(f"Failed to flush changes: {e}")
    
    def _prepare_transaction_item(self, entity: Any, operation: str) -> None:
        """Prepare transaction item for DynamoDB TransactWrite."""
        # Determine table name based on entity type
        table_name = self._get_table_name_for_entity(entity)
        
        if operation == "Put":
            # Convert entity to DynamoDB item format
            item = self._entity_to_item(entity)
            transaction_item = {
                "Put": {
                    "TableName": table_name,
                    "Item": item,
                    "ConditionExpression": "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": self._get_id_field(entity)}
                }
            }
        
        elif operation == "Update":
            # Create update expression
            item = self._entity_to_item(entity)
            key = {self._get_id_field(entity): str(entity.id)}
            
            # Build update expression
            update_expressions = []
            expression_values = {}
            expression_names = {}
            
            for field, value in item.items():
                if field != self._get_id_field(entity):
                    field_placeholder = f"#{field}"
                    value_placeholder = f":{field}"
                    
                    update_expressions.append(f"{field_placeholder} = {value_placeholder}")
                    expression_names[field_placeholder] = field
                    expression_values[value_placeholder] = value
            
            transaction_item = {
                "Update": {
                    "TableName": table_name,
                    "Key": key,
                    "UpdateExpression": f"SET {', '.join(update_expressions)}",
                    "ExpressionAttributeNames": expression_names,
                    "ExpressionAttributeValues": expression_values,
                    "ConditionExpression": "attribute_exists(#id)",
                }
            }
            transaction_item["Update"]["ExpressionAttributeNames"]["#id"] = self._get_id_field(entity)
        
        elif operation == "Delete":
            key = {self._get_id_field(entity): str(entity.id)}
            
            transaction_item = {
                "Delete": {
                    "TableName": table_name,
                    "Key": key,
                    "ConditionExpression": "attribute_exists(#id)",
                    "ExpressionAttributeNames": {"#id": self._get_id_field(entity)}
                }
            }
        
        else:
            raise UnitOfWorkError(f"Unknown operation: {operation}")
        
        self._transaction_items.append(transaction_item)
    
    async def _execute_transaction(self) -> None:
        """Execute DynamoDB transaction."""
        if not self._transaction_items:
            return
        
        if not self._connection:
            raise UnitOfWorkError("No active connection")
        
        # DynamoDB has a limit of 25 items per TransactWrite
        batch_size = 25
        
        for i in range(0, len(self._transaction_items), batch_size):
            batch_items = self._transaction_items[i:i + batch_size]
            
            try:
                await asyncio.to_thread(
                    self._connection.dynamodb.meta.client.transact_write_items,
                    TransactItems=batch_items
                )
                
            except Exception as e:
                logger.error(f"Transaction batch failed: {e}")
                raise
        
        # Clear processed items
        self._transaction_items.clear()
    
    async def _execute_compensation(self) -> None:
        """Execute compensation actions for rollback."""
        # For each new entity, delete it
        for entity in self._change_tracker.new_entities:
            try:
                table_name = self._get_table_name_for_entity(entity)
                table = self._connection.get_table(table_name)
                
                key = {self._get_id_field(entity): str(entity.id)}
                await asyncio.to_thread(table.delete_item, Key=key)
                
            except Exception as e:
                logger.warning(f"Failed to compensate new entity {entity}: {e}")
        
        # For dirty entities, we'd need to restore original values
        # This would require keeping snapshots of original state
        
        # For removed entities, we'd need to restore them
        # This also requires keeping snapshots
        
        logger.debug("Compensation rollback completed")
    
    def _get_table_name_for_entity(self, entity: Any) -> str:
        """Get DynamoDB table name for entity type."""
        entity_type = type(entity).__name__
        
        table_mapping = {
            "UserProfile": "ai-nutritionist-users",
            "GeneratedMealPlan": "ai-nutritionist-meal-plans",
            "PlanFeedback": "ai-nutritionist-feedback",
        }
        
        return table_mapping.get(entity_type, f"ai-nutritionist-{entity_type.lower()}")
    
    def _get_id_field(self, entity: Any) -> str:
        """Get ID field name for entity type."""
        entity_type = type(entity).__name__
        
        id_field_mapping = {
            "UserProfile": "user_id",
            "GeneratedMealPlan": "plan_id",
            "PlanFeedback": "feedback_id",
        }
        
        return id_field_mapping.get(entity_type, "id")
    
    def _entity_to_item(self, entity: Any) -> Dict[str, Any]:
        """Convert entity to DynamoDB item."""
        # This would use the repository's conversion logic
        entity_type = type(entity).__name__
        
        if entity_type == "UserProfile":
            repo = self._repositories.get('users')
            if repo:
                return repo._user_to_item(entity)
        elif entity_type == "GeneratedMealPlan":
            repo = self._repositories.get('meal_plans')
            if repo:
                # Implement _plan_to_item method in repository
                pass
        
        # Fallback: convert using entity's to_dict method if available
        if hasattr(entity, 'to_dict'):
            return entity.to_dict()
        
        raise UnitOfWorkError(f"Cannot convert entity of type {entity_type} to DynamoDB item")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get unit of work statistics."""
        return {
            "transaction_started": self._transaction_started,
            "is_committed": self._is_committed,
            "pending_new": len(self._change_tracker.new_entities),
            "pending_dirty": len(self._change_tracker.dirty_entities),
            "pending_removed": len(self._change_tracker.removed_entities),
            "savepoints": len(self._savepoints),
            "transaction_items": len(self._transaction_items)
        }
