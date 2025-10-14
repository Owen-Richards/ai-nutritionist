# src/services/knowledge/ingestion_pipeline.py

"""
Recipe ingestion pipeline for RAG system.
Handles embedding generation and vector database upsert.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Note: In production, install these packages:
# pip install sentence-transformers pinecone-client

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Statistics from recipe ingestion."""

    total: int
    successful: int
    failed: int
    success_rate: float
    duration_seconds: float
    errors: List[str]


class RecipeIngestionPipeline:
    """
    Pipeline for ingesting recipes into vector database.

    Example usage:
        pipeline = RecipeIngestionPipeline(
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            batch_size=100
        )

        stats = await pipeline.ingest_recipes(recipes)
        print(f"Ingested {stats.successful}/{stats.total} recipes")
    """

    def __init__(
        self,
        pinecone_index_name: str = "nutrition-recipes",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        batch_size: int = 100,
        use_mock: bool = True,  # For prototyping without real Pinecone
    ):
        """
        Initialize ingestion pipeline.

        Args:
            pinecone_index_name: Name of Pinecone index
            embedding_model: HuggingFace model name for embeddings
            batch_size: Number of recipes per batch
            use_mock: If True, use mock implementations (for testing)
        """
        self.batch_size = batch_size
        self.use_mock = use_mock
        self.embedding_model_name = embedding_model

        if use_mock:
            logger.info("Using mock implementations for prototyping")
            self.index = MockPineconeIndex()
            self.encoder = MockEmbeddingEncoder()
        else:
            # Real implementations (requires packages installed)
            try:
                import pinecone
                from sentence_transformers import SentenceTransformer

                self.encoder = SentenceTransformer(embedding_model)
                self.index = pinecone.Index(pinecone_index_name)
                logger.info(f"Connected to Pinecone index: {pinecone_index_name}")
            except ImportError as e:
                logger.error(f"Missing dependencies: {e}")
                raise

    async def ingest_recipes(
        self, recipes: List[Dict[str, Any]], skip_existing: bool = True
    ) -> IngestionStats:
        """
        Ingest batch of recipes into vector database.

        Args:
            recipes: List of recipe dictionaries
            skip_existing: If True, skip recipes already in database

        Returns:
            Ingestion statistics
        """
        import time

        start_time = time.time()

        total_recipes = len(recipes)
        successful = 0
        failed = 0
        errors = []

        logger.info(f"Starting ingestion of {total_recipes} recipes")

        # Process in batches
        for i in range(0, total_recipes, self.batch_size):
            batch = recipes[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1

            try:
                logger.info(f"Processing batch {batch_num} ({len(batch)} recipes)")

                # 1. Generate embeddings
                vectors = await self._generate_embeddings(batch)

                # 2. Prepare for upsert
                upsert_data = self._prepare_upsert_data(batch, vectors)

                # 3. Upsert to Pinecone
                await self._upsert_to_index(upsert_data)

                successful += len(batch)
                logger.info(f"✓ Batch {batch_num} completed successfully")

            except Exception as e:
                error_msg = f"Error ingesting batch {batch_num}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed += len(batch)

        duration = time.time() - start_time
        success_rate = (successful / total_recipes * 100) if total_recipes > 0 else 0

        stats = IngestionStats(
            total=total_recipes,
            successful=successful,
            failed=failed,
            success_rate=success_rate,
            duration_seconds=duration,
            errors=errors,
        )

        logger.info(
            f"Ingestion complete: {successful}/{total_recipes} successful "
            f"({success_rate:.1f}%) in {duration:.2f}s"
        )

        return stats

    async def _generate_embeddings(self, recipes: List[Dict[str, Any]]) -> List[List[float]]:
        """Generate embeddings for recipe batch."""
        texts = [self._create_searchable_text(recipe) for recipe in recipes]

        if self.use_mock:
            # Mock embeddings for prototyping
            embeddings = self.encoder.encode(texts)
        else:
            # Real embeddings
            embeddings = self.encoder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            embeddings = embeddings.tolist()

        logger.debug(f"Generated {len(embeddings)} embeddings")
        return embeddings

    def _create_searchable_text(self, recipe: Dict[str, Any]) -> str:
        """
        Create searchable text from recipe data.

        This combines multiple fields to create a rich semantic representation.
        """
        components = [
            # Primary fields (highest weight)
            recipe["name"],
            recipe.get("description", ""),
            # Cuisine and meal type
            f"Cuisine: {recipe.get('cuisine', 'unknown')}",
            f"Meal type: {', '.join(recipe.get('meal_type', []))}",
            # Ingredients (important for semantic search)
            f"Ingredients: {', '.join([ing['name'] for ing in recipe.get('ingredients', [])])}",
            # Dietary information
            f"Dietary: {', '.join(recipe.get('dietary_labels', []))}",
            # Characteristics
            f"Difficulty: {recipe.get('difficulty', 'medium')}",
            f"Time: {recipe.get('total_time_min', 0)} minutes",
            # Nutritional highlights
            f"{recipe.get('calories', 0)} calories",
            f"{recipe.get('protein_g', 0)}g protein",
        ]

        # Filter out empty strings and join
        searchable_text = " ".join(filter(None, components))

        return searchable_text

    def _prepare_upsert_data(
        self, recipes: List[Dict[str, Any]], vectors: List[List[float]]
    ) -> List[Dict[str, Any]]:
        """
        Prepare data for Pinecone upsert.

        Pinecone format:
        {
            "id": "recipe_001",
            "values": [0.1, 0.2, ...],  # embedding vector
            "metadata": {...}  # filterable fields
        }
        """
        upsert_data = []

        for recipe, vector in zip(recipes, vectors):
            # Prepare metadata (only filterable fields)
            metadata = {
                "name": recipe["name"],
                "description": recipe.get("description", "")[:500],  # Truncate
                "cuisine": recipe.get("cuisine", "unknown"),
                "meal_type": recipe.get("meal_type", []),
                "dietary_labels": recipe.get("dietary_labels", []),
                "allergens": recipe.get("allergens", []),
                "calories": int(recipe.get("calories", 0)),
                "protein_g": float(recipe.get("protein_g", 0)),
                "total_time_min": int(recipe.get("total_time_min", 0)),
                "difficulty": recipe.get("difficulty", "medium"),
                "cost_tier": recipe.get("cost_tier", "moderate"),
                "rating": float(recipe.get("rating", 0)),
                "popularity_score": float(recipe.get("popularity_score", 0)),
                "source_name": recipe.get("source_name", ""),
                "verified": recipe.get("verified", False),
            }

            upsert_data.append({"id": recipe["recipe_id"], "values": vector, "metadata": metadata})

        return upsert_data

    async def _upsert_to_index(self, upsert_data: List[Dict[str, Any]]) -> None:
        """Upsert vectors to Pinecone index."""
        if self.use_mock:
            # Mock upsert
            await self.index.upsert(vectors=upsert_data)
        else:
            # Real upsert (synchronous in pinecone-client)
            self.index.upsert(vectors=upsert_data)

        logger.debug(f"Upserted {len(upsert_data)} vectors to index")

    async def delete_all_recipes(self) -> None:
        """Delete all recipes from index (for testing)."""
        if self.use_mock:
            await self.index.delete_all()
        else:
            self.index.delete(delete_all=True)

        logger.info("Deleted all recipes from index")


# ==================== Mock Implementations ====================


class MockEmbeddingEncoder:
    """Mock embedding encoder for prototyping."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings (random but deterministic)."""
        import hashlib

        embeddings = []
        for text in texts:
            # Use hash for deterministic "randomness"
            hash_obj = hashlib.md5(text.encode())
            seed = int(hash_obj.hexdigest(), 16) % (2**31)

            import random

            random.seed(seed)

            # Generate normalized vector
            vector = [random.gauss(0, 1) for _ in range(self.dimension)]

            # Normalize
            magnitude = sum(x**2 for x in vector) ** 0.5
            vector = [x / magnitude for x in vector]

            embeddings.append(vector)

        return embeddings


class MockPineconeIndex:
    """Mock Pinecone index for prototyping."""

    def __init__(self):
        self.vectors: Dict[str, Dict[str, Any]] = {}

    async def upsert(self, vectors: List[Dict[str, Any]]) -> None:
        """Mock upsert operation."""
        for item in vectors:
            self.vectors[item["id"]] = item

        logger.debug(f"Mock upsert: {len(vectors)} vectors (total: {len(self.vectors)})")

    async def delete_all(self) -> None:
        """Mock delete all operation."""
        self.vectors.clear()
        logger.debug("Mock delete all: cleared all vectors")

    def get_stats(self) -> Dict[str, Any]:
        """Get mock index statistics."""
        return {
            "total_vectors": len(self.vectors),
            "dimension": 384,
            "index_fullness": len(self.vectors) / 10000,  # Mock capacity
        }
