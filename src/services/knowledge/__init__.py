# src/services/knowledge/__init__.py

"""
Knowledge base services for RAG (Retrieval-Augmented Generation).
"""

from .food_rag import FoodKnowledgeRAG
from .ingestion_pipeline import RecipeIngestionPipeline
from .sample_data import SAMPLE_RECIPES

__all__ = [
    "FoodKnowledgeRAG",
    "RecipeIngestionPipeline",
    "SAMPLE_RECIPES",
]
