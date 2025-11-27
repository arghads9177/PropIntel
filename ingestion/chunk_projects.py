"""
Chunk Projects Script

Processes cleaned project data and creates semantic chunks:
- Reads from data/cleaned/projects.json
- Creates semantic chunks for each project
- Saves to data/chunked/project_chunks.json
"""

import json
from pathlib import Path
from typing import Dict, Any, List

from ingestion.chunkers.project_chunker import ProjectChunker
from ingestion.config.env_loader import get_config


class ChunkingRunner:
    """Orchestrates the chunking process for project data."""
    
    def __init__(self,
                 cleaned_file: str = "data/cleaned/projects.json",
                 chunked_file: str = "data/chunked/project_chunks.json"):
        """
        Initialize chunking runner.
        
        Args:
            cleaned_file: Path to cleaned projects JSON file
            chunked_file: Path to output chunked data JSON file
        """
        self.config = get_config()
        self.logger = self.config.get_logger()
        
        self.cleaned_file = Path(cleaned_file)
        self.chunked_file = Path(chunked_file)
        
        # Create chunked directory
        self.chunked_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize chunker
        self.chunker = ProjectChunker()
        
        self.logger.info(f"ChunkingRunner initialized")
        self.logger.info(f"Input file: {self.cleaned_file}")
        self.logger.info(f"Output file: {self.chunked_file}")
    
    def load_cleaned_data(self) -> List[Dict[str, Any]]:
        """
        Load cleaned projects from JSON file.
        
        Returns:
            List of cleaned project dictionaries
        """
        try:
            with open(self.cleaned_file, 'r', encoding='utf-8') as f:
                projects = json.load(f)
            
            self.logger.info(f"Loaded {len(projects)} projects from {self.cleaned_file}")
            return projects
            
        except FileNotFoundError:
            self.logger.error(f"Cleaned data file not found: {self.cleaned_file}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading cleaned data: {e}")
            return []
    
    def save_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Save all chunks to JSON file.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.chunked_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(chunks)} chunks to: {self.chunked_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving chunks: {e}")
            return False
    
    def chunk_all(self) -> Dict[str, Any]:
        """
        Create chunks for all projects.
        
        Returns:
            Summary statistics
        """
        stats = {
            'total_projects': 0,
            'total_chunks': 0,
            'successful_projects': 0,
            'failed_projects': 0,
            'chunks_by_type': {
                'overview': 0,
                'tower': 0,
                'location': 0
            },
            'chunks_by_category': {
                'upcoming': 0,
                'running': 0,
                'completed': 0
            },
            'failed_projects_list': []
        }
        
        # Load cleaned projects
        projects = self.load_cleaned_data()
        
        if not projects:
            self.logger.error("No projects to chunk")
            return stats
        
        stats['total_projects'] = len(projects)
        
        # Collect all chunks
        all_chunks = []
        
        self.logger.info(f"Starting chunking of {len(projects)} projects")
        print(f"\n{'='*60}")
        print(f"CHUNKING {len(projects)} PROJECTS")
        print(f"{'='*60}\n")
        
        # Process each project
        for i, project in enumerate(projects, 1):
            project_name = project.get('project_name', 'Unknown')
            category = project.get('category', 'unknown')
            
            print(f"[{i}/{len(projects)}] Chunking: {project_name}")
            self.logger.info(f"Processing {i}/{len(projects)}: {project_name}")
            
            # Create chunks
            chunks = self.chunker.chunk(project)
            
            if not chunks:
                stats['failed_projects'] += 1
                stats['failed_projects_list'].append(project_name)
                print(f"  ✗ Failed to create chunks")
                continue
            
            # Add chunks to collection
            all_chunks.extend(chunks)
            stats['successful_projects'] += 1
            stats['total_chunks'] += len(chunks)
            
            # Count by type and category
            for chunk in chunks:
                chunk_type = chunk['metadata'].get('chunk_type', 'unknown')
                if chunk_type in stats['chunks_by_type']:
                    stats['chunks_by_type'][chunk_type] += 1
                
                if category in stats['chunks_by_category']:
                    stats['chunks_by_category'][category] += len(chunks)
            
            print(f"  ✓ Created {len(chunks)} chunks")
            
            # Progress update
            if i % 5 == 0 or i == len(projects):
                print(f"\nProgress: {i}/{len(projects)} processed")
                print(f"Total chunks created: {stats['total_chunks']}\n")
        
        # Save all chunks
        if all_chunks:
            if self.save_chunks(all_chunks):
                print(f"\n✓ Saved {len(all_chunks)} chunks to {self.chunked_file}")
            else:
                print(f"\n✗ Failed to save chunks to {self.chunked_file}")
        
        # Print summary
        self._print_summary(stats)
        
        return stats
    
    def _print_summary(self, stats: Dict[str, Any]):
        """Print chunking summary."""
        print(f"\n{'='*60}")
        print(f"CHUNKING COMPLETED")
        print(f"{'='*60}")
        print(f"Total Projects: {stats['total_projects']}")
        print(f"Successful: {stats['successful_projects']}")
        print(f"Failed: {stats['failed_projects']}")
        print(f"\nTotal Chunks: {stats['total_chunks']}")
        
        print(f"\nChunks by Type:")
        for chunk_type, count in stats['chunks_by_type'].items():
            print(f"  {chunk_type.capitalize()}: {count}")
        
        if stats['failed_projects_list']:
            print(f"\nFailed Projects:")
            for project in stats['failed_projects_list']:
                print(f"  - {project}")
        
        print(f"\nChunked data saved to: {self.chunked_file}")
        print(f"{'='*60}\n")
        
        if stats['failed_projects'] == 0:
            print("All projects chunked successfully!")
        else:
            print(f"Partially successful: {stats['failed_projects']} projects failed")


def main():
    """Main entry point for chunking script."""
    config = get_config()
    logger = config.get_logger()
    
    try:
        logger.info("="*60)
        logger.info("STARTING PROJECT DATA CHUNKING")
        logger.info("="*60)
        
        # Run chunking
        runner = ChunkingRunner()
        stats = runner.chunk_all()
        
        logger.info("="*60)
        logger.info("CHUNKING PROCESS COMPLETED")
        logger.info(f"Total Chunks: {stats['total_chunks']}")
        logger.info("="*60)
        
        return 0 if stats['failed_projects'] == 0 else 1
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        print(f"\nFatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
