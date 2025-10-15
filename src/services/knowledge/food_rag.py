# src/services/knowledge/food_rag.py

"""
RAG (Retrieval-Augmented Generation) service for food knowledge base.
Handles semantic search for recipes and nutritional information.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RecipeSearchResult:
    """Result from recipe search."""

    recipe_id: str
    name: str
    description: str
    cuisine: str
    relevance_score: float
    calories: int
    protein_g: float
    total_time_min: int
    difficulty: str
    metadata: Dict[str, Any]


class FoodKnowledgeRAG:
    """
    RAG system for semantic food and recipe search.

    Example usage:
        rag = FoodKnowledgeRAG()

        results = await rag.search_recipes(
            query="high protein vegetarian meals",
            filters={"max_calories": 500, "allergens_exclude": ["nuts"]},
            top_k=5
        )

        for recipe in results:
            print(f"{recipe.name} - {recipe.relevance_score:.2f}")
    """

    def __init__(
        self,
        index_name: str = "nutrition-recipes",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        use_mock: bool = True,
    ):
        """
        Initialize RAG service.

        Args:
            index_name: Name of Pinecone index
            embedding_model: HuggingFace model for query embeddings
            use_mock: If True, use mock implementation
        """
        self.use_mock = use_mock
        self.embedding_model_name = embedding_model

        if use_mock:
            logger.info("Using mock RAG implementation")
            from .ingestion_pipeline import MockEmbeddingEncoder, MockPineconeIndex

            self.index = MockPineconeIndex()
            self.encoder = MockEmbeddingEncoder()
        else:
            # Real implementation
            try:
                import pinecone
                from sentence_transformers import SentenceTransformer

                self.encoder = SentenceTransformer(embedding_model)
                self.index = pinecone.Index(index_name)
                logger.info(f"Connected to Pinecone index: {index_name}")
            except ImportError as e:
                logger.error(f"Missing dependencies: {e}")
                raise

    async def search_recipes(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        min_score: float = 0.7,
    ) -> List[RecipeSearchResult]:
        """
        Semantic search for recipes.

        Args:
            query: Natural language search query
                   e.g., "quick vegan dinner under 30 minutes"
            filters: Metadata filters
                - max_calories: Maximum calories
                - min_protein_g: Minimum protein
                - allergens_exclude: List of allergens to exclude
                - cuisine: List of cuisines to include
                - dietary_labels: Required dietary labels
                - max_time_min: Maximum total time
                - cost_tier: List of cost tiers (budget, moderate, premium)
            top_k: Number of results to return
            min_score: Minimum similarity score threshold (0-1)

        Returns:
            List of matching recipes sorted by relevance
        """
        # Generate query embedding
        query_embedding = self._encode_query(query)

        # Build filter for vector database
        db_filter = self._build_filter(filters or {})

        # Search vector database
        if self.use_mock:
            # Mock search (return empty for now)
            results = []
            logger.info(f"Mock search for: '{query}' with filters: {filters}")
        else:
            # Real search
            results = self.index.query(
                vector=query_embedding, filter=db_filter, top_k=top_k, include_metadata=True
            )

        # Filter by score and convert to results
        recipes = []
        for match in results:
            if match.score >= min_score:
                recipe = RecipeSearchResult(
                    recipe_id=match.id,
                    name=match.metadata["name"],
                    description=match.metadata.get("description", ""),
                    cuisine=match.metadata["cuisine"],
                    relevance_score=match.score,
                    calories=match.metadata["calories"],
                    protein_g=match.metadata["protein_g"],
                    total_time_min=match.metadata["total_time_min"],
                    difficulty=match.metadata["difficulty"],
                    metadata=match.metadata,
                )
                recipes.append(recipe)

        logger.info(f"Found {len(recipes)} recipes matching query")
        return recipes

    def _encode_query(self, query: str) -> List[float]:
        """Encode query text to embedding vector."""
        if self.use_mock:
            embedding = self.encoder.encode([query])[0]
        else:
            embedding = self.encoder.encode(query).tolist()

        return embedding

    def _build_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Pinecone metadata filter from user filters.

        Pinecone filter syntax:
        {
            "field": {"$operator": value},
            "$and": [condition1, condition2],
            "$or": [condition1, condition2]
        }
        """
        pinecone_filter = {}

        # Calorie range
        if "max_calories" in filters:
            pinecone_filter["calories"] = {"$lte": filters["max_calories"]}
        if "min_calories" in filters:
            pinecone_filter.setdefault("calories", {})["$gte"] = filters["min_calories"]

        # Protein range
        if "min_protein_g" in filters:
            pinecone_filter["protein_g"] = {"$gte": filters["min_protein_g"]}
        if "max_protein_g" in filters:
            pinecone_filter.setdefault("protein_g", {})["$lte"] = filters["max_protein_g"]

        # Exclude allergens (must NOT contain any)
        if "allergens_exclude" in filters:
            pinecone_filter["allergens"] = {"$nin": filters["allergens_exclude"]}

        # Cuisine filter (must be in list)
        if "cuisine" in filters:
            cuisines = (
                filters["cuisine"] if isinstance(filters["cuisine"], list) else [filters["cuisine"]]
            )
            pinecone_filter["cuisine"] = {"$in": cuisines}

        # Dietary labels (must have ALL specified labels)
        if "dietary_labels" in filters:
            for label in filters["dietary_labels"]:
                pinecone_filter[f"dietary_labels"] = {"$in": [label]}

        # Time constraint
        if "max_time_min" in filters:
            pinecone_filter["total_time_min"] = {"$lte": filters["max_time_min"]}

        # Cost tier
        if "cost_tier" in filters:
            cost_tiers = (
                filters["cost_tier"]
                if isinstance(filters["cost_tier"], list)
                else [filters["cost_tier"]]
            )
            pinecone_filter["cost_tier"] = {"$in": cost_tiers}

        # Difficulty
        if "difficulty" in filters:
            difficulties = (
                filters["difficulty"]
                if isinstance(filters["difficulty"], list)
                else [filters["difficulty"]]
            )
            pinecone_filter["difficulty"] = {"$in": difficulties}

        # Minimum rating
        if "min_rating" in filters:
            pinecone_filter["rating"] = {"$gte": filters["min_rating"]}

        return pinecone_filter

    async def get_recipe_by_id(self, recipe_id: str) -> Optional[RecipeSearchResult]:
        """
        Fetch a specific recipe by ID.

        Args:
            recipe_id: Recipe identifier

        Returns:
            Recipe details or None if not found
        """
        if self.use_mock:
            logger.info(f"Mock fetch recipe: {recipe_id}")
            return None
        else:
            # Real fetch
            result = self.index.fetch(ids=[recipe_id])

            if recipe_id in result.vectors:
                vector_data = result.vectors[recipe_id]
                return RecipeSearchResult(
                    recipe_id=recipe_id,
                    name=vector_data.metadata["name"],
                    description=vector_data.metadata.get("description", ""),
                    cuisine=vector_data.metadata["cuisine"],
                    relevance_score=1.0,  # Direct fetch
                    calories=vector_data.metadata["calories"],
                    protein_g=vector_data.metadata["protein_g"],
                    total_time_min=vector_data.metadata["total_time_min"],
                    difficulty=vector_data.metadata["difficulty"],
                    metadata=vector_data.metadata,
                )

            return None

    async def search_similar_recipes(
        self, recipe_id: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None
    ) -> List[RecipeSearchResult]:
        """
        Find recipes similar to a given recipe.

        Args:
            recipe_id: Reference recipe ID
            top_k: Number of similar recipes to return
            filters: Optional metadata filters

        Returns:
            List of similar recipes
        """
        # Fetch the reference recipe's embedding
        if self.use_mock:
            logger.info(f"Mock similar search for recipe: {recipe_id}")
            return []
        else:
            result = self.index.fetch(ids=[recipe_id])

            if recipe_id not in result.vectors:
                logger.warning(f"Recipe not found: {recipe_id}")
                return []

            # Use the recipe's embedding to find similar ones
            embedding = result.vectors[recipe_id].values

            db_filter = self._build_filter(filters or {})

            results = self.index.query(
                vector=embedding,
                filter=db_filter,
                top_k=top_k + 1,  # +1 to exclude the original recipe
                include_metadata=True,
            )

            # Convert to results, excluding the original recipe
            recipes = []
            for match in results.matches:
                if match.id != recipe_id:  # Skip original
                    recipe = RecipeSearchResult(
                        recipe_id=match.id,
                        name=match.metadata["name"],
                        description=match.metadata.get("description", ""),
                        cuisine=match.metadata["cuisine"],
                        relevance_score=match.score,
                        calories=match.metadata["calories"],
                        protein_g=match.metadata["protein_g"],
                        total_time_min=match.metadata["total_time_min"],
                        difficulty=match.metadata["difficulty"],
                        metadata=match.metadata,
                    )
                    recipes.append(recipe)

            return recipes[:top_k]
