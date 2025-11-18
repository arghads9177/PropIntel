"""
Ingestion Orchestrator for PropIntel

This module orchestrates the complete data ingestion pipeline:
1. Load clean data
2. Chunk documents
3. Generate embeddings
4. Store in ChromaDB

Coordinates all components for end-to-end data ingestion.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .document_chunker import DocumentChunker, DocumentChunk
from .embedding_generator import EmbeddingGenerator
from .chromadb_manager import ChromaDBManager


class IngestionOrchestrator:
    """
    Orchestrate the complete data ingestion pipeline.
    
    Workflow:
    1. Load clean JSON data
    2. Chunk into semantic units
    3. Generate embeddings
    4. Store in ChromaDB
    5. Report statistics
    """
    
    def __init__(
        self, 
        embedding_model: str = "openai",
        collection_name: str = "propintel_companies",
        persist_directory: Optional[str] = None
    ):
        """
        Initialize the ingestion orchestrator.
        
        Args:
            embedding_model: Model to use for embeddings ('openai', 'huggingface')
            collection_name: Name of ChromaDB collection
            persist_directory: Path to persist ChromaDB
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.chunker = DocumentChunker()
        self.embedder = EmbeddingGenerator(model_name=embedding_model)
        self.db_manager = ChromaDBManager(
            persist_directory=persist_directory,
            collection_name=collection_name
        )
        
        # Track pipeline statistics
        self.pipeline_stats = {
            'start_time': None,
            'end_time': None,
            'duration_seconds': 0,
            'files_processed': 0,
            'chunks_created': 0,
            'embeddings_generated': 0,
            'documents_stored': 0,
            'errors': []
        }
        
        self.logger.info("IngestionOrchestrator initialized")
    
    def ingest_file(self, file_path: str, company_id: Optional[str] = None) -> bool:
        """
        Ingest a single clean JSON file.
        
        Args:
            file_path: Path to clean JSON file
            company_id: Optional company identifier (extracted from filename if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Ingesting file: {file_path}")
        
        try:
            # Load JSON data
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract company_id from filename if not provided
            if company_id is None:
                file_stem = Path(file_path).stem
                # Remove '_clean' suffix if present
                company_id = file_stem.replace('_clean', '')
            
            # Chunk the data
            chunks = self.chunker.chunk_company_data(data, company_id)
            self.pipeline_stats['chunks_created'] += len(chunks)
            self.logger.info(f"Created {len(chunks)} chunks")
            
            # Generate embeddings
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedder.generate_embeddings(chunk_texts)
            self.pipeline_stats['embeddings_generated'] += len(embeddings)
            self.logger.info(f"Generated {len(embeddings)} embeddings")
            
            # Store in ChromaDB
            success = self.db_manager.upsert_documents(chunks, embeddings)
            
            if success:
                self.pipeline_stats['documents_stored'] += len(chunks)
                self.pipeline_stats['files_processed'] += 1
                self.logger.info(f"Successfully ingested file: {file_path}")
                return True
            else:
                self.logger.error(f"Failed to store documents for: {file_path}")
                self.pipeline_stats['errors'].append({
                    'file': file_path,
                    'error': 'Failed to store documents'
                })
                return False
                
        except Exception as e:
            self.logger.error(f"Error ingesting file {file_path}: {e}")
            self.pipeline_stats['errors'].append({
                'file': file_path,
                'error': str(e)
            })
            return False
    
    def ingest_directory(self, directory_path: str, pattern: str = "*_clean.json") -> Dict[str, Any]:
        """
        Ingest all clean JSON files from a directory.
        
        Args:
            directory_path: Path to directory containing clean JSON files
            pattern: File pattern to match (default: *_clean.json)
            
        Returns:
            Dictionary with ingestion statistics
        """
        self.logger.info(f"Ingesting directory: {directory_path}")
        self.pipeline_stats['start_time'] = datetime.now()
        
        try:
            directory = Path(directory_path)
            
            # Find all matching files
            files = list(directory.glob(pattern))
            self.logger.info(f"Found {len(files)} files matching pattern: {pattern}")
            
            if not files:
                self.logger.warning(f"No files found matching pattern: {pattern}")
                return self.get_pipeline_stats()
            
            # Process each file
            successful = 0
            failed = 0
            
            for file_path in files:
                self.logger.info(f"\nProcessing: {file_path.name}")
                
                if self.ingest_file(str(file_path)):
                    successful += 1
                else:
                    failed += 1
            
            # Record end time
            self.pipeline_stats['end_time'] = datetime.now()
            duration = self.pipeline_stats['end_time'] - self.pipeline_stats['start_time']
            self.pipeline_stats['duration_seconds'] = duration.total_seconds()
            
            # Log summary
            self.logger.info("\n" + "="*60)
            self.logger.info("INGESTION COMPLETE")
            self.logger.info("="*60)
            self.logger.info(f"Files processed: {successful}/{len(files)}")
            self.logger.info(f"Total chunks: {self.pipeline_stats['chunks_created']}")
            self.logger.info(f"Total embeddings: {self.pipeline_stats['embeddings_generated']}")
            self.logger.info(f"Total documents stored: {self.pipeline_stats['documents_stored']}")
            self.logger.info(f"Duration: {self.pipeline_stats['duration_seconds']:.2f} seconds")
            
            if failed > 0:
                self.logger.warning(f"Failed files: {failed}")
                for error in self.pipeline_stats['errors']:
                    self.logger.warning(f"  - {error['file']}: {error['error']}")
            
            return self.get_pipeline_stats()
            
        except Exception as e:
            self.logger.error(f"Error ingesting directory: {e}")
            self.pipeline_stats['errors'].append({
                'directory': directory_path,
                'error': str(e)
            })
            return self.get_pipeline_stats()
    
    def ingest_data_dict(self, data: Dict[str, Any], company_id: str) -> bool:
        """
        Ingest data directly from a dictionary.
        
        Args:
            data: Company data dictionary
            company_id: Company identifier
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Ingesting data for company: {company_id}")
        
        try:
            # Chunk the data
            chunks = self.chunker.chunk_company_data(data, company_id)
            self.pipeline_stats['chunks_created'] += len(chunks)
            
            # Generate embeddings
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedder.generate_embeddings(chunk_texts)
            self.pipeline_stats['embeddings_generated'] += len(embeddings)
            
            # Store in ChromaDB
            success = self.db_manager.upsert_documents(chunks, embeddings)
            
            if success:
                self.pipeline_stats['documents_stored'] += len(chunks)
                return True
            else:
                self.pipeline_stats['errors'].append({
                    'company_id': company_id,
                    'error': 'Failed to store documents'
                })
                return False
                
        except Exception as e:
            self.logger.error(f"Error ingesting data for {company_id}: {e}")
            self.pipeline_stats['errors'].append({
                'company_id': company_id,
                'error': str(e)
            })
            return False
    
    def delete_company_data(self, company_id: str) -> bool:
        """
        Delete all data for a specific company.
        
        Args:
            company_id: Company identifier
            
        Returns:
            True if successful, False otherwise
        """
        return self.db_manager.delete_by_company_id(company_id)
    
    def reset_database(self) -> bool:
        """
        Reset the entire database (WARNING: Deletes all data).
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.warning("Resetting entire database!")
        return self.db_manager.reset_collection()
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        
        stats = self.pipeline_stats.copy()
        
        # Add component stats
        stats['chunker_stats'] = self.chunker.get_chunk_stats()
        stats['embedder_stats'] = self.embedder.get_stats()
        stats['db_stats'] = self.db_manager.get_stats()
        stats['collection_stats'] = self.db_manager.get_collection_stats()
        
        return stats
    
    def print_pipeline_report(self):
        """Print a formatted pipeline report"""
        
        stats = self.get_pipeline_stats()
        
        print("\n" + "="*80)
        print("PROPINTEL DATA INGESTION PIPELINE REPORT")
        print("="*80)
        
        # Pipeline stats
        print(f"\n📊 PIPELINE STATISTICS")
        print(f"   Files Processed: {stats['files_processed']}")
        print(f"   Chunks Created: {stats['chunks_created']}")
        print(f"   Embeddings Generated: {stats['embeddings_generated']}")
        print(f"   Documents Stored: {stats['documents_stored']}")
        
        if stats['start_time'] and stats['end_time']:
            print(f"   Start Time: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   End Time: {stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Duration: {stats['duration_seconds']:.2f} seconds")
        
        # Collection stats
        if 'collection_stats' in stats and stats['collection_stats']:
            col_stats = stats['collection_stats']
            print(f"\n💾 DATABASE STATISTICS")
            print(f"   Collection: {col_stats.get('collection_name', 'N/A')}")
            print(f"   Total Documents: {col_stats.get('total_documents', 0)}")
            print(f"   Persist Directory: {col_stats.get('persist_directory', 'N/A')}")
        
        # Errors
        if stats['errors']:
            print(f"\n⚠️  ERRORS ({len(stats['errors'])})")
            for error in stats['errors']:
                print(f"   - {error}")
        else:
            print(f"\n✅ No errors encountered")
        
        print("\n" + "="*80)
    
    def test_retrieval(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """
        Test retrieval with a sample query.
        
        Args:
            query: Query text
            n_results: Number of results to return
            
        Returns:
            Query results
        """
        self.logger.info(f"Testing retrieval with query: '{query}'")
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.generate_single_embedding(query)
            
            # Query ChromaDB
            results = self.db_manager.query_similar(
                query_text=query,
                query_embedding=query_embedding,
                n_results=n_results
            )
            
            # Format results
            if results and 'documents' in results and results['documents']:
                print(f"\n🔍 Query: '{query}'")
                print(f"   Found {len(results['documents'][0])} results:\n")
                
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                ), 1):
                    print(f"   Result {i}:")
                    print(f"   Distance: {distance:.4f}")
                    print(f"   Company: {metadata.get('company_id', 'Unknown')}")
                    print(f"   Section: {metadata.get('section', 'Unknown')}")
                    print(f"   Content: {doc[:200]}...")
                    print()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error testing retrieval: {e}")
            return {}
