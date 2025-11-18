"""
Vector Database Module for PropIntel

This module provides components for data ingestion into the vector database:
- Document chunking for semantic search
- Embedding generation using OpenAI and fallback models
- ChromaDB management for vector storage and retrieval
- Data ingestion orchestration
"""

from .document_chunker import DocumentChunker
from .embedding_generator import EmbeddingGenerator
from .chromadb_manager import ChromaDBManager
from .ingestion_orchestrator import IngestionOrchestrator

__all__ = [
    'DocumentChunker',
    'EmbeddingGenerator',
    'ChromaDBManager',
    'IngestionOrchestrator'
]
