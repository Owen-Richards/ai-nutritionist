"""
Database Migration Framework
==========================

A comprehensive migration framework supporting both SQL and NoSQL databases
with enterprise-grade features for zero-downtime deployments.
"""

from .migration_engine import MigrationEngine, MigrationConfig
from .version_control import VersionManager, MigrationVersion
from .strategies import (
    ZeroDowntimeMigration,
    BlueGreenMigration,
    GradualEvolution,
    DataBackfilling
)

__version__ = "1.0.0"
__author__ = "AI Nutritionist Team"

__all__ = [
    "MigrationEngine",
    "MigrationConfig", 
    "VersionManager",
    "MigrationVersion",
    "ZeroDowntimeMigration",
    "BlueGreenMigration", 
    "GradualEvolution",
    "DataBackfilling"
]
