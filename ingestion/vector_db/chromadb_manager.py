"""
ChromaDB Manager for PropIntel

This module manages vector database operations using ChromaDB.
Handles collection creation, document storage, and metadata management.
"""

import logging
from typing import List, Dict, Any, Optional
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
import uuid

from .document_chunker import DocumentChunk
from ..config.env_loader import get_config


class ChromaDBManager:
    """
    Manage ChromaDB vector database operations.
    
    Handles:
    - Database initialization
    - Collection management
    - Document storage with embeddings
    - Metadata indexing
    """
    
    def __init__(self, persist_directory: Optional[str] = None, collection_name: str = "propintel_companies"):
        """
        Initialize ChromaDB manager.
        
        Args:
            persist_directory: Path to persist the database (default from .env)
            collection_name: Name of the collection to use
        """
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        
        # Set persist directory
        if persist_directory is None:
            persist_directory = self.config.get("CHROMA_DB_PATH", "./data/chromadb")
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = self._initialize_client()
        
        # Get or create collection
        self.collection_name = collection_name
        self.collection = self._get_or_create_collection()
        
        # Track statistics
        self.stats = {
            'documents_added': 0,
            'documents_updated': 0,
            'errors': 0
        }
        
        self.logger.info(f"ChromaDBManager initialized with collection: {collection_name}")
    
    def _initialize_client(self) -> chromadb.Client:
        """Initialize ChromaDB client with persistence"""
        
        try:
            client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self.logger.info(f"ChromaDB client initialized at: {self.persist_directory}")
            return client
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            count = collection.count()
            self.logger.info(f"Loaded existing collection '{self.collection_name}' with {count} documents")
            return collection
        except Exception:
            # Create new collection
            try:
                collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "description": "PropIntel company data for RAG retrieval",
                        "created_by": "PropIntel Data Ingestion Pipeline"
                    }
                )
                self.logger.info(f"Created new collection: {self.collection_name}")
                return collection
            except Exception as e:
                self.logger.error(f"Failed to create collection: {e}")
                raise
    
    def add_documents(
        self, 
        chunks: List[DocumentChunk], 
        embeddings: List[List[float]]
    ) -> bool:
        """
        Add documents with embeddings to the collection.
        
        Args:
            chunks: List of DocumentChunk objects
            embeddings: List of embedding vectors corresponding to chunks
            
        Returns:
            True if successful, False otherwise
        """
        if len(chunks) != len(embeddings):
            self.logger.error(f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")
            return False
        
        if not chunks:
            self.logger.warning("No chunks to add")
            return True
        
        self.logger.info(f"Adding {len(chunks)} documents to collection")
        
        try:
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            embeddings_list = []
            
            for chunk, embedding in zip(chunks, embeddings):
                # Use chunk_id or generate UUID
                doc_id = chunk.chunk_id if chunk.chunk_id else str(uuid.uuid4())
                ids.append(doc_id)
                
                # Document content
                documents.append(chunk.content)
                
                # Metadata
                metadata = chunk.metadata.copy()
                metadata['chunk_type'] = chunk.chunk_type
                metadatas.append(metadata)
                
                # Embedding
                embeddings_list.append(embedding)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings_list
            )
            
            self.stats['documents_added'] += len(chunks)
            self.logger.info(f"Successfully added {len(chunks)} documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding documents: {e}")
            self.stats['errors'] += 1
            return False
    
    def upsert_documents(
        self, 
        chunks: List[DocumentChunk], 
        embeddings: List[List[float]]
    ) -> bool:
        """
        Update or insert documents with embeddings.
        
        Args:
            chunks: List of DocumentChunk objects
            embeddings: List of embedding vectors
            
        Returns:
            True if successful, False otherwise
        """
        if len(chunks) != len(embeddings):
            self.logger.error(f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")
            return False
        
        if not chunks:
            self.logger.warning("No chunks to upsert")
            return True
        
        self.logger.info(f"Upserting {len(chunks)} documents")
        
        try:
            # Prepare data
            ids = []
            documents = []
            metadatas = []
            embeddings_list = []
            
            for chunk, embedding in zip(chunks, embeddings):
                doc_id = chunk.chunk_id if chunk.chunk_id else str(uuid.uuid4())
                ids.append(doc_id)
                documents.append(chunk.content)
                
                metadata = chunk.metadata.copy()
                metadata['chunk_type'] = chunk.chunk_type
                metadatas.append(metadata)
                
                embeddings_list.append(embedding)
            
            # Upsert to collection
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings_list
            )
            
            self.stats['documents_updated'] += len(chunks)
            self.logger.info(f"Successfully upserted {len(chunks)} documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Error upserting documents: {e}")
            self.stats['errors'] += 1
            return False
    
    def delete_by_company_id(self, company_id: str) -> bool:
        """
        Delete all documents for a specific company.
        
        Args:
            company_id: Company identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Query for all documents with this company_id
            results = self.collection.get(
                where={"company_id": company_id}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                self.logger.info(f"Deleted {len(results['ids'])} documents for company: {company_id}")
                return True
            else:
                self.logger.warning(f"No documents found for company: {company_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error deleting documents: {e}")
            self.stats['errors'] += 1
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        
        try:
            count = self.collection.count()
            
            # Get sample document to check metadata
            sample = self.collection.peek(limit=1)
            
            stats = {
                'collection_name': self.collection_name,
                'total_documents': count,
                'persist_directory': str(self.persist_directory),
                'sample_metadata': sample['metadatas'][0] if sample['metadatas'] else None
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def reset_collection(self) -> bool:
        """
        Delete and recreate the collection (WARNING: Deletes all data).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.warning(f"Resetting collection: {self.collection_name}")
            
            # Delete collection
            self.client.delete_collection(name=self.collection_name)
            
            # Recreate collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "PropIntel company data for RAG retrieval",
                    "created_by": "PropIntel Data Ingestion Pipeline"
                }
            )
            
            # Reset stats
            self.stats['documents_added'] = 0
            self.stats['documents_updated'] = 0
            
            self.logger.info(f"Collection reset successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error resetting collection: {e}")
            self.stats['errors'] += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get operation statistics"""
        return self.stats.copy()
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query for similar documents using embedding.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter
            
        Returns:
            Query results with documents, distances, and metadata
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            
            num_results = len(results['ids'][0]) if results['ids'] else 0
            self.logger.info(f"Query returned {num_results} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Error querying collection: {e}")
            return {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    def query_similar(
        self, 
        query_text: str, 
        query_embedding: List[float],
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query for similar documents (for testing retrieval).
        
        Args:
            query_text: Query text for logging
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where_filter: Optional metadata filter
            
        Returns:
            Query results with documents, distances, and metadata
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )
            
            self.logger.info(f"Query '{query_text}' returned {len(results['ids'][0])} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Error querying collection: {e}")
            return {}
