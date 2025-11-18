"""
PropIntel Data Ingestion Pipeline - Execution Script

This script runs the complete Phase 4A: Data Ingestion Pipeline
1. Loads clean company data
2. Chunks documents semantically
3. Generates embeddings
4. Stores in ChromaDB vector database

Usage:
    python run_data_ingestion.py [--reset] [--test-query "query text"]
"""

import sys
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ingestion.vector_db.ingestion_orchestrator import IngestionOrchestrator
from ingestion.config.env_loader import get_config


def setup_logging():
    """Configure logging for the pipeline"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data_ingestion.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main execution function"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="PropIntel Data Ingestion Pipeline")
    parser.add_argument(
        '--reset', 
        action='store_true', 
        help='Reset the database before ingestion (deletes all existing data)'
    )
    parser.add_argument(
        '--test-query', 
        type=str, 
        help='Test retrieval with a query after ingestion'
    )
    parser.add_argument(
        '--data-dir', 
        type=str, 
        default='./data/processed',
        help='Directory containing clean JSON files (default: ./data/processed)'
    )
    parser.add_argument(
        '--pattern', 
        type=str, 
        default='*_clean.json',
        help='File pattern to match (default: *_clean.json)'
    )
    parser.add_argument(
        '--embedding-model', 
        type=str, 
        default='openai',
        choices=['openai', 'huggingface'],
        help='Embedding model to use (default: openai)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("PROPINTEL DATA INGESTION PIPELINE - PHASE 4A")
    logger.info("="*80)
    
    try:
        # Load environment configuration
        config = get_config()
        logger.info("Environment configuration loaded")
        
        # Initialize orchestrator
        logger.info(f"Initializing ingestion orchestrator with {args.embedding_model} embeddings...")
        orchestrator = IngestionOrchestrator(embedding_model=args.embedding_model)
        
        # Reset database if requested
        if args.reset:
            logger.warning("Resetting database (all existing data will be deleted)...")
            if orchestrator.reset_database():
                logger.info("Database reset successfully")
            else:
                logger.error("Failed to reset database")
                return 1
        
        # Run ingestion
        logger.info(f"\nStarting data ingestion from: {args.data_dir}")
        logger.info(f"File pattern: {args.pattern}\n")
        
        stats = orchestrator.ingest_directory(
            directory_path=args.data_dir,
            pattern=args.pattern
        )
        
        # Print detailed report
        orchestrator.print_pipeline_report()
        
        # Test retrieval if requested
        if args.test_query:
            logger.info("\n" + "="*80)
            logger.info("TESTING RETRIEVAL")
            logger.info("="*80)
            orchestrator.test_retrieval(args.test_query, n_results=3)
        
        logger.info("\n✅ Data ingestion pipeline completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Pipeline failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
