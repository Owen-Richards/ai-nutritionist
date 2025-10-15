"""
Configure Migration Environment

This file configures the migration environment and provides
a simple test to validate the migration framework setup.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from migrations.migration_engine import MigrationEngine, MigrationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_migration_framework():
    """Test the migration framework setup."""
    logger.info("🧪 Testing Migration Framework Setup...")
    
    try:
        # Create test configuration
        config = MigrationConfig(
            aws_region='us-east-1',
            dynamodb_table_prefix='test-nutritionist',
            migration_table_name='test-nutritionist-migrations',
            backup_enabled=True,
            dry_run=True  # Safe test mode
        )
        
        # Initialize migration engine
        engine = MigrationEngine(config)
        
        # Test basic functionality
        logger.info("✅ Migration engine initialized successfully")
        
        # Test configuration validation
        validation_result = await engine.validate_configuration()
        if validation_result:
            logger.info("✅ Configuration validation passed")
        else:
            logger.error("❌ Configuration validation failed")
            return False
        
        # Test migration discovery
        migrations_dir = Path(__file__).parent / "versions"
        if migrations_dir.exists():
            migration_files = list(migrations_dir.glob("*.py"))
            logger.info(f"✅ Found {len(migration_files)} migration files")
            
            for migration_file in migration_files:
                logger.info(f"  📄 {migration_file.name}")
        else:
            logger.warning("⚠️  No migrations directory found")
        
        logger.info("🎉 Migration framework test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration framework test failed: {e}")
        return False


def print_migration_usage():
    """Print usage instructions for the migration framework."""
    print("""
🚀 AI Nutritionist - Database Migration Framework

USAGE EXAMPLES:

1. Create a new migration:
   python -m migrations create "add_user_settings_table"

2. Run all pending migrations:
   python -m migrations upgrade

3. Check migration status:
   python -m migrations status

4. Rollback last migration:
   python -m migrations downgrade

5. Blue-green deployment:
   python -m migrations blue-green-deploy

6. Data backfilling:
   python -m migrations backfill --strategy batch

7. View migration history:
   python -m migrations history

8. Validate migrations:
   python -m migrations validate

CONFIGURATION:
- Set AWS_REGION environment variable (default: us-east-1)
- Set DYNAMODB_TABLE_PREFIX environment variable (default: nutritionist)
- Ensure AWS credentials are configured

MIGRATION FILES:
- Located in: migrations/versions/
- Format: YYYYMMDD_HHMMSS_description.py
- Must implement upgrade() and downgrade() functions

STRATEGIES AVAILABLE:
- Zero-downtime: For production deployments with no service interruption
- Blue-green: Complete environment isolation during deployment
- Gradual evolution: Progressive rollout with feature flags
- Data backfilling: Efficient large-scale data migrations

For more information, see: migrations/README.md
""")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration Framework Test & Setup")
    parser.add_argument('--test', action='store_true', help='Run framework test')
    parser.add_argument('--usage', action='store_true', help='Show usage examples')
    
    args = parser.parse_args()
    
    if args.test:
        # Run async test
        result = asyncio.run(test_migration_framework())
        sys.exit(0 if result else 1)
    elif args.usage:
        print_migration_usage()
    else:
        # Default: show usage
        print_migration_usage()
