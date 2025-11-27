"""
Project Vector Store Ingestor

Ingests project chunks into ChromaDB vector store:
- Loads chunked project data
- Creates embeddings
- Stores in ChromaDB with metadata
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import chromadb
from chromadb.config import Settings

from ingestion.config.env_loader import get_config


class ProjectVectorIngestor:
    """Ingest project chunks into vector store."""
    
    def __init__(self, collection_name: str = "propintel_knowledge"):
        """
        Initialize vector store ingestor.
        
        Args:
            collection_name: Name of ChromaDB collection
        """
        self.config = get_config()
        self.logger = self.config.get_logger()
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.config.get_chroma_db_path())
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        self.logger.info(f"ProjectVectorIngestor initialized")
        self.logger.info(f"Collection: {collection_name}")
        self.logger.info(f"ChromaDB path: {self.config.get_chroma_db_path()}")
    
    def ingest_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest chunks into vector store.
        
        Args:
            chunks: List of chunk dictionaries with text and metadata
            
        Returns:
            Ingestion statistics
        """
        stats = {
            'total': len(chunks),
            'successful': 0,
            'failed': 0,
            'by_type': {
                'overview': 0,
                'tower': 0,
                'location': 0
            },
            'failed_chunks': []
        }
        
        if not chunks:
            self.logger.warning("No chunks to ingest")
            return stats
        
        self.logger.info(f"Starting ingestion of {len(chunks)} chunks")
        
        # Prepare batch data
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            try:
                # Generate unique ID
                chunk_id = self._generate_chunk_id(chunk, i)
                
                # Extract text
                text = chunk.get('text', '')
                if not text:
                    self.logger.warning(f"Empty text in chunk {i}")
                    stats['failed'] += 1
                    continue
                
                # Extract metadata
                metadata = chunk.get('metadata', {})
                
                # Add to batch
                ids.append(chunk_id)
                documents.append(text)
                metadatas.append(metadata)
                
                # Track by type
                chunk_type = metadata.get('chunk_type', 'unknown')
                if chunk_type in stats['by_type']:
                    stats['by_type'][chunk_type] += 1
                
                stats['successful'] += 1
                
            except Exception as e:
                self.logger.error(f"Error preparing chunk {i}: {e}")
                stats['failed'] += 1
                stats['failed_chunks'].append(i)
        
        # Add batch to collection
        if ids:
            try:
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                self.logger.info(f"Successfully ingested {len(ids)} chunks")
            except Exception as e:
                self.logger.error(f"Error adding to collection: {e}", exc_info=True)
                stats['failed'] = len(ids)
                stats['successful'] = 0
        
        return stats
    
    def _generate_chunk_id(self, chunk: Dict[str, Any], index: int) -> str:
        """
        Generate unique ID for chunk.
        
        Args:
            chunk: Chunk dictionary
            index: Chunk index
            
        Returns:
            Unique chunk ID
        """
        metadata = chunk.get('metadata', {})
        project_name = metadata.get('project_name', 'unknown')
        chunk_type = metadata.get('chunk_type', 'unknown')
        
        # Sanitize project name for ID
        safe_name = project_name.lower().replace(' ', '_').replace('-', '_')
        
        # For tower chunks, include tower_id
        if chunk_type == 'tower':
            tower_id = metadata.get('tower_id', 'unknown')
            return f"project_{safe_name}_{chunk_type}_{tower_id}"
        
        # For other chunks
        return f"project_{safe_name}_{chunk_type}"
    
    def clear_project_data(self) -> bool:
        """
        Clear existing project data from collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all project chunk IDs
            results = self.collection.get()
            
            if results and results['ids']:
                project_ids = [
                    id for id in results['ids'] 
                    if id.startswith('project_')
                ]
                
                if project_ids:
                    self.collection.delete(ids=project_ids)
                    self.logger.info(f"Deleted {len(project_ids)} existing project chunks")
                    return True
            
            self.logger.info("No existing project data to clear")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing project data: {e}", exc_info=True)
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Collection statistics
        """
        try:
            count = self.collection.count()
            
            # Get sample to analyze
            results = self.collection.get(limit=1000)
            
            stats = {
                'total_documents': count,
                'collection_name': self.collection.name,
                'sample_metadata': results['metadatas'][:3] if results['metadatas'] else []
            }
            
            # Count by type if metadata available
            if results['metadatas']:
                type_counts = {}
                for metadata in results['metadatas']:
                    chunk_type = metadata.get('chunk_type', 'unknown')
                    type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
                stats['by_type'] = type_counts
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}")
            return {'error': str(e)}


def main():
    """Test the ingestor with sample chunks."""
    ingestor = ProjectVectorIngestor()
    
    # Test with sample chunks
    sample_chunks = [
        {
            "text": "Project Name: Test Apartment\nStatus: Running\nDeveloper: Test Construction",
            "metadata": {
                "project_name": "Test Apartment",
                "category": "running",
                "chunk_type": "overview",
                "developer": "Test Construction",
                "tower_count": 2
            }
        },
        {
            "text": "Project: Test Apartment\nTower: Tower 1\nNumber of Floors: G+4",
            "metadata": {
                "project_name": "Test Apartment",
                "category": "running",
                "chunk_type": "tower",
                "tower_id": "tower_1",
                "number_of_floors": "G+4"
            }
        }
    ]
    
    print("Testing ingestion with sample chunks...")
    stats = ingestor.ingest_chunks(sample_chunks)
    
    print(f"\nIngestion Stats:")
    print(f"Total: {stats['total']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    
    print("\nCollection Stats:")
    collection_stats = ingestor.get_collection_stats()
    print(f"Total documents: {collection_stats.get('total_documents', 0)}")


if __name__ == "__main__":
    main()
