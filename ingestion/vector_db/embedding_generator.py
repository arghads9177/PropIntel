"""
Embedding Generator for PropIntel

This module provides embedding generation capabilities using OpenAI and fallback models.
Converts text chunks into vector embeddings for semantic search.
"""

import logging
from typing import List, Dict, Any, Optional
import os
from pathlib import Path

# Import embedding models
try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI embeddings not available")

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    logging.warning("HuggingFace embeddings not available")

from ..config.env_loader import get_config


class EmbeddingGenerator:
    """
    Generate vector embeddings for text chunks.
    
    Supports multiple embedding models with fallback:
    1. OpenAI (text-embedding-3-small) - Primary
    2. HuggingFace (sentence-transformers) - Fallback
    """
    
    def __init__(self, model_name: str = "openai", embedding_model: Optional[str] = None):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the model provider ('openai', 'huggingface')
            embedding_model: Specific model name (e.g., 'text-embedding-3-small')
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.config = get_config()
        
        # Initialize embedding model
        self.embeddings = self._initialize_embeddings(model_name, embedding_model)
        
        # Track statistics
        self.stats = {
            'total_embeddings': 0,
            'total_tokens': 0,
            'errors': 0
        }
        
        self.logger.info(f"EmbeddingGenerator initialized with model: {model_name}")
    
    def _initialize_embeddings(self, model_name: str, embedding_model: Optional[str]):
        """Initialize the embedding model"""
        
        if model_name == "openai":
            if not OPENAI_AVAILABLE:
                self.logger.warning("OpenAI not available, falling back to HuggingFace")
                return self._initialize_embeddings("huggingface", None)
            
            api_key = self.config.get("OPENAI_API_KEY")
            if not api_key:
                self.logger.error("OPENAI_API_KEY not found in environment")
                return self._initialize_embeddings("huggingface", None)
            
            try:
                model = embedding_model or "text-embedding-3-small"
                embeddings = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=api_key
                )
                self.logger.info(f"Initialized OpenAI embeddings with model: {model}")
                return embeddings
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI embeddings: {e}")
                return self._initialize_embeddings("huggingface", None)
        
        elif model_name == "huggingface":
            if not HUGGINGFACE_AVAILABLE:
                raise RuntimeError("No embedding models available")
            
            try:
                model = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
                embeddings = HuggingFaceEmbeddings(
                    model_name=model,
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                self.logger.info(f"Initialized HuggingFace embeddings with model: {model}")
                return embeddings
            except Exception as e:
                self.logger.error(f"Failed to initialize HuggingFace embeddings: {e}")
                raise
        
        else:
            raise ValueError(f"Unsupported model_name: {model_name}")
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        self.logger.info(f"Generating embeddings for {len(texts)} texts")
        
        try:
            # Process in batches for efficiency
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                
                # Generate embeddings for batch
                batch_embeddings = self.embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)
                
                self.stats['total_embeddings'] += len(batch)
                self.logger.debug(f"Processed batch {i//batch_size + 1}: {len(batch)} texts")
            
            self.logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            self.stats['errors'] += 1
            raise
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector
        """
        try:
            embedding = self.embeddings.embed_query(text)
            self.stats['total_embeddings'] += 1
            return embedding
        except Exception as e:
            self.logger.error(f"Error generating single embedding: {e}")
            self.stats['errors'] += 1
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        
        try:
            # Generate a test embedding to get dimension
            test_embedding = self.embeddings.embed_query("test")
            return len(test_embedding)
        except Exception as e:
            self.logger.error(f"Error getting embedding dimension: {e}")
            # Default dimensions for common models
            if "text-embedding-3-small" in str(self.embeddings):
                return 1536
            elif "text-embedding-ada-002" in str(self.embeddings):
                return 1536
            elif "all-MiniLM-L6-v2" in str(self.embeddings):
                return 384
            else:
                return 384  # Default fallback
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedding generation statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_embeddings': 0,
            'total_tokens': 0,
            'errors': 0
        }
