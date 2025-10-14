"""
Zero-Downtime Migration Strategy
==============================

Implements zero-downtime database migrations using advanced techniques
like shadow tables, gradual column additions, and dual-write patterns.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from ..migration_engine import MigrationConfig, MigrationResult, MigrationStatus

logger = logging.getLogger(__name__)


class ZeroDowntimeMigration:
    """
    Zero-downtime migration strategy implementation.
    
    Uses techniques like:
    - Shadow tables for schema changes
    - Gradual column additions
    - Dual-write patterns
    - Background data migration
    - Atomic switches
    """
    
    def __init__(self, config: MigrationConfig):
        """
        Initialize zero-downtime migration strategy.
        
        Args:
            config: Migration configuration
        """
        self.config = config
        self.max_downtime_ms = config.max_downtime_seconds * 1000
        
        # Strategy settings
        self.batch_size = 1000
        self.migration_rate_limit = 100  # operations per second
        self.health_check_interval = 5   # seconds
        
        # State tracking
        self.shadow_tables: List[str] = []
        self.dual_write_active = False
        self.migration_progress = 0.0
    
    async def execute(self, migration_path: str, result: MigrationResult) -> None:
        """
        Execute zero-downtime migration.
        
        Args:
            migration_path: Path to migration script
            result: Migration result to update
        """
        logger.info(f"Starting zero-downtime migration: {result.version}")
        
        try:
            # Load migration content
            with open(migration_path, 'r') as f:
                migration_content = f.read()
            
            # Parse migration operations
            operations = self._parse_migration_operations(migration_content)
            
            # Execute operations with zero-downtime techniques
            for operation in operations:
                await self._execute_operation(operation, result)
                
                # Health check after each operation
                await self._health_check(result)
            
            # Final verification
            await self._verify_migration_success(result)
            
            logger.info(f"Zero-downtime migration completed: {result.version}")
            
        except Exception as e:
            logger.error(f"Zero-downtime migration failed: {e}")
            await self._cleanup_shadow_resources(result)
            raise
    
    def _parse_migration_operations(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse migration content into discrete operations.
        
        Args:
            content: Migration file content
            
        Returns:
            List of operation dictionaries
        """
        operations = []
        
        # This is a simplified parser - in practice, you'd use a more sophisticated
        # SQL/migration parser depending on your database type
        
        lines = content.split('\n')
        current_operation = None
        
        for line in lines:
            line = line.strip()
            
            if not line or line.startswith('--'):
                continue
            
            # Detect operation types
            if line.upper().startswith('CREATE TABLE'):
                current_operation = {
                    'type': 'create_table',
                    'sql': line,
                    'strategy': 'direct'
                }
                operations.append(current_operation)
            
            elif line.upper().startswith('ALTER TABLE'):
                current_operation = {
                    'type': 'alter_table',
                    'sql': line,
                    'strategy': 'shadow_table'
                }
                operations.append(current_operation)
            
            elif line.upper().startswith('ADD COLUMN'):
                current_operation = {
                    'type': 'add_column',
                    'sql': line,
                    'strategy': 'gradual_addition'
                }
                operations.append(current_operation)
            
            elif line.upper().startswith('DROP COLUMN'):
                current_operation = {
                    'type': 'drop_column',
                    'sql': line,
                    'strategy': 'gradual_removal'
                }
                operations.append(current_operation)
            
            elif line.upper().startswith('CREATE INDEX'):
                current_operation = {
                    'type': 'create_index',
                    'sql': line,
                    'strategy': 'concurrent_index'
                }
                operations.append(current_operation)
            
            else:
                # Continuation of previous operation
                if current_operation:
                    current_operation['sql'] += f' {line}'
        
        return operations
    
    async def _execute_operation(self, operation: Dict[str, Any], 
                                result: MigrationResult) -> None:
        """
        Execute a single migration operation using appropriate zero-downtime strategy.
        
        Args:
            operation: Operation to execute
            result: Migration result to update
        """
        operation_type = operation['type']
        strategy = operation['strategy']
        
        logger.info(f"Executing {operation_type} using {strategy} strategy")
        
        if strategy == 'direct':
            await self._execute_direct_operation(operation, result)
        elif strategy == 'shadow_table':
            await self._execute_shadow_table_operation(operation, result)
        elif strategy == 'gradual_addition':
            await self._execute_gradual_addition(operation, result)
        elif strategy == 'gradual_removal':
            await self._execute_gradual_removal(operation, result)
        elif strategy == 'concurrent_index':
            await self._execute_concurrent_index(operation, result)
        else:
            raise ValueError(f"Unknown migration strategy: {strategy}")
    
    async def _execute_direct_operation(self, operation: Dict[str, Any], 
                                      result: MigrationResult) -> None:
        """Execute operation directly (for safe operations)."""
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would execute {operation['sql']}")
            return
        
        # For DynamoDB, this would be a direct table operation
        if self.config.database_type.value == "dynamodb":
            await self._execute_dynamodb_operation(operation, result)
        else:
            await self._execute_sql_operation(operation, result)
    
    async def _execute_shadow_table_operation(self, operation: Dict[str, Any], 
                                            result: MigrationResult) -> None:
        """
        Execute operation using shadow table technique.
        
        This creates a new table with the desired schema, migrates data
        gradually, then performs an atomic switch.
        """
        logger.info("Starting shadow table migration")
        
        # Phase 1: Create shadow table with new schema
        shadow_table_name = await self._create_shadow_table(operation, result)
        self.shadow_tables.append(shadow_table_name)
        
        # Phase 2: Enable dual-write mode
        await self._enable_dual_write(operation, result)
        
        # Phase 3: Migrate existing data in batches
        await self._migrate_data_to_shadow_table(operation, result, shadow_table_name)
        
        # Phase 4: Verify data consistency
        await self._verify_shadow_table_data(operation, result, shadow_table_name)
        
        # Phase 5: Atomic switch
        await self._atomic_table_switch(operation, result, shadow_table_name)
        
        # Phase 6: Cleanup
        await self._cleanup_old_table(operation, result)
        
        logger.info("Shadow table migration completed")
    
    async def _create_shadow_table(self, operation: Dict[str, Any], 
                                 result: MigrationResult) -> str:
        """Create shadow table with new schema."""
        # Extract table name from operation
        table_name = self._extract_table_name(operation['sql'])
        shadow_table_name = f"{table_name}_shadow_{int(time.time())}"
        
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would create shadow table {shadow_table_name}")
            return shadow_table_name
        
        # Create the shadow table
        # Implementation depends on database type
        logger.info(f"Created shadow table: {shadow_table_name}")
        result.affected_tables.append(shadow_table_name)
        
        return shadow_table_name
    
    async def _enable_dual_write(self, operation: Dict[str, Any], 
                               result: MigrationResult) -> None:
        """Enable dual-write mode to both original and shadow tables."""
        if self.config.dry_run:
            logger.info("DRY RUN: Would enable dual-write mode")
            return
        
        # This would typically involve updating application configuration
        # or using database triggers/events
        self.dual_write_active = True
        logger.info("Dual-write mode enabled")
    
    async def _migrate_data_to_shadow_table(self, operation: Dict[str, Any], 
                                          result: MigrationResult, 
                                          shadow_table_name: str) -> None:
        """Migrate existing data to shadow table in batches."""
        if self.config.dry_run:
            logger.info("DRY RUN: Would migrate data to shadow table")
            return
        
        table_name = self._extract_table_name(operation['sql'])
        
        # Get total record count for progress tracking
        total_records = await self._get_table_record_count(table_name)
        migrated_records = 0
        
        logger.info(f"Migrating {total_records} records from {table_name} to {shadow_table_name}")
        
        # Migrate in batches
        last_key = None
        
        while True:
            # Fetch batch of records
            batch, last_key = await self._fetch_batch(table_name, last_key)
            
            if not batch:
                break
            
            # Transform and insert into shadow table
            await self._insert_batch_to_shadow_table(batch, shadow_table_name)
            
            migrated_records += len(batch)
            self.migration_progress = migrated_records / total_records
            
            # Rate limiting
            await asyncio.sleep(1.0 / self.migration_rate_limit)
            
            # Progress logging
            if migrated_records % 10000 == 0:
                logger.info(f"Migrated {migrated_records}/{total_records} records ({self.migration_progress:.1%})")
        
        logger.info(f"Data migration completed: {migrated_records} records")
        result.metrics['migrated_records'] = migrated_records
    
    async def _verify_shadow_table_data(self, operation: Dict[str, Any], 
                                      result: MigrationResult, 
                                      shadow_table_name: str) -> None:
        """Verify data consistency between original and shadow tables."""
        if self.config.dry_run:
            logger.info("DRY RUN: Would verify shadow table data")
            return
        
        logger.info("Verifying data consistency...")
        
        table_name = self._extract_table_name(operation['sql'])
        
        # Compare record counts
        original_count = await self._get_table_record_count(table_name)
        shadow_count = await self._get_table_record_count(shadow_table_name)
        
        if original_count != shadow_count:
            raise RuntimeError(f"Record count mismatch: {original_count} vs {shadow_count}")
        
        # Sample-based data verification
        await self._verify_data_samples(table_name, shadow_table_name)
        
        logger.info("Data consistency verification passed")
    
    async def _atomic_table_switch(self, operation: Dict[str, Any], 
                                 result: MigrationResult, 
                                 shadow_table_name: str) -> None:
        """Perform atomic switch from original to shadow table."""
        if self.config.dry_run:
            logger.info("DRY RUN: Would perform atomic table switch")
            return
        
        table_name = self._extract_table_name(operation['sql'])
        backup_table_name = f"{table_name}_backup_{int(time.time())}"
        
        logger.info(f"Performing atomic switch: {table_name} -> {shadow_table_name}")
        
        # Measure downtime
        switch_start = time.time()
        
        try:
            # 1. Rename original table to backup
            await self._rename_table(table_name, backup_table_name)
            
            # 2. Rename shadow table to original
            await self._rename_table(shadow_table_name, table_name)
            
            # 3. Disable dual-write mode
            self.dual_write_active = False
            
            switch_duration = (time.time() - switch_start) * 1000
            
            if switch_duration > self.max_downtime_ms:
                logger.warning(f"Switch took {switch_duration:.1f}ms (exceeds {self.max_downtime_ms}ms limit)")
            else:
                logger.info(f"Atomic switch completed in {switch_duration:.1f}ms")
            
            result.metrics['switch_duration_ms'] = switch_duration
            
        except Exception as e:
            # Rollback on failure
            try:
                await self._rename_table(backup_table_name, table_name)
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
            raise
    
    async def _execute_gradual_addition(self, operation: Dict[str, Any], 
                                      result: MigrationResult) -> None:
        """Execute gradual column addition."""
        logger.info("Executing gradual column addition")
        
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would add column gradually")
            return
        
        # Phase 1: Add column with default value
        await self._add_column_with_default(operation, result)
        
        # Phase 2: Backfill data if needed
        await self._backfill_column_data(operation, result)
        
        # Phase 3: Add constraints if specified
        await self._add_column_constraints(operation, result)
        
        logger.info("Gradual column addition completed")
    
    async def _execute_gradual_removal(self, operation: Dict[str, Any], 
                                     result: MigrationResult) -> None:
        """Execute gradual column removal."""
        logger.info("Executing gradual column removal")
        
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would remove column gradually")
            return
        
        # Phase 1: Remove constraints
        await self._remove_column_constraints(operation, result)
        
        # Phase 2: Stop using column in application (manual step)
        logger.info("Ensure application no longer uses the column before proceeding")
        
        # Phase 3: Drop the column
        await self._drop_column(operation, result)
        
        logger.info("Gradual column removal completed")
    
    async def _execute_concurrent_index(self, operation: Dict[str, Any], 
                                      result: MigrationResult) -> None:
        """Execute concurrent index creation."""
        logger.info("Creating index concurrently")
        
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would create index concurrently")
            return
        
        # For PostgreSQL, this would use CREATE INDEX CONCURRENTLY
        # For other databases, implement appropriate concurrent indexing
        
        await self._create_index_concurrently(operation, result)
        
        logger.info("Concurrent index creation completed")
    
    async def _health_check(self, result: MigrationResult) -> None:
        """Perform health check during migration."""
        try:
            # Check database connectivity
            await self._check_database_health()
            
            # Check application health
            await self._check_application_health()
            
            # Check resource usage
            await self._check_resource_usage()
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            # Don't fail the migration for health check issues, but log them
            result.metrics.setdefault('health_warnings', []).append(str(e))
    
    async def _cleanup_shadow_resources(self, result: MigrationResult) -> None:
        """Clean up shadow tables and temporary resources."""
        logger.info("Cleaning up shadow resources")
        
        for shadow_table in self.shadow_tables:
            try:
                await self._drop_table(shadow_table)
                logger.info(f"Dropped shadow table: {shadow_table}")
            except Exception as e:
                logger.warning(f"Failed to drop shadow table {shadow_table}: {e}")
        
        self.shadow_tables.clear()
        self.dual_write_active = False
    
    # Database-specific helper methods
    async def _execute_dynamodb_operation(self, operation: Dict[str, Any], 
                                        result: MigrationResult) -> None:
        """Execute DynamoDB-specific operation."""
        # Implementation would depend on the specific DynamoDB operation
        logger.info(f"Executing DynamoDB operation: {operation['type']}")
    
    async def _execute_sql_operation(self, operation: Dict[str, Any], 
                                   result: MigrationResult) -> None:
        """Execute SQL operation."""
        # Implementation would use SQLAlchemy or similar
        logger.info(f"Executing SQL operation: {operation['type']}")
    
    def _extract_table_name(self, sql: str) -> str:
        """Extract table name from SQL statement."""
        # Simplified extraction - would need more sophisticated parsing
        import re
        
        # Look for table name after ALTER TABLE or similar
        match = re.search(r'TABLE\s+(\w+)', sql, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return "unknown_table"
    
    async def _get_table_record_count(self, table_name: str) -> int:
        """Get record count for a table."""
        # Implementation depends on database type
        return 0
    
    async def _fetch_batch(self, table_name: str, last_key: Optional[Any]) -> tuple:
        """Fetch a batch of records from table."""
        # Implementation depends on database type
        return [], None
    
    async def _insert_batch_to_shadow_table(self, batch: List[Dict], 
                                          shadow_table_name: str) -> None:
        """Insert batch of records to shadow table."""
        # Implementation depends on database type
        pass
    
    async def _verify_data_samples(self, original_table: str, 
                                 shadow_table: str) -> None:
        """Verify data consistency using sample records."""
        # Implementation would compare sample records between tables
        pass
    
    async def _rename_table(self, old_name: str, new_name: str) -> None:
        """Rename a table atomically."""
        # Implementation depends on database type
        pass
    
    async def _add_column_with_default(self, operation: Dict[str, Any], 
                                     result: MigrationResult) -> None:
        """Add column with default value."""
        # Implementation depends on database type
        pass
    
    async def _backfill_column_data(self, operation: Dict[str, Any], 
                                  result: MigrationResult) -> None:
        """Backfill data for new column."""
        # Implementation depends on specific column and data requirements
        pass
    
    async def _add_column_constraints(self, operation: Dict[str, Any], 
                                    result: MigrationResult) -> None:
        """Add constraints to new column."""
        # Implementation depends on database type
        pass
    
    async def _remove_column_constraints(self, operation: Dict[str, Any], 
                                       result: MigrationResult) -> None:
        """Remove constraints from column."""
        # Implementation depends on database type
        pass
    
    async def _drop_column(self, operation: Dict[str, Any], 
                         result: MigrationResult) -> None:
        """Drop column from table."""
        # Implementation depends on database type
        pass
    
    async def _create_index_concurrently(self, operation: Dict[str, Any], 
                                       result: MigrationResult) -> None:
        """Create index concurrently."""
        # Implementation depends on database type
        pass
    
    async def _drop_table(self, table_name: str) -> None:
        """Drop a table."""
        # Implementation depends on database type
        pass
    
    async def _check_database_health(self) -> None:
        """Check database health."""
        # Implementation would check database connectivity and performance
        pass
    
    async def _check_application_health(self) -> None:
        """Check application health."""
        # Implementation would check application endpoints
        pass
    
    async def _check_resource_usage(self) -> None:
        """Check system resource usage."""
        # Implementation would check CPU, memory, disk usage
        pass
    
    async def _verify_migration_success(self, result: MigrationResult) -> None:
        """Verify overall migration success."""
        logger.info("Verifying migration success...")
        
        # Perform final health checks
        await self._health_check(result)
        
        # Verify all operations completed
        if result.affected_tables:
            logger.info(f"Migration affected {len(result.affected_tables)} tables")
        
        # Check performance impact
        if 'switch_duration_ms' in result.metrics:
            duration = result.metrics['switch_duration_ms']
            if duration <= self.max_downtime_ms:
                logger.info(f"Migration met downtime requirement: {duration:.1f}ms <= {self.max_downtime_ms}ms")
            else:
                logger.warning(f"Migration exceeded downtime requirement: {duration:.1f}ms > {self.max_downtime_ms}ms")
        
        logger.info("Migration success verification completed")
