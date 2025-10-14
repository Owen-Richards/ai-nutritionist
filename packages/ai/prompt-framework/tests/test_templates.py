"""
Unit tests for Prompt Template system
"""

import pytest
from pathlib import Path
import json

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.templates.base import (
    PromptTemplate,
    PromptMetadata,
    PromptRenderer,
    InMemoryTemplateCache,
)


class TestPromptMetadata:
    """Tests for PromptMetadata model."""
    
    def test_valid_metadata(self):
        """Test creating valid metadata."""
        metadata = PromptMetadata(
            version="1.0.0",
            author="test-author",
            description="Test template",
            tags=["test", "sample"],
            cost_tier="low"
        )
        assert metadata.version == "1.0.0"
        assert metadata.author == "test-author"
        assert metadata.cost_tier == "low"
    
    def test_invalid_semver(self):
        """Test validation of semantic version."""
        with pytest.raises(ValueError, match="Invalid semantic version"):
            PromptMetadata(version="1.0")  # Missing patch version
        
        with pytest.raises(ValueError, match="Invalid semantic version"):
            PromptMetadata(version="v1.0.0")  # Invalid prefix
    
    def test_invalid_cost_tier(self):
        """Test validation of cost tier."""
        with pytest.raises(ValueError, match="Invalid cost tier"):
            PromptMetadata(version="1.0.0", cost_tier="extreme")


class TestPromptTemplate:
    """Tests for PromptTemplate model."""
    
    def test_template_creation(self):
        """Test creating a prompt template."""
        metadata = PromptMetadata(version="1.0.0")
        template = PromptTemplate(
            name="test_template",
            metadata=metadata,
            template_content="Hello {{ name }}!",
            required_variables={"name"},
        )
        
        assert template.name == "test_template"
        assert template.version == "1.0.0"
        assert "name" in template.required_variables
    
    def test_template_hash(self):
        """Test template content hashing."""
        metadata = PromptMetadata(version="1.0.0")
        template1 = PromptTemplate(
            name="test",
            metadata=metadata,
            template_content="Content A",
        )
        template2 = PromptTemplate(
            name="test",
            metadata=metadata,
            template_content="Content B",
        )
        
        assert template1.template_hash != template2.template_hash
    
    def test_serialization(self):
        """Test template serialization and deserialization."""
        metadata = PromptMetadata(version="1.0.0", author="test")
        original = PromptTemplate(
            name="test",
            metadata=metadata,
            template_content="Hello {{ name }}",
            required_variables={"name"},
        )
        
        # Serialize
        data = original.to_dict()
        assert data["name"] == "test"
        assert data["metadata"]["version"] == "1.0.0"
        
        # Deserialize
        restored = PromptTemplate.from_dict(data)
        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.template_content == original.template_content


class TestInMemoryTemplateCache:
    """Tests for template caching."""
    
    def test_cache_operations(self):
        """Test basic cache get/set/invalidate."""
        cache = InMemoryTemplateCache(max_size=2)
        metadata = PromptMetadata(version="1.0.0")
        
        template1 = PromptTemplate(
            name="t1", metadata=metadata, template_content="T1"
        )
        template2 = PromptTemplate(
            name="t2", metadata=metadata, template_content="T2"
        )
        
        # Initially empty
        assert cache.get("t1") is None
        
        # Add templates
        cache.set("t1", template1)
        cache.set("t2", template2)
        
        # Retrieve
        assert cache.get("t1") == template1
        assert cache.get("t2") == template2
        
        # Invalidate
        cache.invalidate("t1")
        assert cache.get("t1") is None
    
    def test_lru_eviction(self):
        """Test LRU cache eviction."""
        cache = InMemoryTemplateCache(max_size=2)
        metadata = PromptMetadata(version="1.0.0")
        
        t1 = PromptTemplate(name="t1", metadata=metadata, template_content="T1")
        t2 = PromptTemplate(name="t2", metadata=metadata, template_content="T2")
        t3 = PromptTemplate(name="t3", metadata=metadata, template_content="T3")
        
        cache.set("t1", t1)
        cache.set("t2", t2)
        
        # Access t1 to make it recently used
        cache.get("t1")
        
        # Add t3, should evict t2 (least recently used)
        cache.set("t3", t3)
        
        assert cache.get("t1") is not None  # Still cached
        assert cache.get("t2") is None      # Evicted
        assert cache.get("t3") is not None  # Newly added


@pytest.fixture
def temp_template_dir(tmp_path):
    """Create temporary directory with test templates."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    
    # Create a test template file
    template_content = "Hello {{ name }}, your goal is {{ goal }}."
    template_file = template_dir / "greeting_1_0_0.j2"
    template_file.write_text(template_content)
    
    # Create metadata file
    metadata = {
        "version": "1.0.0",
        "author": "test",
        "description": "Test greeting",
        "tags": ["greeting"],
        "cost_tier": "low"
    }
    metadata_file = template_dir / "greeting_1_0_0.json"
    metadata_file.write_text(json.dumps(metadata))
    
    # Create another version
    template_v2 = "Hi {{ name }}! Goal: {{ goal }}"
    template_file_v2 = template_dir / "greeting_2_0_0.j2"
    template_file_v2.write_text(template_v2)
    
    return template_dir


class TestPromptRenderer:
    """Tests for PromptRenderer."""
    
    def test_load_template(self, temp_template_dir):
        """Test loading template from filesystem."""
        renderer = PromptRenderer(temp_template_dir)
        
        template = renderer.load_template("greeting", "1.0.0")
        
        assert template.name == "greeting"
        assert template.version == "1.0.0"
        assert "name" in template.required_variables
        assert "goal" in template.required_variables
    
    def test_load_nonexistent_template(self, temp_template_dir):
        """Test loading non-existent template raises error."""
        renderer = PromptRenderer(temp_template_dir)
        
        with pytest.raises(FileNotFoundError):
            renderer.load_template("nonexistent", "1.0.0")
    
    @pytest.mark.asyncio
    async def test_render_template(self, temp_template_dir):
        """Test rendering template with context."""
        renderer = PromptRenderer(temp_template_dir)
        
        result = await renderer.render(
            "greeting",
            "1.0.0",
            {"name": "Alice", "goal": "lose weight"}
        )
        
        assert "Alice" in result
        assert "lose weight" in result
    
    @pytest.mark.asyncio
    async def test_render_missing_variable(self, temp_template_dir):
        """Test rendering with missing required variable."""
        renderer = PromptRenderer(temp_template_dir, strict_mode=True)
        
        with pytest.raises(ValueError, match="Missing required variables"):
            await renderer.render(
                "greeting",
                "1.0.0",
                {"name": "Alice"}  # Missing 'goal'
            )
    
    @pytest.mark.asyncio
    async def test_render_non_strict_mode(self, temp_template_dir):
        """Test rendering in non-strict mode allows missing variables."""
        renderer = PromptRenderer(temp_template_dir, strict_mode=False)
        
        # Should not raise, but will have undefined values
        result = await renderer.render(
            "greeting",
            "1.0.0",
            {"name": "Alice"},
            validate=False
        )
        
        assert "Alice" in result
    
    def test_list_versions(self, temp_template_dir):
        """Test listing all versions of a template."""
        renderer = PromptRenderer(temp_template_dir)
        
        versions = renderer.list_versions("greeting")
        
        assert versions == ["1.0.0", "2.0.0"]
    
    def test_get_latest_version(self, temp_template_dir):
        """Test getting latest version."""
        renderer = PromptRenderer(temp_template_dir)
        
        latest = renderer.get_latest_version("greeting")
        
        assert latest == "2.0.0"
    
    def test_template_caching(self, temp_template_dir):
        """Test that templates are cached after first load."""
        cache = InMemoryTemplateCache()
        renderer = PromptRenderer(temp_template_dir, cache=cache)
        
        # First load - from filesystem
        template1 = renderer.load_template("greeting", "1.0.0")
        
        # Second load - from cache
        template2 = renderer.load_template("greeting", "1.0.0")
        
        # Should be the same object (cached)
        assert template1 is template2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
