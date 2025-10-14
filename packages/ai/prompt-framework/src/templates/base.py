"""
Prompt Template Base Classes

Provides core abstractions for prompt template management, rendering, and versioning.
Supports Jinja2 templates with semantic versioning and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Protocol
import hashlib
import json

import jinja2
import jinja2.meta
from pydantic import BaseModel, Field, field_validator


class PromptMetadata(BaseModel):
    """Metadata for a prompt template version."""
    
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    author: str = Field(default="system", description="Author of this version")
    description: str = Field(default="", description="Change description")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    cost_tier: str = Field(default="medium", description="Expected token usage tier")
    
    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate semantic version format."""
        parts = v.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"Invalid semantic version: {v}. Expected format: X.Y.Z")
        return v
    
    @field_validator("cost_tier")
    @classmethod
    def validate_cost_tier(cls, v: str) -> str:
        """Validate cost tier is recognized."""
        valid_tiers = {"low", "medium", "high"}
        if v not in valid_tiers:
            raise ValueError(f"Invalid cost tier: {v}. Must be one of {valid_tiers}")
        return v


class PromptTemplate(BaseModel):
    """
    Immutable prompt template with versioning and metadata.
    
    Represents a single version of a prompt template. Multiple versions
    can exist for the same prompt name, enabling A/B testing and rollback.
    """
    
    name: str = Field(..., description="Unique template name (e.g., 'meal_plan_weekly')")
    metadata: PromptMetadata = Field(..., description="Version metadata")
    template_content: str = Field(..., description="Jinja2 template string")
    required_variables: set[str] = Field(default_factory=set, description="Required context variables")
    optional_variables: set[str] = Field(default_factory=set, description="Optional context variables")
    
    @property
    def version(self) -> str:
        """Convenience accessor for version."""
        return self.metadata.version
    
    @property
    def template_hash(self) -> str:
        """Generate deterministic hash of template content."""
        return hashlib.sha256(self.template_content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "name": self.name,
            "metadata": self.metadata.model_dump(),
            "template_content": self.template_content,
            "required_variables": list(self.required_variables),
            "optional_variables": list(self.optional_variables),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptTemplate":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            metadata=PromptMetadata(**data["metadata"]),
            template_content=data["template_content"],
            required_variables=set(data.get("required_variables", [])),
            optional_variables=set(data.get("optional_variables", [])),
        )


class TemplateCache(Protocol):
    """Protocol for template caching implementations."""
    
    def get(self, key: str) -> Optional[PromptTemplate]:
        """Retrieve cached template."""
        ...
    
    def set(self, key: str, template: PromptTemplate) -> None:
        """Store template in cache."""
        ...
    
    def invalidate(self, key: str) -> None:
        """Remove template from cache."""
        ...


@dataclass
class InMemoryTemplateCache:
    """Simple in-memory template cache with LRU eviction."""
    
    _cache: Dict[str, PromptTemplate] = field(default_factory=dict)
    _access_order: list[str] = field(default_factory=list)
    max_size: int = 100
    
    def get(self, key: str) -> Optional[PromptTemplate]:
        """Retrieve cached template and update access order."""
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None
    
    def set(self, key: str, template: PromptTemplate) -> None:
        """Store template and evict oldest if needed."""
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self.max_size:
            # Evict least recently used
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        
        self._cache[key] = template
        self._access_order.append(key)
    
    def invalidate(self, key: str) -> None:
        """Remove template from cache."""
        if key in self._cache:
            del self._cache[key]
            self._access_order.remove(key)
    
    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._access_order.clear()


class PromptRenderer:
    """
    Thread-safe prompt renderer with template caching.
    
    Loads Jinja2 templates from filesystem, renders with context validation,
    and caches compiled templates for performance.
    """
    
    def __init__(
        self,
        template_dir: str | Path,
        cache: Optional[TemplateCache] = None,
        strict_mode: bool = True
    ):
        """
        Initialize renderer.
        
        Args:
            template_dir: Directory containing .j2 template files
            cache: Optional custom cache implementation (defaults to in-memory)
            strict_mode: If True, raises error on missing required variables
        """
        self.template_dir = Path(template_dir)
        self.cache = cache or InMemoryTemplateCache()
        self.strict_mode = strict_mode
        
        # Configure Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=False,  # Prompts are not HTML
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=jinja2.StrictUndefined if strict_mode else jinja2.Undefined,
        )
    
    def load_template(self, name: str, version: str) -> PromptTemplate:
        """
        Load template from filesystem or cache.
        
        Args:
            name: Template name (e.g., 'meal_plan_weekly')
            version: Semantic version (e.g., '1.0.0')
        
        Returns:
            PromptTemplate instance
        
        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template metadata is invalid
        """
        cache_key = f"{name}@{version}"
        
        # Check cache first
        if cached := self.cache.get(cache_key):
            return cached
        
        # Load from filesystem
        template_path = self.template_dir / f"{name}_{version.replace('.', '_')}.j2"
        metadata_path = self.template_dir / f"{name}_{version.replace('.', '_')}.json"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        template_content = template_path.read_text(encoding="utf-8")
        
        # Load metadata if exists, otherwise create default
        if metadata_path.exists():
            metadata_data = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata = PromptMetadata(**metadata_data)
        else:
            metadata = PromptMetadata(version=version, description=f"Template {name}")
        
        # Extract required/optional variables from Jinja2 template
        ast = self.jinja_env.parse(template_content)
        required_vars = jinja2.meta.find_undeclared_variables(ast)
        
        template = PromptTemplate(
            name=name,
            metadata=metadata,
            template_content=template_content,
            required_variables=required_vars,
            optional_variables=set(),  # Could be specified in metadata
        )
        
        # Cache for future use
        self.cache.set(cache_key, template)
        return template
    
    async def render(
        self,
        name: str,
        version: str,
        context: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """
        Render template with provided context.
        
        Args:
            name: Template name
            version: Semantic version
            context: Variables to inject into template
            validate: If True, validates required variables are present
        
        Returns:
            Rendered prompt string
        
        Raises:
            ValueError: If required variables missing (when validate=True)
            jinja2.TemplateError: If rendering fails
        """
        template = self.load_template(name, version)
        
        # Validate context if requested
        if validate and self.strict_mode:
            missing = template.required_variables - set(context.keys())
            if missing:
                raise ValueError(
                    f"Missing required variables for {name}@{version}: {missing}"
                )
        
        # Render using Jinja2
        jinja_template = self.jinja_env.from_string(template.template_content)
        rendered = jinja_template.render(**context)
        
        return rendered.strip()
    
    def list_versions(self, name: str) -> list[str]:
        """
        List all available versions for a template.
        
        Args:
            name: Template name
        
        Returns:
            List of version strings, sorted by semantic version
        """
        pattern = f"{name}_*.j2"
        versions = []
        
        for path in self.template_dir.glob(pattern):
            # Extract version from filename (e.g., meal_plan_weekly_1_0_0.j2 -> 1.0.0)
            version_part = path.stem.replace(f"{name}_", "")
            version = version_part.replace("_", ".")
            versions.append(version)
        
        # Sort by semantic version
        versions.sort(key=lambda v: tuple(map(int, v.split("."))))
        return versions
    
    def get_latest_version(self, name: str) -> str:
        """
        Get the latest semantic version for a template.
        
        Args:
            name: Template name
        
        Returns:
            Latest version string
        
        Raises:
            ValueError: If no versions exist
        """
        versions = self.list_versions(name)
        if not versions:
            raise ValueError(f"No versions found for template: {name}")
        return versions[-1]
