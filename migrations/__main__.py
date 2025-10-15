"""
Migration CLI Tool
================

Command-line interface for managing database migrations with
comprehensive commands for all migration operations.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .migration_engine import MigrationEngine, MigrationConfig, MigrationStrategy, DatabaseType
from .version_control import VersionManager, VersionFormat, MigrationState

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationCLI:
    """Command-line interface for migration operations."""
    
    def __init__(self):
        self.engine = None
        self.version_manager = None
        self.config = None
    
    def setup_parser(self) -> argparse.ArgumentParser:
        """Setup argument parser with all commands."""
        parser = argparse.ArgumentParser(
            description='AI Nutritionist Database Migration Tool',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python -m migrations create "add_user_analytics_table"
  python -m migrations upgrade
  python -m migrations upgrade --strategy=zero-downtime
  python -m migrations downgrade
  python -m migrations status
  python -m migrations validate
  python -m migrations blue-green-deploy
  python -m migrations backfill --target-version=20241014_143000
  python -m migrations rollback --to-version=20241014_120000
            """
        )
        
        # Global options
        parser.add_argument(
            '--config',
            type=str,
            help='Path to configuration file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without executing'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        parser.add_argument(
            '--database-type',
            choices=['postgresql', 'mysql', 'sqlite', 'dynamodb'],
            default='dynamodb',
            help='Database type (default: dynamodb)'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Create command
        create_parser = subparsers.add_parser(
            'create',
            help='Create a new migration'
        )
        create_parser.add_argument(
            'name',
            help='Migration name'
        )
        create_parser.add_argument(
            '--version-format',
            choices=['timestamp', 'semantic', 'sequential'],
            default='timestamp',
            help='Version format (default: timestamp)'
        )
        create_parser.add_argument(
            '--template',
            choices=['sql', 'dynamodb', 'data_migration'],
            default='dynamodb',
            help='Migration template to use'
        )
        
        # Upgrade command
        upgrade_parser = subparsers.add_parser(
            'upgrade',
            help='Run pending migrations'
        )
        upgrade_parser.add_argument(
            '--target-version',
            help='Upgrade to specific version'
        )
        upgrade_parser.add_argument(
            '--strategy',
            choices=['standard', 'zero_downtime', 'blue_green', 'gradual'],
            default='standard',
            help='Migration strategy (default: standard)'
        )
        upgrade_parser.add_argument(
            '--auto-approve',
            action='store_true',
            help='Automatically approve migration execution'
        )
        
        # Downgrade command
        downgrade_parser = subparsers.add_parser(
            'downgrade',
            help='Rollback migrations'
        )
        downgrade_parser.add_argument(
            '--steps',
            type=int,
            default=1,
            help='Number of migrations to rollback (default: 1)'
        )
        downgrade_parser.add_argument(
            '--to-version',
            help='Rollback to specific version'
        )
        
        # Status command
        status_parser = subparsers.add_parser(
            'status',
            help='Show migration status'
        )
        status_parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)'
        )
        
        # Validate command
        validate_parser = subparsers.add_parser(
            'validate',
            help='Validate migrations'
        )
        validate_parser.add_argument(
            '--migration-path',
            help='Validate specific migration file'
        )
        
        # Blue-green deploy command
        bg_parser = subparsers.add_parser(
            'blue-green-deploy',
            help='Perform blue-green deployment'
        )
        bg_parser.add_argument(
            '--target-version',
            help='Target version for deployment'
        )
        
        # Backfill command
        backfill_parser = subparsers.add_parser(
            'backfill',
            help='Run data backfill operations'
        )
        backfill_parser.add_argument(
            '--target-version',
            required=True,
            help='Version containing backfill operations'
        )
        backfill_parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for backfill (default: 1000)'
        )
        
        # Rollback command
        rollback_parser = subparsers.add_parser(
            'rollback',
            help='Emergency rollback to previous version'
        )
        rollback_parser.add_argument(
            '--to-version',
            required=True,
            help='Version to rollback to'
        )
        
        # History command
        history_parser = subparsers.add_parser(
            'history',
            help='Show migration history'
        )
        history_parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Number of recent migrations to show (default: 10)'
        )
        
        # Conflicts command
        conflicts_parser = subparsers.add_parser(
            'conflicts',
            help='Manage migration conflicts'
        )
        conflicts_subparsers = conflicts_parser.add_subparsers(dest='conflicts_action')
        
        # List conflicts
        conflicts_subparsers.add_parser(
            'list',
            help='List migration conflicts'
        )
        
        # Resolve conflict
        resolve_parser = conflicts_subparsers.add_parser(
            'resolve',
            help='Resolve migration conflict'
        )
        resolve_parser.add_argument(
            'conflict_id',
            help='Conflict ID to resolve'
        )
        resolve_parser.add_argument(
            '--strategy',
            choices=['rename_source', 'rename_target', 'merge', 'abort'],
            required=True,
            help='Resolution strategy'
        )
        
        return parser
    
    async def run(self, args: List[str]) -> int:
        """Run the CLI with given arguments."""
        parser = self.setup_parser()
        parsed_args = parser.parse_args(args)
        
        # Setup logging
        if parsed_args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Initialize configuration
        await self._initialize_config(parsed_args)
        
        # Execute command
        try:
            if parsed_args.command == 'create':
                return await self._create_migration(parsed_args)
            elif parsed_args.command == 'upgrade':
                return await self._upgrade_migrations(parsed_args)
            elif parsed_args.command == 'downgrade':
                return await self._downgrade_migrations(parsed_args)
            elif parsed_args.command == 'status':
                return await self._show_status(parsed_args)
            elif parsed_args.command == 'validate':
                return await self._validate_migrations(parsed_args)
            elif parsed_args.command == 'blue-green-deploy':
                return await self._blue_green_deploy(parsed_args)
            elif parsed_args.command == 'backfill':
                return await self._run_backfill(parsed_args)
            elif parsed_args.command == 'rollback':
                return await self._emergency_rollback(parsed_args)
            elif parsed_args.command == 'history':
                return await self._show_history(parsed_args)
            elif parsed_args.command == 'conflicts':
                return await self._manage_conflicts(parsed_args)
            else:
                parser.print_help()
                return 1
                
        except Exception as e:
            logger.error(f"Command failed: {e}")
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    async def _initialize_config(self, args) -> None:
        """Initialize migration configuration."""
        # Create configuration
        self.config = MigrationConfig(
            database_type=DatabaseType(args.database_type),
            dry_run=args.dry_run
        )
        
        # Load from config file if provided
        if args.config:
            config_path = Path(args.config)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Update config with file values
                for key, value in config_data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
        
        # Initialize engine and version manager
        self.engine = MigrationEngine(self.config)
        self.version_manager = VersionManager()
        
        logger.info(f"Initialized for {self.config.database_type.value} database")
    
    async def _create_migration(self, args) -> int:
        """Create a new migration."""
        logger.info(f"Creating migration: {args.name}")
        
        # Generate version
        version_format = VersionFormat(args.version_format)
        version = self.version_manager.generate_version(version_format)
        
        # Create migration version
        migration_version = self.version_manager.create_version(
            version=version,
            name=args.name,
            description=f"Migration: {args.name}"
        )
        
        # Create migration file
        migration_file = await self._create_migration_file(
            migration_version, args.template
        )
        
        logger.info(f"✅ Created migration: {version}")
        logger.info(f"📄 File: {migration_file}")
        
        return 0
    
    async def _create_migration_file(self, migration_version, template: str) -> str:
        """Create migration file from template."""
        migrations_dir = Path("migrations/versions")
        migrations_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{migration_version.version}_{migration_version.name.replace(' ', '_')}.py"
        file_path = migrations_dir / filename
        
        # Get template content
        template_content = self._get_template_content(template, migration_version)
        
        # Write file
        with open(file_path, 'w') as f:
            f.write(template_content)
        
        # Update migration version with file path
        migration_version.file_path = str(file_path)
        
        return str(file_path)
    
    def _get_template_content(self, template: str, migration_version) -> str:
        """Get template content for migration file."""
        if template == 'dynamodb':
            return f'''\"\"\"
{migration_version.description}

Revision ID: {migration_version.version}
Created: {migration_version.created_at.isoformat()}
\"\"\"

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def upgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    \"\"\"
    Apply the migration.
    
    Args:
        dynamodb: DynamoDB resource
        dynamodb_client: DynamoDB client
        config: Migration configuration
        result: Migration result object
    \"\"\"
    logger.info("Applying migration: {migration_version.version}")
    
    # Example: Create a new table
    table_name = f"{{config.dynamodb_table_prefix}}-new-table"
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {{
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }}
            ],
            AttributeDefinitions=[
                {{
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }}
            ],
            BillingMode='PAY_PER_REQUEST',
            Tags=[
                {{
                    'Key': 'Migration',
                    'Value': '{migration_version.version}'
                }}
            ]
        )
        
        # Wait for table to be active
        table.wait_until_exists()
        
        logger.info(f"Created table: {{table_name}}")
        result.affected_tables.append(table_name)
        
    except Exception as e:
        logger.error(f"Failed to create table: {{e}}")
        raise


def downgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    \"\"\"
    Rollback the migration.
    
    Args:
        dynamodb: DynamoDB resource
        dynamodb_client: DynamoDB client
        config: Migration configuration
        result: Migration result object
    \"\"\"
    logger.info("Rolling back migration: {migration_version.version}")
    
    table_name = f"{{config.dynamodb_table_prefix}}-new-table"
    
    try:
        # Delete the table
        table = dynamodb.Table(table_name)
        table.delete()
        
        logger.info(f"Deleted table: {{table_name}}")
        
    except Exception as e:
        logger.error(f"Failed to delete table: {{e}}")
        raise
'''
        
        elif template == 'sql':
            return f'''\"\"\"
{migration_version.description}

Revision ID: {migration_version.version}
Created: {migration_version.created_at.isoformat()}
\"\"\"

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '{migration_version.version}'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    \"\"\"Apply the migration.\"\"\"
    # Example: Create a new table
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

def downgrade():
    \"\"\"Rollback the migration.\"\"\"
    op.drop_table('new_table')
'''
        
        elif template == 'data_migration':
            return f'''\"\"\"
{migration_version.description}

Revision ID: {migration_version.version}
Created: {migration_version.created_at.isoformat()}

Data Migration Template
\"\"\"

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# BACKFILL_TASK: migrate_user_data, batch_size=1000, strategy=batch_sequential
# SOURCE: SELECT * FROM users WHERE migrated = false
# TRANSFORM: add_new_field

def upgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    \"\"\"
    Apply the data migration.
    \"\"\"
    logger.info("Starting data migration: {migration_version.version}")
    
    # This migration will be automatically processed by the backfill strategy
    # based on the BACKFILL_TASK comments above
    
    logger.info("Data migration setup completed")

def downgrade(dynamodb, dynamodb_client, config, result, **kwargs):
    \"\"\"
    Rollback the data migration.
    \"\"\"
    logger.info("Rolling back data migration: {migration_version.version}")
    
    # Rollback logic would go here
    
    logger.info("Data migration rollback completed")

def add_new_field(record):
    \"\"\"
    Transform function for adding new field to records.
    \"\"\"
    record['new_field'] = 'default_value'
    record['migrated'] = True
    record['migration_timestamp'] = datetime.now(timezone.utc).isoformat()
    
    return record
'''
        
        else:
            raise ValueError(f"Unknown template: {template}")
    
    async def _upgrade_migrations(self, args) -> int:
        """Run pending migrations."""
        logger.info("Running pending migrations...")
        
        # Get migration path
        if args.target_version:
            migration_path = self.version_manager.get_migration_path(None, args.target_version)
        else:
            # Get all pending migrations
            ordered_versions = self.version_manager.get_dependency_order()
            applied_versions = {
                v.version for v in self.version_manager.list_versions(MigrationState.APPLIED)
            }
            migration_path = [v for v in ordered_versions if v not in applied_versions]
        
        if not migration_path:
            logger.info("✅ No pending migrations")
            return 0
        
        # Set strategy
        strategy = MigrationStrategy(args.strategy)
        self.config.strategy = strategy
        self.config.auto_approve = args.auto_approve
        
        # Execute migrations
        success_count = 0
        for version in migration_path:
            migration_info = self.version_manager.get_version_info(version)
            if not migration_info or not migration_info.file_path:
                logger.warning(f"Migration file not found for version: {version}")
                continue
            
            if not args.auto_approve:
                response = input(f"Apply migration {version} ({migration_info.name})? [y/N]: ")
                if response.lower() != 'y':
                    logger.info(f"Skipped migration: {version}")
                    continue
            
            logger.info(f"Applying migration: {version}")
            
            try:
                result = await self.engine.execute_migration(migration_info.file_path, version)
                
                if result.status.value == "completed":
                    self.version_manager.mark_applied(version)
                    success_count += 1
                    logger.info(f"✅ Applied migration: {version}")
                else:
                    logger.error(f"❌ Migration failed: {version} - {result.error_message}")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Migration failed: {version} - {e}")
                break
        
        logger.info(f"Applied {success_count} migrations")
        return 0 if success_count == len(migration_path) else 1
    
    async def _downgrade_migrations(self, args) -> int:
        """Rollback migrations."""
        logger.info("Rolling back migrations...")
        
        if args.to_version:
            # Rollback to specific version
            current_version = self._get_current_version()
            if current_version:
                rollback_path = self.version_manager.get_rollback_path(current_version, args.to_version)
            else:
                logger.error("No current version found")
                return 1
        else:
            # Rollback specified number of steps
            applied_versions = [
                v.version for v in self.version_manager.list_versions(MigrationState.APPLIED)
            ]
            applied_versions.sort(reverse=True)  # Most recent first
            
            if len(applied_versions) < args.steps:
                logger.error(f"Cannot rollback {args.steps} steps, only {len(applied_versions)} applied")
                return 1
            
            rollback_path = applied_versions[:args.steps]
        
        if not rollback_path:
            logger.info("No migrations to rollback")
            return 0
        
        # Execute rollbacks
        success_count = 0
        for version in rollback_path:
            migration_info = self.version_manager.get_version_info(version)
            if not migration_info:
                logger.warning(f"Migration info not found for version: {version}")
                continue
            
            logger.info(f"Rolling back migration: {version}")
            
            try:
                # Use engine's rollback functionality
                result = self.engine.rollback_to_version(version)
                
                if result.status.value == "completed":
                    success_count += 1
                    logger.info(f"✅ Rolled back migration: {version}")
                else:
                    logger.error(f"❌ Rollback failed: {version}")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Rollback failed: {version} - {e}")
                break
        
        logger.info(f"Rolled back {success_count} migrations")
        return 0 if success_count == len(rollback_path) else 1
    
    async def _show_status(self, args) -> int:
        """Show migration status."""
        versions = self.version_manager.list_versions()
        
        if args.format == 'json':
            status_data = {
                'total_migrations': len(versions),
                'applied': len([v for v in versions if v.state == MigrationState.APPLIED]),
                'pending': len([v for v in versions if v.state != MigrationState.APPLIED]),
                'migrations': [
                    {
                        'version': v.version,
                        'name': v.name,
                        'state': v.state.value,
                        'applied_at': v.applied_at.isoformat() if v.applied_at else None
                    }
                    for v in versions
                ]
            }
            print(json.dumps(status_data, indent=2))
        else:
            # Table format
            print("\\nMigration Status")
            print("=" * 60)
            print(f"{'Version':<20} {'Name':<25} {'State':<12} {'Applied'}")
            print("-" * 60)
            
            for version in versions:
                applied_str = version.applied_at.strftime('%Y-%m-%d %H:%M') if version.applied_at else '-'
                print(f"{version.version:<20} {version.name:<25} {version.state.value:<12} {applied_str}")
            
            print(f"\\nTotal: {len(versions)} migrations")
            print(f"Applied: {len([v for v in versions if v.state == MigrationState.APPLIED])}")
            print(f"Pending: {len([v for v in versions if v.state != MigrationState.APPLIED])}")
        
        return 0
    
    async def _validate_migrations(self, args) -> int:
        """Validate migrations."""
        if args.migration_path:
            # Validate specific migration
            is_valid, issues = self.engine.validate_migration(args.migration_path)
            
            if is_valid:
                logger.info(f"✅ Migration valid: {args.migration_path}")
                return 0
            else:
                logger.error(f"❌ Migration invalid: {args.migration_path}")
                for issue in issues:
                    logger.error(f"  - {issue}")
                return 1
        else:
            # Validate all migrations
            is_valid, issues = self.version_manager.validate_dependencies()
            
            if is_valid:
                logger.info("✅ All migrations valid")
                return 0
            else:
                logger.error("❌ Migration validation failed:")
                for issue in issues:
                    logger.error(f"  - {issue}")
                return 1
    
    async def _blue_green_deploy(self, args) -> int:
        """Perform blue-green deployment."""
        logger.info("Starting blue-green deployment...")
        
        # Set blue-green strategy
        self.config.strategy = MigrationStrategy.BLUE_GREEN
        
        # Get target version
        target_version = args.target_version or self._get_latest_version()
        if not target_version:
            logger.error("No target version specified")
            return 1
        
        migration_info = self.version_manager.get_version_info(target_version)
        if not migration_info:
            logger.error(f"Migration not found: {target_version}")
            return 1
        
        try:
            result = await self.engine.execute_migration(migration_info.file_path, target_version)
            
            if result.status.value == "completed":
                logger.info("✅ Blue-green deployment completed successfully")
                return 0
            else:
                logger.error(f"❌ Blue-green deployment failed: {result.error_message}")
                return 1
                
        except Exception as e:
            logger.error(f"❌ Blue-green deployment failed: {e}")
            return 1
    
    async def _run_backfill(self, args) -> int:
        """Run data backfill operations."""
        logger.info(f"Running backfill for version: {args.target_version}")
        
        # Set backfill strategy
        self.config.strategy = MigrationStrategy.STANDARD  # Backfill uses data backfilling strategy
        
        migration_info = self.version_manager.get_version_info(args.target_version)
        if not migration_info:
            logger.error(f"Migration not found: {args.target_version}")
            return 1
        
        try:
            result = await self.engine.execute_migration(migration_info.file_path, args.target_version)
            
            if result.status.value == "completed":
                logger.info("✅ Backfill completed successfully")
                
                # Show backfill metrics
                if 'backfill_progress' in result.metrics:
                    progress = result.metrics['backfill_progress']
                    logger.info(f"  Completion: {progress['completion_percentage']:.1f}%")
                    logger.info(f"  Rate: {progress['processing_rate']:.1f} records/sec")
                
                return 0
            else:
                logger.error(f"❌ Backfill failed: {result.error_message}")
                return 1
                
        except Exception as e:
            logger.error(f"❌ Backfill failed: {e}")
            return 1
    
    async def _emergency_rollback(self, args) -> int:
        """Perform emergency rollback."""
        logger.warning(f"Performing emergency rollback to version: {args.to_version}")
        
        try:
            result = self.engine.rollback_to_version(args.to_version)
            
            if result.status.value == "completed":
                logger.info("✅ Emergency rollback completed")
                return 0
            else:
                logger.error(f"❌ Emergency rollback failed: {result.error_message}")
                return 1
                
        except Exception as e:
            logger.error(f"❌ Emergency rollback failed: {e}")
            return 1
    
    async def _show_history(self, args) -> int:
        """Show migration history."""
        history = self.engine.get_migration_status()
        
        # Sort by completion time, most recent first
        history.sort(key=lambda r: r.completed_at or r.started_at, reverse=True)
        
        # Limit results
        if args.limit:
            history = history[:args.limit]
        
        print("\\nMigration History")
        print("=" * 80)
        print(f"{'Version':<20} {'Status':<12} {'Started':<16} {'Duration':<10} {'Error'}")
        print("-" * 80)
        
        for result in history:
            started = result.started_at.strftime('%Y-%m-%d %H:%M')
            duration = f"{result.duration_seconds:.1f}s" if result.duration_seconds else "-"
            error = result.error_message[:30] + "..." if result.error_message and len(result.error_message) > 30 else result.error_message or ""
            
            print(f"{result.version:<20} {result.status.value:<12} {started:<16} {duration:<10} {error}")
        
        print(f"\\nShowing {len(history)} most recent migrations")
        return 0
    
    async def _manage_conflicts(self, args) -> int:
        """Manage migration conflicts."""
        if args.conflicts_action == 'list':
            conflicts = self.version_manager.get_conflicts(resolved=False)
            
            if not conflicts:
                logger.info("✅ No unresolved conflicts")
                return 0
            
            print("\\nMigration Conflicts")
            print("=" * 60)
            print(f"{'ID':<20} {'Type':<20} {'Description'}")
            print("-" * 60)
            
            for conflict in conflicts:
                print(f"{str(conflict.conflict_id)[:18]:<20} {conflict.type.value:<20} {conflict.description[:40]}")
            
            return 0
        
        elif args.conflicts_action == 'resolve':
            from uuid import UUID
            
            try:
                conflict_id = UUID(args.conflict_id)
                success = self.version_manager.resolve_conflict(conflict_id, args.strategy)
                
                if success:
                    logger.info(f"✅ Conflict resolved: {conflict_id}")
                    return 0
                else:
                    logger.error(f"❌ Failed to resolve conflict: {conflict_id}")
                    return 1
                    
            except ValueError:
                logger.error(f"Invalid conflict ID: {args.conflict_id}")
                return 1
            except Exception as e:
                logger.error(f"❌ Error resolving conflict: {e}")
                return 1
        
        else:
            logger.error("Invalid conflicts action")
            return 1
    
    def _get_current_version(self) -> Optional[str]:
        """Get current migration version."""
        applied_versions = [
            v.version for v in self.version_manager.list_versions(MigrationState.APPLIED)
        ]
        
        if applied_versions:
            # Return most recent applied version
            ordered_versions = self.version_manager.get_dependency_order()
            for version in reversed(ordered_versions):
                if version in applied_versions:
                    return version
        
        return None
    
    def _get_latest_version(self) -> Optional[str]:
        """Get latest available version."""
        ordered_versions = self.version_manager.get_dependency_order()
        return ordered_versions[-1] if ordered_versions else None


def main():
    """Main entry point for CLI."""
    cli = MigrationCLI()
    
    # Run CLI
    exit_code = asyncio.run(cli.run(sys.argv[1:]))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
