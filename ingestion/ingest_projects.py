"""
Ingest Projects Script

Ingests chunked project data into ChromaDB vector store:
- Reads from data/chunked/project_chunks.json
- Optionally clears existing project data
- Ingests chunks with embeddings
- Provides ingestion statistics
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import argparse

from ingestion.ingestors.project_ingestor import ProjectVectorIngestor
from ingestion.config.env_loader import get_config


class IngestionRunner:
    """Orchestrates the vector store ingestion process."""
    
    def __init__(self,
                 chunked_file: str = "data/chunked/project_chunks.json",
                 clear_existing: bool = False):
        """
        Initialize ingestion runner.
        
        Args:
            chunked_file: Path to chunked data JSON file
            clear_existing: Whether to clear existing project data before ingestion
        """
        self.config = get_config()
        self.logger = self.config.get_logger()
        
        self.chunked_file = Path(chunked_file)
        self.clear_existing = clear_existing
        
        # Initialize ingestor
        self.ingestor = ProjectVectorIngestor()
        
        self.logger.info(f"IngestionRunner initialized")
        self.logger.info(f"Input file: {self.chunked_file}")
        self.logger.info(f"Clear existing: {self.clear_existing}")
    
    def load_chunks(self) -> List[Dict[str, Any]]:
        """
        Load chunks from JSON file.
        
        Returns:
            List of chunk dictionaries
        """
        try:
            with open(self.chunked_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            self.logger.info(f"Loaded {len(chunks)} chunks from {self.chunked_file}")
            return chunks
            
        except FileNotFoundError:
            self.logger.error(f"Chunked data file not found: {self.chunked_file}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading chunks: {e}")
            return []
    
    def ingest_all(self) -> Dict[str, Any]:
        """
        Ingest all chunks into vector store.
        
        Returns:
            Summary statistics
        """
        print(f"\n{'='*60}")
        print(f"PROJECT DATA INGESTION")
        print(f"{'='*60}\n")
        
        # Clear existing data if requested
        if self.clear_existing:
            print("Clearing existing project data from vector store...")
            if self.ingestor.clear_project_data():
                print("✓ Existing project data cleared\n")
            else:
                print("✗ Failed to clear existing data\n")
        
        # Load chunks
        print(f"Loading chunks from {self.chunked_file}...")
        chunks = self.load_chunks()
        
        if not chunks:
            print("✗ No chunks to ingest")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'by_type': {}
            }
        
        print(f"✓ Loaded {len(chunks)} chunks\n")
        
        # Ingest chunks
        print(f"Ingesting {len(chunks)} chunks into ChromaDB...")
        stats = self.ingestor.ingest_chunks(chunks)
        
        # Print summary
        self._print_summary(stats)
        
        # Get collection stats
        print("\nGetting collection statistics...")
        collection_stats = self.ingestor.get_collection_stats()
        self._print_collection_stats(collection_stats)
        
        return stats
    
    def _print_summary(self, stats: Dict[str, Any]):
        """Print ingestion summary."""
        print(f"\n{'='*60}")
        print(f"INGESTION COMPLETED")
        print(f"{'='*60}")
        print(f"Total Chunks: {stats['total']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        
        if stats['by_type']:
            print(f"\nChunks by Type:")
            for chunk_type, count in stats['by_type'].items():
                print(f"  {chunk_type.capitalize()}: {count}")
        
        if stats.get('failed_chunks'):
            print(f"\nFailed Chunk Indices:")
            for idx in stats['failed_chunks']:
                print(f"  - {idx}")
        
        print(f"{'='*60}\n")
        
        if stats['failed'] == 0:
            print("✓ All chunks ingested successfully!")
        else:
            print(f"⚠ Partially successful: {stats['failed']} chunks failed")
    
    def _print_collection_stats(self, stats: Dict[str, Any]):
        """Print collection statistics."""
        print(f"\n{'='*60}")
        print(f"VECTOR STORE STATISTICS")
        print(f"{'='*60}")
        print(f"Collection: {stats.get('collection_name', 'unknown')}")
        print(f"Total Documents: {stats.get('total_documents', 0)}")
        
        if stats.get('by_type'):
            print(f"\nDocuments by Type:")
            for doc_type, count in stats['by_type'].items():
                print(f"  {doc_type.capitalize()}: {count}")
        
        print(f"{'='*60}\n")


def main():
    """Main entry point for ingestion script."""
    parser = argparse.ArgumentParser(description='Ingest project chunks into vector store')
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing project data before ingestion'
    )
    parser.add_argument(
        '--chunked-file',
        default='data/chunked/project_chunks.json',
        help='Path to chunked data file'
    )
    
    args = parser.parse_args()
    
    config = get_config()
    logger = config.get_logger()
    
    try:
        logger.info("="*60)
        logger.info("STARTING VECTOR STORE INGESTION")
        logger.info("="*60)
        
        # Run ingestion
        runner = IngestionRunner(
            chunked_file=args.chunked_file,
            clear_existing=args.clear
        )
        stats = runner.ingest_all()
        
        logger.info("="*60)
        logger.info("INGESTION PROCESS COMPLETED")
        logger.info(f"Successful: {stats['successful']}/{stats['total']}")
        logger.info("="*60)
        
        return 0 if stats['failed'] == 0 else 1
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        print(f"\nFatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
