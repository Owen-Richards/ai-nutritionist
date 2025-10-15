"""
Migration Version Control System
==============================

Advanced version control for database migrations with conflict resolution,
dependency tracking, and semantic versioning support.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class VersionFormat(str, Enum):
    """Version format types."""
    SEMANTIC = "semantic"  # 1.2.3
    TIMESTAMP = "timestamp"  # 20241014_143000
    SEQUENTIAL = "sequential"  # 001, 002, 003
    HASH = "hash"  # git-style hash


class ConflictType(str, Enum):
    """Types of migration conflicts."""
    VERSION_COLLISION = "version_collision"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    SCHEMA_CONFLICT = "schema_conflict"
    DATA_CONFLICT = "data_conflict"


class MigrationState(str, Enum):
    """Migration state in version control."""
    DRAFT = "draft"
    STAGED = "staged"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationDependency:
    """Represents a migration dependency."""
    
    migration_id: str
    version: str
    required: bool = True
    reason: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.version} ({'required' if self.required else 'optional'})"


@dataclass
class MigrationConflict:
    """Represents a migration conflict."""
    
    conflict_id: UUID = field(default_factory=uuid4)
    type: ConflictType = ConflictType.VERSION_COLLISION
    source_migration: str = ""
    target_migration: str = ""
    description: str = ""
    resolution_strategy: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.description:
            self.description = f"{self.type.value} between {self.source_migration} and {self.target_migration}"


@dataclass
class MigrationVersion:
    """Comprehensive migration version information."""
    
    # Basic identification
    version: str
    migration_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    
    # Version metadata
    format: VersionFormat = VersionFormat.TIMESTAMP
    major: Optional[int] = None
    minor: Optional[int] = None
    patch: Optional[int] = None
    
    # Timing and authorship
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None
    
    # Dependencies and relationships
    dependencies: List[MigrationDependency] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)  # Migrations that depend on this one
    
    # State and metadata
    state: MigrationState = MigrationState.DRAFT
    file_path: Optional[str] = None
    checksum: Optional[str] = None
    
    # Conflict tracking
    conflicts: List[MigrationConflict] = field(default_factory=list)
    
    # Rollback information
    rollback_script: Optional[str] = None
    rollback_tested: bool = False
    
    # Tags and labels
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Parse version components based on format."""
        if self.format == VersionFormat.SEMANTIC:
            self._parse_semantic_version()
        elif self.format == VersionFormat.TIMESTAMP:
            self._parse_timestamp_version()
    
    def _parse_semantic_version(self) -> None:
        """Parse semantic version (e.g., 1.2.3)."""
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$'
        match = re.match(pattern, self.version)
        
        if match:
            self.major = int(match.group(1))
            self.minor = int(match.group(2))
            self.patch = int(match.group(3))
    
    def _parse_timestamp_version(self) -> None:
        """Parse timestamp version (e.g., 20241014_143000)."""
        pattern = r'^(\d{8})_(\d{6})$'
        match = re.match(pattern, self.version)
        
        if match:
            date_part = match.group(1)
            time_part = match.group(2)
            
            # Extract components for sorting
            self.major = int(date_part)
            self.minor = int(time_part[:4])  # HHMM
            self.patch = int(time_part[4:])   # SS
    
    def add_dependency(self, dependency: MigrationDependency) -> None:
        """Add a migration dependency."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)
    
    def add_conflict(self, conflict: MigrationConflict) -> None:
        """Add a migration conflict."""
        self.conflicts.append(conflict)
    
    def has_unresolved_conflicts(self) -> bool:
        """Check if there are unresolved conflicts."""
        return any(not conflict.resolved for conflict in self.conflicts)
    
    def is_compatible_with(self, other: 'MigrationVersion') -> bool:
        """Check if this migration is compatible with another."""
        # Check for direct conflicts
        if self.has_unresolved_conflicts():
            return False
        
        # Check version collision
        if self.version == other.version:
            return False
        
        # Check for dependency cycles
        if other.version in [dep.version for dep in self.dependencies]:
            if self.version in [dep.version for dep in other.dependencies]:
                return False  # Circular dependency
        
        return True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'version': self.version,
            'migration_id': str(self.migration_id),
            'name': self.name,
            'description': self.description,
            'format': self.format.value,
            'major': self.major,
            'minor': self.minor,
            'patch': self.patch,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'applied_by': self.applied_by,
            'dependencies': [
                {
                    'migration_id': dep.migration_id,
                    'version': dep.version,
                    'required': dep.required,
                    'reason': dep.reason
                }
                for dep in self.dependencies
            ],
            'dependents': self.dependents,
            'state': self.state.value,
            'file_path': self.file_path,
            'checksum': self.checksum,
            'conflicts': [
                {
                    'conflict_id': str(conflict.conflict_id),
                    'type': conflict.type.value,
                    'source_migration': conflict.source_migration,
                    'target_migration': conflict.target_migration,
                    'description': conflict.description,
                    'resolution_strategy': conflict.resolution_strategy,
                    'resolved': conflict.resolved,
                    'resolved_at': conflict.resolved_at.isoformat() if conflict.resolved_at else None
                }
                for conflict in self.conflicts
            ],
            'rollback_script': self.rollback_script,
            'rollback_tested': self.rollback_tested,
            'tags': self.tags,
            'labels': self.labels
        }


class VersionManager:
    """
    Manages migration versions with advanced conflict resolution
    and dependency tracking.
    """
    
    def __init__(self, repository_path: str = "migrations"):
        """
        Initialize version manager.
        
        Args:
            repository_path: Path to migration repository
        """
        self.repository_path = Path(repository_path)
        self.versions_file = self.repository_path / "versions.json"
        self.conflicts_file = self.repository_path / "conflicts.json"
        
        # In-memory state
        self.versions: Dict[str, MigrationVersion] = {}
        self.conflicts: List[MigrationConflict] = []
        
        # Ensure repository structure exists
        self._initialize_repository()
        
        # Load existing versions
        self._load_versions()
        self._load_conflicts()
    
    def _initialize_repository(self) -> None:
        """Initialize migration repository structure."""
        self.repository_path.mkdir(parents=True, exist_ok=True)
        
        # Create versions file if it doesn't exist
        if not self.versions_file.exists():
            self._save_versions()
        
        # Create conflicts file if it doesn't exist
        if not self.conflicts_file.exists():
            self._save_conflicts()
    
    def _load_versions(self) -> None:
        """Load versions from storage."""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r') as f:
                    data = json.load(f)
                
                for version_data in data.get('versions', []):
                    version = self._version_from_dict(version_data)
                    self.versions[version.version] = version
                    
            except Exception as e:
                logger.error(f"Failed to load versions: {e}")
    
    def _load_conflicts(self) -> None:
        """Load conflicts from storage."""
        if self.conflicts_file.exists():
            try:
                with open(self.conflicts_file, 'r') as f:
                    data = json.load(f)
                
                for conflict_data in data.get('conflicts', []):
                    conflict = self._conflict_from_dict(conflict_data)
                    self.conflicts.append(conflict)
                    
            except Exception as e:
                logger.error(f"Failed to load conflicts: {e}")
    
    def _save_versions(self) -> None:
        """Save versions to storage."""
        data = {
            'versions': [version.to_dict() for version in self.versions.values()],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        with open(self.versions_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_conflicts(self) -> None:
        """Save conflicts to storage."""
        data = {
            'conflicts': [
                {
                    'conflict_id': str(conflict.conflict_id),
                    'type': conflict.type.value,
                    'source_migration': conflict.source_migration,
                    'target_migration': conflict.target_migration,
                    'description': conflict.description,
                    'resolution_strategy': conflict.resolution_strategy,
                    'resolved': conflict.resolved,
                    'resolved_at': conflict.resolved_at.isoformat() if conflict.resolved_at else None
                }
                for conflict in self.conflicts
            ],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        with open(self.conflicts_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _version_from_dict(self, data: Dict) -> MigrationVersion:
        """Create MigrationVersion from dictionary."""
        version = MigrationVersion(
            version=data['version'],
            migration_id=UUID(data['migration_id']),
            name=data.get('name', ''),
            description=data.get('description', ''),
            format=VersionFormat(data.get('format', VersionFormat.TIMESTAMP.value)),
            major=data.get('major'),
            minor=data.get('minor'),
            patch=data.get('patch'),
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data.get('created_by', ''),
            applied_at=datetime.fromisoformat(data['applied_at']) if data.get('applied_at') else None,
            applied_by=data.get('applied_by'),
            dependents=data.get('dependents', []),
            state=MigrationState(data.get('state', MigrationState.DRAFT.value)),
            file_path=data.get('file_path'),
            checksum=data.get('checksum'),
            rollback_script=data.get('rollback_script'),
            rollback_tested=data.get('rollback_tested', False),
            tags=data.get('tags', []),
            labels=data.get('labels', {})
        )
        
        # Load dependencies
        for dep_data in data.get('dependencies', []):
            dependency = MigrationDependency(
                migration_id=dep_data['migration_id'],
                version=dep_data['version'],
                required=dep_data.get('required', True),
                reason=dep_data.get('reason')
            )
            version.dependencies.append(dependency)
        
        # Load conflicts
        for conflict_data in data.get('conflicts', []):
            conflict = self._conflict_from_dict(conflict_data)
            version.conflicts.append(conflict)
        
        return version
    
    def _conflict_from_dict(self, data: Dict) -> MigrationConflict:
        """Create MigrationConflict from dictionary."""
        return MigrationConflict(
            conflict_id=UUID(data['conflict_id']),
            type=ConflictType(data['type']),
            source_migration=data['source_migration'],
            target_migration=data['target_migration'],
            description=data['description'],
            resolution_strategy=data.get('resolution_strategy'),
            resolved=data.get('resolved', False),
            resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') else None
        )
    
    def generate_version(self, format: VersionFormat = VersionFormat.TIMESTAMP,
                        base_version: Optional[str] = None) -> str:
        """
        Generate a new version number.
        
        Args:
            format: Version format to use
            base_version: Base version for incremental formats
            
        Returns:
            New version string
        """
        if format == VersionFormat.TIMESTAMP:
            return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        elif format == VersionFormat.SEMANTIC:
            if base_version:
                # Parse and increment
                pattern = r'^(\d+)\.(\d+)\.(\d+)'
                match = re.match(pattern, base_version)
                if match:
                    major, minor, patch = map(int, match.groups())
                    return f"{major}.{minor}.{patch + 1}"
            
            # Default semantic version
            return "1.0.0"
        
        elif format == VersionFormat.SEQUENTIAL:
            # Find highest sequential number
            sequential_versions = [
                v for v in self.versions.keys() 
                if v.isdigit()
            ]
            
            if sequential_versions:
                next_num = max(int(v) for v in sequential_versions) + 1
                return f"{next_num:03d}"
            else:
                return "001"
        
        elif format == VersionFormat.HASH:
            # Generate a short hash
            return uuid4().hex[:8]
        
        else:
            raise ValueError(f"Unsupported version format: {format}")
    
    def create_version(self, version: str, name: str = "", 
                      description: str = "", 
                      dependencies: Optional[List[str]] = None) -> MigrationVersion:
        """
        Create a new migration version.
        
        Args:
            version: Version string
            name: Migration name
            description: Migration description
            dependencies: List of dependent version strings
            
        Returns:
            Created MigrationVersion
        """
        # Check for version collision
        if version in self.versions:
            raise ValueError(f"Version {version} already exists")
        
        # Create the version
        migration_version = MigrationVersion(
            version=version,
            name=name,
            description=description
        )
        
        # Add dependencies
        if dependencies:
            for dep_version in dependencies:
                if dep_version not in self.versions:
                    logger.warning(f"Dependency version {dep_version} not found")
                
                dependency = MigrationDependency(
                    migration_id=str(uuid4()),
                    version=dep_version,
                    required=True,
                    reason="Explicit dependency"
                )
                migration_version.add_dependency(dependency)
                
                # Update dependent's dependents list
                if dep_version in self.versions:
                    self.versions[dep_version].dependents.append(version)
        
        # Check for conflicts
        conflicts = self._detect_conflicts(migration_version)
        for conflict in conflicts:
            migration_version.add_conflict(conflict)
            self.conflicts.append(conflict)
        
        # Store the version
        self.versions[version] = migration_version
        
        # Persist changes
        self._save_versions()
        self._save_conflicts()
        
        logger.info(f"Created migration version: {version}")
        return migration_version
    
    def _detect_conflicts(self, new_version: MigrationVersion) -> List[MigrationConflict]:
        """Detect conflicts with existing versions."""
        conflicts = []
        
        for existing_version in self.versions.values():
            # Version collision (shouldn't happen due to earlier check)
            if existing_version.version == new_version.version:
                conflict = MigrationConflict(
                    type=ConflictType.VERSION_COLLISION,
                    source_migration=new_version.version,
                    target_migration=existing_version.version,
                    description=f"Version {new_version.version} already exists"
                )
                conflicts.append(conflict)
            
            # Dependency conflicts
            if self._has_dependency_conflict(new_version, existing_version):
                conflict = MigrationConflict(
                    type=ConflictType.DEPENDENCY_CONFLICT,
                    source_migration=new_version.version,
                    target_migration=existing_version.version,
                    description="Circular dependency detected"
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _has_dependency_conflict(self, version1: MigrationVersion, 
                               version2: MigrationVersion) -> bool:
        """Check if two versions have dependency conflicts."""
        # Check for circular dependencies
        v1_deps = {dep.version for dep in version1.dependencies}
        v2_deps = {dep.version for dep in version2.dependencies}
        
        # If version1 depends on version2 and version2 depends on version1
        if version2.version in v1_deps and version1.version in v2_deps:
            return True
        
        return False
    
    def resolve_conflict(self, conflict_id: UUID, 
                        strategy: str) -> bool:
        """
        Resolve a migration conflict.
        
        Args:
            conflict_id: Conflict to resolve
            strategy: Resolution strategy
            
        Returns:
            True if resolved successfully
        """
        # Find the conflict
        conflict = None
        for c in self.conflicts:
            if c.conflict_id == conflict_id:
                conflict = c
                break
        
        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found")
        
        if conflict.resolved:
            logger.info(f"Conflict {conflict_id} already resolved")
            return True
        
        try:
            # Apply resolution strategy
            if strategy == "rename_source":
                self._resolve_by_renaming(conflict, True)
            elif strategy == "rename_target":
                self._resolve_by_renaming(conflict, False)
            elif strategy == "merge":
                self._resolve_by_merging(conflict)
            elif strategy == "abort":
                self._resolve_by_aborting(conflict)
            else:
                raise ValueError(f"Unknown resolution strategy: {strategy}")
            
            # Mark as resolved
            conflict.resolved = True
            conflict.resolved_at = datetime.now(timezone.utc)
            conflict.resolution_strategy = strategy
            
            # Update version conflicts
            for version in self.versions.values():
                for v_conflict in version.conflicts:
                    if v_conflict.conflict_id == conflict_id:
                        v_conflict.resolved = True
                        v_conflict.resolved_at = conflict.resolved_at
                        v_conflict.resolution_strategy = strategy
            
            # Persist changes
            self._save_versions()
            self._save_conflicts()
            
            logger.info(f"Conflict {conflict_id} resolved using strategy: {strategy}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict_id}: {e}")
            return False
    
    def _resolve_by_renaming(self, conflict: MigrationConflict, 
                           rename_source: bool) -> None:
        """Resolve conflict by renaming one of the versions."""
        if conflict.type != ConflictType.VERSION_COLLISION:
            raise ValueError("Renaming only applies to version collisions")
        
        if rename_source:
            old_version = conflict.source_migration
            new_version = f"{old_version}_renamed_{int(time.time())}"
        else:
            old_version = conflict.target_migration
            new_version = f"{old_version}_renamed_{int(time.time())}"
        
        # Rename the version
        if old_version in self.versions:
            version_obj = self.versions.pop(old_version)
            version_obj.version = new_version
            self.versions[new_version] = version_obj
            
            # Update dependencies in other versions
            for other_version in self.versions.values():
                for dep in other_version.dependencies:
                    if dep.version == old_version:
                        dep.version = new_version
                
                if old_version in other_version.dependents:
                    other_version.dependents.remove(old_version)
                    other_version.dependents.append(new_version)
    
    def _resolve_by_merging(self, conflict: MigrationConflict) -> None:
        """Resolve conflict by merging migrations."""
        # This would require sophisticated merging logic
        # For now, just mark as resolved
        logger.info(f"Merging resolution for conflict {conflict.conflict_id} not implemented")
    
    def _resolve_by_aborting(self, conflict: MigrationConflict) -> None:
        """Resolve conflict by aborting one of the migrations."""
        # Remove the source migration
        if conflict.source_migration in self.versions:
            del self.versions[conflict.source_migration]
    
    def get_dependency_order(self) -> List[str]:
        """
        Get migrations in dependency order (topological sort).
        
        Returns:
            List of version strings in execution order
        """
        # Build dependency graph
        graph = {}
        in_degree = {}
        
        for version in self.versions.keys():
            graph[version] = []
            in_degree[version] = 0
        
        for version, migration in self.versions.items():
            for dep in migration.dependencies:
                if dep.version in graph:
                    graph[dep.version].append(version)
                    in_degree[version] += 1
        
        # Topological sort using Kahn's algorithm
        queue = [v for v in in_degree if in_degree[v] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(result) != len(self.versions):
            raise ValueError("Circular dependency detected in migrations")
        
        return result
    
    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Validate all migration dependencies.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Check for circular dependencies
            self.get_dependency_order()
        except ValueError as e:
            issues.append(str(e))
        
        # Check for missing dependencies
        for version, migration in self.versions.items():
            for dep in migration.dependencies:
                if dep.version not in self.versions:
                    issues.append(f"Missing dependency: {version} depends on {dep.version}")
        
        # Check for unresolved conflicts
        unresolved_conflicts = [c for c in self.conflicts if not c.resolved]
        if unresolved_conflicts:
            issues.append(f"{len(unresolved_conflicts)} unresolved conflicts")
        
        return len(issues) == 0, issues
    
    def get_migration_path(self, from_version: Optional[str], 
                          to_version: str) -> List[str]:
        """
        Get migration path from one version to another.
        
        Args:
            from_version: Starting version (None for fresh install)
            to_version: Target version
            
        Returns:
            List of versions to execute in order
        """
        if from_version and from_version not in self.versions:
            raise ValueError(f"From version {from_version} not found")
        
        if to_version not in self.versions:
            raise ValueError(f"To version {to_version} not found")
        
        # Get all versions in dependency order
        ordered_versions = self.get_dependency_order()
        
        # Find start and end indices
        start_idx = 0
        if from_version:
            try:
                start_idx = ordered_versions.index(from_version) + 1
            except ValueError:
                raise ValueError(f"From version {from_version} not in dependency order")
        
        try:
            end_idx = ordered_versions.index(to_version) + 1
        except ValueError:
            raise ValueError(f"To version {to_version} not in dependency order")
        
        # Return the path
        return ordered_versions[start_idx:end_idx]
    
    def get_rollback_path(self, from_version: str, 
                         to_version: str) -> List[str]:
        """
        Get rollback path from one version to another.
        
        Args:
            from_version: Current version
            to_version: Target version (earlier)
            
        Returns:
            List of versions to rollback in reverse order
        """
        forward_path = self.get_migration_path(to_version, from_version)
        return list(reversed(forward_path))
    
    def list_versions(self, state: Optional[MigrationState] = None) -> List[MigrationVersion]:
        """
        List migration versions with optional state filter.
        
        Args:
            state: Optional state filter
            
        Returns:
            List of migration versions
        """
        versions = list(self.versions.values())
        
        if state:
            versions = [v for v in versions if v.state == state]
        
        # Sort by creation time
        versions.sort(key=lambda v: v.created_at)
        
        return versions
    
    def get_version_info(self, version: str) -> Optional[MigrationVersion]:
        """Get detailed information about a specific version."""
        return self.versions.get(version)
    
    def mark_applied(self, version: str, applied_by: str = "system") -> None:
        """Mark a migration version as applied."""
        if version in self.versions:
            self.versions[version].state = MigrationState.APPLIED
            self.versions[version].applied_at = datetime.now(timezone.utc)
            self.versions[version].applied_by = applied_by
            self._save_versions()
    
    def mark_failed(self, version: str, error_message: str = "") -> None:
        """Mark a migration version as failed."""
        if version in self.versions:
            self.versions[version].state = MigrationState.FAILED
            self.versions[version].labels['error_message'] = error_message
            self._save_versions()
    
    def get_conflicts(self, resolved: Optional[bool] = None) -> List[MigrationConflict]:
        """Get migration conflicts with optional resolution filter."""
        conflicts = self.conflicts.copy()
        
        if resolved is not None:
            conflicts = [c for c in conflicts if c.resolved == resolved]
        
        return conflicts
