"""
Project Data Cleaner

Cleans and standardizes raw project data:
- Validates required fields
- Standardizes text formatting
- Handles missing values
- Ensures data consistency
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from ingestion.config.env_loader import get_config


class ProjectCleaner:
    """Clean and standardize raw project data."""
    
    def __init__(self):
        """Initialize project cleaner."""
        self.config = get_config()
        self.logger = self.config.get_logger()
        self.logger.info("ProjectCleaner initialized")
        
        # Required fields
        self.required_fields = ['project_name', 'location', 'towers', 'developed_by', 'category']
        
        # Valid categories
        self.valid_categories = ['upcoming', 'running', 'completed']
    
    def clean(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean raw project data.
        
        Args:
            raw_data: Raw project data dictionary
            
        Returns:
            Cleaned project data or None if validation fails
        """
        try:
            # Validate required fields
            if not self._validate_required_fields(raw_data):
                return None
            
            # Create cleaned data structure
            cleaned_data = {
                'project_name': self._clean_project_name(raw_data.get('project_name', '')),
                'location': self._clean_location(raw_data.get('location', '')),
                'towers': self._clean_towers(raw_data.get('towers', {})),
                'developed_by': self._clean_developer(raw_data.get('developed_by', '')),
                'category': self._clean_category(raw_data.get('category', '')),
                'metadata': {
                    'cleaned_at': datetime.now().isoformat(),
                    'source': 'web_scraping'
                }
            }
            
            # Validate cleaned data
            if not self._validate_cleaned_data(cleaned_data):
                return None
            
            return cleaned_data
            
        except Exception as e:
            self.logger.error(f"Error cleaning project data: {e}", exc_info=True)
            return None
    
    def _validate_required_fields(self, data: Dict[str, Any]) -> bool:
        """
        Validate that all required fields are present.
        
        Args:
            data: Raw data dictionary
            
        Returns:
            True if all required fields present, False otherwise
        """
        for field in self.required_fields:
            if field not in data:
                self.logger.warning(f"Missing required field: {field}")
                return False
        return True
    
    def _clean_project_name(self, name: str) -> str:
        """
        Clean and standardize project name.
        
        Args:
            name: Raw project name
            
        Returns:
            Cleaned project name
        """
        if not name:
            return ""
        
        # Strip whitespace
        cleaned = name.strip()
        
        # Standardize capitalization (Title Case)
        cleaned = cleaned.title()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove special characters but keep alphanumeric, spaces, hyphens, and parentheses
        cleaned = re.sub(r'[^\w\s\-\(\)]', '', cleaned)
        
        return cleaned
    
    def _clean_location(self, location: str) -> str:
        """
        Clean and standardize location.
        
        Args:
            location: Raw location string
            
        Returns:
            Cleaned location string
        """
        if not location:
            return ""
        
        # Strip whitespace
        cleaned = location.strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove multiple commas
        cleaned = re.sub(r',+', ',', cleaned)
        
        # Remove leading/trailing commas
        cleaned = cleaned.strip(',').strip()
        
        # Standardize common location abbreviations
        cleaned = re.sub(r'\bPin\s*[:–-]?\s*', 'Pin: ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bPS\s*[:–-]?\s*', 'PS: ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bHolding\s+no\s*[:–-]?\s*', 'Holding No: ', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _clean_towers(self, towers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and validate tower data.
        
        Args:
            towers: Raw towers dictionary
            
        Returns:
            Cleaned towers dictionary
        """
        if not towers or not isinstance(towers, dict):
            return {}
        
        cleaned_towers = {}
        
        for tower_key, tower_data in towers.items():
            # Validate tower key format (flexible matching)
            # Accepts: tower_1, tower1, tower_1_, tower1_, etc.
            if not re.match(r'^tower_?\d+_?$', tower_key, re.IGNORECASE):
                self.logger.warning(f"Invalid tower key format: {tower_key}")
                continue
            
            # Standardize tower key (tower_1, tower_2, etc.)
            # Extract the number and rebuild the key
            number_match = re.search(r'(\d+)', tower_key)
            if number_match:
                tower_number = number_match.group(1)
                standardized_key = f'tower_{tower_number}'
            else:
                self.logger.warning(f"Could not extract tower number from: {tower_key}")
                continue
            
            # Clean tower data
            if isinstance(tower_data, dict):
                cleaned_tower = {
                    'number_of_floors': self._clean_floors(tower_data.get('number_of_floors', ''))
                }
                cleaned_towers[standardized_key] = cleaned_tower
        
        return cleaned_towers
    
    def _clean_floors(self, floors: str) -> str:
        """
        Clean and standardize floor information.
        
        Args:
            floors: Raw floor string (e.g., "G+4", "B+G+4", "5")
            
        Returns:
            Cleaned floor string
        """
        if not floors:
            return ""
        
        # Strip whitespace
        cleaned = floors.strip()
        
        # Standardize to uppercase
        cleaned = cleaned.upper()
        
        # Remove extra spaces
        cleaned = re.sub(r'\s+', '', cleaned)
        
        # Standardize format: B+G+4, G+4, etc.
        # Pattern: optional B+ followed by G+ followed by number
        if re.match(r'^[BG\+\d]+$', cleaned):
            return cleaned
        
        # If it's just a number, return as is
        if cleaned.isdigit():
            return cleaned
        
        # If contains "Coming Soon" or similar
        if 'COMING' in cleaned or 'SOON' in cleaned:
            return "Coming Soon"
        
        return cleaned
    
    def _clean_developer(self, developer: str) -> str:
        """
        Clean and standardize developer name.
        
        Args:
            developer: Raw developer name
            
        Returns:
            Cleaned developer name
        """
        if not developer:
            return ""
        
        # Strip whitespace
        cleaned = developer.strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Standardize company suffixes
        cleaned = re.sub(r'\(Pvt\)\s*Ltd\.?', '(Pvt) Ltd.', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'Pvt\.?\s*Ltd\.?', 'Pvt. Ltd.', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bLtd\.?$', 'Ltd.', cleaned, flags=re.IGNORECASE)
        
        # Capitalize properly
        # Keep abbreviations like "Pvt", "Ltd" in proper case
        words = cleaned.split()
        capitalized_words = []
        for word in words:
            if word.upper() in ['PVT.', 'LTD.', 'PVT', 'LTD']:
                capitalized_words.append(word.capitalize() + ('.' if not word.endswith('.') else ''))
            elif word in ['(Pvt)', '(Pvt.)']:
                capitalized_words.append('(Pvt)')
            else:
                capitalized_words.append(word.title())
        
        cleaned = ' '.join(capitalized_words)
        
        return cleaned
    
    def _clean_category(self, category: str) -> str:
        """
        Clean and validate category.
        
        Args:
            category: Raw category string
            
        Returns:
            Cleaned category string
        """
        if not category:
            return ""
        
        # Lowercase and strip
        cleaned = category.lower().strip()
        
        # Validate against allowed categories
        if cleaned not in self.valid_categories:
            self.logger.warning(f"Invalid category: {category}, defaulting to 'running'")
            return "running"
        
        return cleaned
    
    def _validate_cleaned_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate cleaned data meets quality requirements.
        
        Args:
            data: Cleaned data dictionary
            
        Returns:
            True if data is valid, False otherwise
        """
        # Check project name is not empty
        if not data.get('project_name'):
            self.logger.warning("Project name is empty after cleaning")
            return False
        
        # Check category is valid
        if data.get('category') not in self.valid_categories:
            self.logger.warning(f"Invalid category: {data.get('category')}")
            return False
        
        # Check towers structure
        towers = data.get('towers', {})
        if not towers:
            self.logger.warning("No tower data available")
            # Allow empty towers for upcoming projects
            if data.get('category') != 'upcoming':
                return False
        
        # Validate each tower
        for tower_key, tower_data in towers.items():
            if not isinstance(tower_data, dict):
                self.logger.warning(f"Invalid tower data format for {tower_key}")
                return False
            
            if 'number_of_floors' not in tower_data:
                self.logger.warning(f"Missing number_of_floors for {tower_key}")
                return False
        
        return True


def main():
    """Test the cleaner with sample data."""
    cleaner = ProjectCleaner()
    
    # Test with sample raw data
    sample_raw = {
        "project_name": "test  apartment",
        "location": "Test Location,  West Bengal, Pin - 123456",
        "towers": {
            "tower1_": {
                "number_of_floors": "g+4"
            }
        },
        "developed_by": "Test Construction pvt ltd",
        "category": "running"
    }
    
    cleaned = cleaner.clean(sample_raw)
    print("Raw data:")
    print(json.dumps(sample_raw, indent=2))
    print("\nCleaned data:")
    print(json.dumps(cleaned, indent=2))


if __name__ == "__main__":
    main()
