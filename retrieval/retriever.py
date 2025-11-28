"""
Retriever Service for PropIntel

This module provides the core retrieval functionality for semantic search
over the ChromaDB vector database. Supports filtering, multi-query retrieval,
and advanced search options.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ingestion.vector_db.chromadb_manager import ChromaDBManager
from ingestion.vector_db.embedding_generator import EmbeddingGenerator


@dataclass
class RetrievalResult:
    """Represents a single retrieval result"""
    
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    distance: float
    score: float  # 1 - normalized_distance (higher is better)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'metadata': self.metadata,
            'distance': self.distance,
            'score': self.score
        }


class RetrieverService:
    """
    Core retrieval service for semantic search.
    
    Provides:
    - Semantic search with embeddings
    - Metadata filtering
    - Multi-query retrieval
    - Result deduplication
    - Score normalization
    """
    
    def __init__(
        self,
        db_manager: Optional[ChromaDBManager] = None,
        embedder: Optional[EmbeddingGenerator] = None,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None
    ):
        """
        Initialize the retriever service.
        
        Args:
            db_manager: ChromaDB manager instance (creates new if None)
            embedder: Embedding generator instance (creates new if None)
            collection_name: Name of ChromaDB collection (default: propintel_companies)
            persist_directory: Path to ChromaDB persistence directory
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.db_manager = db_manager or ChromaDBManager(
            persist_directory=persist_directory,
            collection_name=collection_name
        )
        
        self.embedder = embedder or EmbeddingGenerator()
        
        self.logger.info("RetrieverService initialized")
    
    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve documents using semantic search.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            filters: Optional metadata filters (e.g., {'company_id': 'astha'})
            collection_name: Optional collection name to query (switches temporarily if provided)
            
        Returns:
            List of RetrievalResult objects sorted by relevance
        """
        self.logger.info(f"Retrieving documents for query: '{query}' (n={n_results})")
        
        # Switch collection if specified
        original_collection = None
        if collection_name and collection_name != self.db_manager.collection_name:
            original_collection = self.db_manager.collection_name
            self.db_manager.switch_collection(collection_name)
        
        try:
            # Generate query embedding
            query_embeddings = self.embedder.generate_embeddings([query])
            
            if not query_embeddings or len(query_embeddings) == 0:
                self.logger.error("Failed to generate query embedding")
                return []
            
            query_embedding = query_embeddings[0]
            
            # Retrieve from ChromaDB
            results = self.db_manager.query(
                query_embedding=query_embedding,
                n_results=n_results,
                where=filters
            )
            
            # Parse and convert to RetrievalResult objects
            retrieval_results = self._parse_results(results)
            
            self.logger.info(f"Retrieved {len(retrieval_results)} results")
            return retrieval_results
            
        except Exception as e:
            self.logger.error(f"Error during retrieval: {e}")
            return []
        finally:
            # Restore original collection if we switched
            if original_collection:
                self.db_manager.switch_collection(original_collection)
    
    def retrieve_multi_query(
        self,
        queries: List[str],
        n_results_per_query: int = 3,
        filters: Optional[Dict[str, Any]] = None,
        deduplicate: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve documents using multiple queries (multi-query retrieval).
        Useful for query expansion and diversification.
        
        Args:
            queries: List of query strings
            n_results_per_query: Number of results per query
            filters: Optional metadata filters
            deduplicate: Whether to remove duplicate results
            
        Returns:
            Combined list of RetrievalResult objects
        """
        self.logger.info(f"Multi-query retrieval with {len(queries)} queries")
        
        all_results = []
        seen_ids = set()
        
        for query in queries:
            results = self.retrieve(
                query=query,
                n_results=n_results_per_query,
                filters=filters
            )
            
            for result in results:
                if deduplicate:
                    if result.chunk_id not in seen_ids:
                        all_results.append(result)
                        seen_ids.add(result.chunk_id)
                else:
                    all_results.append(result)
        
        # Sort by score (descending)
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        self.logger.info(f"Multi-query retrieved {len(all_results)} unique results")
        return all_results
    
    def retrieve_by_section(
        self,
        query: str,
        section: str,
        n_results: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve documents filtered by section.
        
        Args:
            query: Search query text
            section: Section name ('company_info', 'contact_details', 'social_media')
            n_results: Number of results to return
            
        Returns:
            List of RetrievalResult objects from specified section
        """
        filters = {'section': section}
        return self.retrieve(query=query, n_results=n_results, filters=filters)
    
    def retrieve_by_company(
        self,
        query: str,
        company_id: str,
        n_results: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve documents for a specific company.
        
        Args:
            query: Search query text
            company_id: Company identifier
            n_results: Number of results to return
            
        Returns:
            List of RetrievalResult objects for specified company
        """
        filters = {'company_id': company_id}
        return self.retrieve(query=query, n_results=n_results, filters=filters)
    
    def retrieve_hybrid(
        self,
        query: str,
        n_results: int = 5,
        semantic_weight: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval combining semantic and keyword search.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            semantic_weight: Weight for semantic search (0-1), keyword gets (1-semantic_weight)
            filters: Optional metadata filters
            
        Returns:
            List of RetrievalResult objects with hybrid scores
        """
        self.logger.info(f"Hybrid retrieval (semantic_weight={semantic_weight})")
        
        # Get semantic results
        semantic_results = self.retrieve(
            query=query,
            n_results=n_results * 2,  # Get more for better hybrid ranking
            filters=filters
        )
        
        # Apply hybrid scoring (for now, just semantic - can add keyword matching later)
        for result in semantic_results:
            # Simple keyword matching score
            keyword_score = self._calculate_keyword_score(query, result.content)
            
            # Combine scores
            result.score = (
                semantic_weight * result.score +
                (1 - semantic_weight) * keyword_score
            )
        
        # Re-sort by hybrid score
        semantic_results.sort(key=lambda x: x.score, reverse=True)
        
        return semantic_results[:n_results]
    
    def _parse_results(self, results: Dict[str, Any]) -> List[RetrievalResult]:
        """
        Parse ChromaDB results into RetrievalResult objects.
        
        Args:
            results: Raw results from ChromaDB
            
        Returns:
            List of RetrievalResult objects
        """
        retrieval_results = []
        
        if not results or 'ids' not in results:
            return retrieval_results
        
        ids = results['ids'][0] if results['ids'] else []
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []
        
        for i in range(len(ids)):
            # Normalize distance to score (lower distance = higher score)
            # Using simple inversion: score = 1 / (1 + distance)
            distance = distances[i]
            score = 1.0 / (1.0 + distance)
            
            retrieval_results.append(RetrievalResult(
                chunk_id=ids[i],
                content=documents[i],
                metadata=metadatas[i],
                distance=distance,
                score=score
            ))
        
        return retrieval_results
    
    def _calculate_keyword_score(self, query: str, content: str) -> float:
        """
        Calculate keyword matching score.
        
        Args:
            query: Query text
            content: Document content
            
        Returns:
            Keyword score (0-1)
        """
        # Simple keyword matching based on term overlap
        query_terms = set(query.lower().split())
        content_terms = set(content.lower().split())
        
        if not query_terms:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = query_terms & content_terms
        union = query_terms | content_terms
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        return {
            'db_stats': self.db_manager.get_stats(),
            'collection_stats': self.db_manager.get_collection_stats(),
            'embedder_stats': self.embedder.get_stats()
        }
    
    def retrieve_from_collection(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve from a specific collection.
        
        Args:
            query: Search query text
            collection_name: Name of collection to query
            n_results: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of RetrievalResult objects
        """
        return self.retrieve(
            query=query,
            n_results=n_results,
            filters=filters,
            collection_name=collection_name
        )
    
    def retrieve_multi_collection(
        self,
        query: str,
        collection_names: List[str],
        n_results_per_collection: int = 3,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[RetrievalResult]]:
        """
        Retrieve from multiple collections.
        
        Args:
            query: Search query text
            collection_names: List of collection names to query
            n_results_per_collection: Number of results per collection
            filters: Optional metadata filters
            
        Returns:
            Dictionary mapping collection names to results
        """
        self.logger.info(f"Multi-collection retrieval from {len(collection_names)} collections")
        
        results_by_collection = {}
        
        for collection_name in collection_names:
            try:
                results = self.retrieve_from_collection(
                    query=query,
                    collection_name=collection_name,
                    n_results=n_results_per_collection,
                    filters=filters
                )
                results_by_collection[collection_name] = results
            except Exception as e:
                self.logger.error(f"Error retrieving from {collection_name}: {e}")
                results_by_collection[collection_name] = []
        
        return results_by_collection
    
    def switch_collection(self, collection_name: str) -> bool:
        """
        Permanently switch to a different collection.
        
        Args:
            collection_name: Name of collection to switch to
            
        Returns:
            True if successful
        """
        return self.db_manager.switch_collection(collection_name)
    
    def get_current_collection(self) -> str:
        """
        Get the name of the currently active collection.
        
        Returns:
            Current collection name
        """
        return self.db_manager.collection_name
    
    def list_available_collections(self) -> List[str]:
        """
        Get list of all available collections.
        
        Returns:
            List of collection names
        """
        return self.db_manager.get_available_collections()
