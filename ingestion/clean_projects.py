"""
Clean Projects Script

Processes raw project JSON files and creates cleaned versions.
- Reads from data/raw/projects/
- Applies cleaning and standardization
- Saves to data/cleaned/projects/
"""

import json
from pathlib import Path
from typing import Dict, Any

from ingestion.cleaners.project_cleaner import ProjectCleaner
from ingestion.config.env_loader import get_config


class CleaningRunner:
    """Orchestrates the cleaning process for all project files."""
    
    def __init__(self, 
                 raw_dir: str = "data/raw/projects",
                 cleaned_file: str = "data/cleaned/projects.json"):
        """
        Initialize cleaning runner.
        
        Args:
            raw_dir: Directory containing raw JSON files
            cleaned_file: Path to output JSON file containing all cleaned projects
        """
        self.config = get_config()
        self.logger = self.config.get_logger()
        
        self.raw_dir = Path(raw_dir)
        self.cleaned_file = Path(cleaned_file)
        
        # Create cleaned directory
        self.cleaned_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize cleaner
        self.cleaner = ProjectCleaner()
        
        self.logger.info(f"CleaningRunner initialized")
        self.logger.info(f"Raw directory: {self.raw_dir}")
        self.logger.info(f"Output file: {self.cleaned_file}")
    
    def load_raw_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load raw JSON file.
        
        Args:
            file_path: Path to raw JSON file
            
        Returns:
            Raw data dictionary
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {e}")
            return None
    
    def save_cleaned_data(self, projects: list) -> bool:
        """
        Save all cleaned projects to a single JSON file.
        
        Args:
            projects: List of cleaned project dictionaries
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.cleaned_file, 'w', encoding='utf-8') as f:
                json.dump(projects, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(projects)} projects to: {self.cleaned_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving cleaned data: {e}")
            return False
    
    def clean_all(self) -> Dict[str, Any]:
        """
        Clean all raw project files and save to single JSON array.
        
        Returns:
            Summary statistics
        """
        stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'by_category': {
                'upcoming': 0,
                'running': 0,
                'completed': 0
            },
            'failed_files': []
        }
        
        # Find all raw JSON files
        raw_files = list(self.raw_dir.rglob('*.json'))
        stats['total'] = len(raw_files)
        
        # Collect all cleaned projects
        cleaned_projects = []
        
        self.logger.info(f"Starting cleaning of {len(raw_files)} raw files")
        print(f"\n{'='*60}")
        print(f"CLEANING {len(raw_files)} PROJECT FILES")
        print(f"{'='*60}\n")
        
        # Process each file
        for i, raw_file in enumerate(raw_files, 1):
            print(f"[{i}/{len(raw_files)}] Cleaning: {raw_file.name}")
            self.logger.info(f"Processing {i}/{len(raw_files)}: {raw_file}")
            
            # Load raw data
            raw_data = self.load_raw_file(raw_file)
            
            if not raw_data:
                stats['failed'] += 1
                stats['failed_files'].append(str(raw_file))
                print(f"  ✗ Failed to load: {raw_file.name}")
                continue
            
            # Clean the data
            cleaned_data = self.cleaner.clean(raw_data)
            
            if not cleaned_data:
                stats['failed'] += 1
                stats['failed_files'].append(str(raw_file))
                print(f"  ✗ Failed to clean: {raw_file.name}")
                continue
            
            # Add to collection
            cleaned_projects.append(cleaned_data)
            stats['successful'] += 1
            
            category = cleaned_data.get('category', 'unknown')
            if category in stats['by_category']:
                stats['by_category'][category] += 1
            
            print(f"  ✓ Success: {cleaned_data['project_name']} ({category})")
            
            # Progress update
            if i % 5 == 0 or i == len(raw_files):
                print(f"\nProgress: {i}/{len(raw_files)} processed")
                print(f"Success: {stats['successful']}, Failed: {stats['failed']}\n")
        
        # Save all cleaned projects to single file
        if cleaned_projects:
            if self.save_cleaned_data(cleaned_projects):
                print(f"\n✓ Saved {len(cleaned_projects)} projects to {self.cleaned_file}")
            else:
                print(f"\n✗ Failed to save projects to {self.cleaned_file}")
        
        # Print summary
        self._print_summary(stats)
        
        return stats
    
    def _print_summary(self, stats: Dict[str, Any]):
        """Print cleaning summary."""
        print(f"\n{'='*60}")
        print(f"CLEANING COMPLETED")
        print(f"{'='*60}")
        print(f"Total Files: {stats['total']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"\nBy Category:")
        for category, count in stats['by_category'].items():
            print(f"  {category.capitalize()}: {count}")
        
        if stats['failed_files']:
            print(f"\nFailed Files:")
            for file in stats['failed_files']:
                print(f"  - {file}")
        
        print(f"\nCleaned data saved to: {self.cleaned_file}")
        print(f"{'='*60}\n")
        
        if stats['failed'] == 0:
            print("All projects cleaned successfully!")
        else:
            print(f"Partially successful: {stats['failed']} files failed")


def main():
    """Main entry point for cleaning script."""
    config = get_config()
    logger = config.get_logger()
    
    try:
        logger.info("="*60)
        logger.info("STARTING PROJECT DATA CLEANING")
        logger.info("="*60)
        
        # Run cleaning
        runner = CleaningRunner()
        stats = runner.clean_all()
        
        logger.info("="*60)
        logger.info("CLEANING PROCESS COMPLETED")
        logger.info(f"Success: {stats['successful']}/{stats['total']}")
        logger.info("="*60)
        
        return 0 if stats['failed'] == 0 else 1
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        print(f"\nFatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
