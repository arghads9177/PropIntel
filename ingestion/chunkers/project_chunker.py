"""
Project Data Chunker

Creates semantic chunks from project data for vector storage:
- Project overview chunk
- Tower-specific chunks
- Location/contact chunk
"""

from typing import Dict, Any, List
from datetime import datetime

from ingestion.config.env_loader import get_config


class ProjectChunker:
    """Create semantic chunks from project data."""
    
    def __init__(self):
        """Initialize project chunker."""
        self.config = get_config()
        self.logger = self.config.get_logger()
        self.logger.info("ProjectChunker initialized")
    
    def chunk(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create semantic chunks from project data.
        
        Args:
            project: Cleaned project data dictionary
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        
        try:
            # Chunk 1: Project Overview
            overview_chunk = self._create_overview_chunk(project)
            if overview_chunk:
                chunks.append(overview_chunk)
            
            # Chunk 2-N: Tower-specific chunks (one per tower)
            tower_chunks = self._create_tower_chunks(project)
            chunks.extend(tower_chunks)
            
            # Chunk N+1: Location and Developer info
            location_chunk = self._create_location_chunk(project)
            if location_chunk:
                chunks.append(location_chunk)
            
            self.logger.info(f"Created {len(chunks)} chunks for {project.get('project_name', 'Unknown')}")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error chunking project {project.get('project_name', 'Unknown')}: {e}", exc_info=True)
            return []
    
    def _create_overview_chunk(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create project overview chunk.
        
        Args:
            project: Project data
            
        Returns:
            Overview chunk with text and metadata
        """
        project_name = project.get('project_name', '')
        category = project.get('category', '')
        developed_by = project.get('developed_by', '')
        towers = project.get('towers', {})
        tower_count = len(towers)
        
        # Build overview text
        text_parts = [
            f"Project Name: {project_name}",
            f"Status: {category.capitalize()}",
            f"Developer: {developed_by}",
        ]
        
        # Add tower summary
        if tower_count > 0:
            text_parts.append(f"Number of Towers: {tower_count}")
        
        text = "\n".join(text_parts)
        
        return {
            "text": text,
            "metadata": {
                "project_name": project_name,
                "category": category,
                "chunk_type": "overview",
                "developer": developed_by,
                "tower_count": tower_count
            }
        }
    
    def _create_tower_chunks(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create individual chunks for each tower.
        
        Args:
            project: Project data
            
        Returns:
            List of tower-specific chunks
        """
        chunks = []
        project_name = project.get('project_name', '')
        category = project.get('category', '')
        towers = project.get('towers', {})
        
        for tower_id, tower_data in towers.items():
            floors = tower_data.get('number_of_floors', '')
            
            # Build tower text
            text_parts = [
                f"Project: {project_name}",
                f"Tower: {tower_id.replace('_', ' ').title()}",
            ]
            
            if floors:
                text_parts.append(f"Number of Floors: {floors}")
            
            text = "\n".join(text_parts)
            
            chunk = {
                "text": text,
                "metadata": {
                    "project_name": project_name,
                    "category": category,
                    "chunk_type": "tower",
                    "tower_id": tower_id,
                    "number_of_floors": floors
                }
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def _create_location_chunk(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create location and developer information chunk.
        
        Args:
            project: Project data
            
        Returns:
            Location chunk with text and metadata
        """
        project_name = project.get('project_name', '')
        category = project.get('category', '')
        location = project.get('location', '')
        developed_by = project.get('developed_by', '')
        
        # Build location text
        text_parts = [
            f"Project: {project_name}",
        ]
        
        if location:
            text_parts.append(f"Location: {location}")
        
        if developed_by:
            text_parts.append(f"Developed By: {developed_by}")
        
        text = "\n".join(text_parts)
        
        return {
            "text": text,
            "metadata": {
                "project_name": project_name,
                "category": category,
                "chunk_type": "location",
                "location": location,
                "developer": developed_by
            }
        }


def main():
    """Test the chunker with sample data."""
    chunker = ProjectChunker()
    
    # Test with sample project
    sample_project = {
        "project_name": "Test Apartment",
        "location": "Test Location, West Bengal",
        "towers": {
            "tower_1": {
                "number_of_floors": "G+4"
            },
            "tower_2": {
                "number_of_floors": "B+G+5"
            }
        },
        "developed_by": "Test Construction Pvt. Ltd.",
        "category": "running",
        "metadata": {
            "cleaned_at": "2025-11-27T12:00:00",
            "source": "web_scraping"
        }
    }
    
    chunks = chunker.chunk(sample_project)
    
    print(f"Created {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i} ({chunk['metadata']['chunk_type']}):")
        print(f"{chunk['text']}")
        print(f"Metadata: {chunk['metadata']}")
        print()


if __name__ == "__main__":
    main()
