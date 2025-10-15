"""
Alembic Environment Configuration
===============================

Configures Alembic for SQL database migrations with support for
multiple database backends and advanced migration features.
"""

import logging
import os
import sys
from logging.config import fileConfig
from typing import Optional

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config.settings import get_settings

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger(__name__)

# Add your model's MetaData object here for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# Configuration
settings = get_settings()


def get_database_url() -> str:
    """
    Get database URL from environment or configuration.
    
    Supports multiple database backends:
    - PostgreSQL
    - MySQL
    - SQLite
    """
    # Check for explicit database URL
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Build from components
    db_type = os.getenv('DB_TYPE', 'postgresql')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'ai_nutritionist')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    if db_type == 'postgresql':
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    elif db_type == 'mysql':
        return f"mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    elif db_type == 'sqlite':
        return f"sqlite:///{db_name}.db"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects to include in migrations.
    
    Args:
        object: The schema object
        name: Object name
        type_: Object type (table, column, etc.)
        reflected: True if object was reflected from database
        compare_to: Comparison object for autogenerate
    
    Returns:
        bool: True if object should be included
    """
    # Skip temporary tables
    if type_ == "table" and name.startswith("temp_"):
        return False
    
    # Skip system tables
    if type_ == "table" and name.startswith("sys_"):
        return False
    
    # Skip alembic version table
    if type_ == "table" and name == "alembic_version":
        return False
    
    return True


def compare_type(context, inspected_column, metadata_column, 
                inspected_type, metadata_type):
    """
    Custom type comparison for autogenerate.
    
    Returns:
        bool or None: True if types differ, False if same, None for default behavior
    """
    # Handle JSON type variations
    if hasattr(metadata_type, 'impl') and hasattr(inspected_type, 'impl'):
        if str(metadata_type.impl) == str(inspected_type.impl):
            return False
    
    # Default comparison
    return None


def compare_server_default(context, inspected_column, metadata_column,
                          inspected_default, metadata_default, rendered_metadata_default):
    """
    Custom server default comparison for autogenerate.
    
    Returns:
        bool: True if defaults differ, False if same
    """
    # Handle timezone-aware defaults
    if inspected_default and metadata_default:
        if "timezone" in str(inspected_default).lower() and "timezone" in str(metadata_default).lower():
            return False
    
    # Default comparison
    return inspected_default != rendered_metadata_default


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=compare_type,
        compare_server_default=compare_server_default,
        render_as_batch=True,  # Enable batch mode for SQLite
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Override sqlalchemy.url in config
    config_dict = config.get_section(config.config_ini_section)
    config_dict['sqlalchemy.url'] = get_database_url()
    
    connectable = engine_from_config(
        config_dict,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=compare_type,
            compare_server_default=compare_server_default,
            render_as_batch=True,  # Enable batch mode for SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_with_backup() -> None:
    """
    Run migrations with automatic backup creation.
    """
    from .migration_engine import MigrationEngine
    
    engine = MigrationEngine()
    
    # Create backup before migration
    logger.info("Creating database backup before migration...")
    backup_id = engine.create_backup()
    logger.info(f"Backup created with ID: {backup_id}")
    
    try:
        # Run the actual migration
        if context.is_offline_mode():
            run_migrations_offline()
        else:
            run_migrations_online()
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        
        # Attempt rollback
        logger.info("Attempting automatic rollback...")
        try:
            engine.restore_backup(backup_id)
            logger.info("Rollback completed successfully")
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {rollback_error}")
            logger.error("Manual intervention required!")
        
        raise


# Main execution
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
