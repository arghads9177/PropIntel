"""
Collection Router for intelligent routing between company and project collections.

This module provides functionality to automatically detect which ChromaDB collection
should be queried based on the user's query content and intent.
"""

import json
import re
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class CollectionRouter:
    """Routes queries to appropriate ChromaDB collections based on query analysis."""
    
    # Collection names
    COMPANY_COLLECTION = "propintel_companies"
    PROJECT_COLLECTION = "propintel_knowledge"
    PROJECTS_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "cleaned" / "projects.json"
    
    # Keywords that indicate project-related queries
    PROJECT_KEYWORDS = [
        'project', 'tower', 'floor', 'storey', 'upcoming', 'running', 
        'completed', 'development', 'construction', 'building', 'block',
        'wing', 'residential', 'commercial', 'property', 'flat', 'apartment'
    ]
    
    # Keywords that indicate company-related queries
    COMPANY_KEYWORDS = [
        'company', 'contact', 'email', 'phone', 'call', 'reach',
        'specialize', 'specialization', 'about the company', 'firm',
        'office', 'address', 'social media', 'facebook', 'linkedin',
        'instagram', 'website', 'timing', 'hours', 'schedule'
    ]
    
    # Project name patterns (for direct project mentions)
    PROJECT_NAME_PATTERNS = [
        r'kabi\s+tirtha',
        r'urban\s+residency',
        r'orbit\s+heights',
        r'green\s+valley',
        r'royal\s+enclave',
        r'skyline\s+towers',
        r'metro\s+homes',
        r'paradise\s+view',
        r'crystal\s+palace',
        r'golden\s+crest',
        r'silver\s+oak',
        r'emerald\s+plaza',
        r'sapphire\s+residency'
    ]
    
    # Company name patterns
    COMPANY_NAME_PATTERNS = [
        r'orbit\s+infra',
        r'green\s+builders',
        r'royal\s+developers',
        r'skyline\s+constructions',
        r'metro\s+properties'
    ]
    
    def __init__(self):
        """Initialize the collection router."""
        self.project_regex = re.compile('|'.join(self.PROJECT_KEYWORDS), re.IGNORECASE)
        self.company_regex = re.compile('|'.join(self.COMPANY_KEYWORDS), re.IGNORECASE)
        dynamic_patterns = self._load_project_name_patterns()
        project_patterns = self.PROJECT_NAME_PATTERNS + dynamic_patterns
        self.project_name_regex = re.compile('|'.join(project_patterns), re.IGNORECASE)
        self.company_name_regex = re.compile('|'.join(self.COMPANY_NAME_PATTERNS), re.IGNORECASE)
        if dynamic_patterns:
            logger.info("Loaded %d dynamic project names for routing", len(dynamic_patterns))
    
    def route(self, query: str) -> str:
        """
        Determine which collection to query based on the input query.
        
        Args:
            query: User's search query
            
        Returns:
            Collection name to query (either COMPANY_COLLECTION or PROJECT_COLLECTION)
        """
        query_lower = query.lower()
        
        # Check for explicit project name mentions
        if self.project_name_regex.search(query_lower):
            logger.info(f"Routing to PROJECT collection (project name detected)")
            return self.PROJECT_COLLECTION
        
        # Check for explicit company name mentions
        if self.company_name_regex.search(query_lower):
            logger.info(f"Routing to COMPANY collection (company name detected)")
            return self.COMPANY_COLLECTION
        
        # Count keyword matches
        project_matches = len(self.project_regex.findall(query_lower))
        company_matches = len(self.company_regex.findall(query_lower))
        
        # Route based on keyword count
        if project_matches > company_matches:
            logger.info(f"Routing to PROJECT collection (project keywords: {project_matches} vs company: {company_matches})")
            return self.PROJECT_COLLECTION
        elif company_matches > project_matches:
            logger.info(f"Routing to COMPANY collection (company keywords: {company_matches} vs project: {project_matches})")
            return self.COMPANY_COLLECTION
        
        # Default to company collection for ambiguous queries
        logger.info(f"Routing to COMPANY collection (default/ambiguous)")
        return self.COMPANY_COLLECTION
    
    def route_with_confidence(self, query: str) -> Dict[str, any]:
        """
        Route query and return confidence score.
        
        Args:
            query: User's search query
            
        Returns:
            Dictionary with collection name and confidence score (0-1)
        """
        query_lower = query.lower()
        
        # Initialize scores
        project_score = 0.0
        company_score = 0.0
        
        # Check for explicit mentions (high confidence)
        if self.project_name_regex.search(query_lower):
            project_score += 0.8
        if self.company_name_regex.search(query_lower):
            company_score += 0.8
        
        # Count keyword matches
        project_matches = len(self.project_regex.findall(query_lower))
        company_matches = len(self.company_regex.findall(query_lower))
        
        # Add keyword scores (normalized)
        project_score += min(project_matches * 0.2, 0.6)
        company_score += min(company_matches * 0.2, 0.6)
        
        # Determine collection and confidence
        if project_score > company_score:
            collection = self.PROJECT_COLLECTION
            confidence = min(project_score, 1.0)
        elif company_score > project_score:
            collection = self.COMPANY_COLLECTION
            confidence = min(company_score, 1.0)
        else:
            # Default to company with low confidence
            collection = self.COMPANY_COLLECTION
            confidence = 0.3
        
        logger.info(f"Routing to {collection} with confidence {confidence:.2f}")
        
        return {
            'collection': collection,
            'confidence': confidence,
            'project_score': project_score,
            'company_score': company_score
        }
    
    def should_query_both(self, query: str, threshold: float = 0.5) -> bool:
        """
        Determine if query should be executed against both collections.
        
        Args:
            query: User's search query
            threshold: Confidence threshold below which both collections should be queried
            
        Returns:
            True if both collections should be queried
        """
        result = self.route_with_confidence(query)
        
        # Query both if confidence is low or scores are close
        if result['confidence'] < threshold:
            return True
        
        score_diff = abs(result['project_score'] - result['company_score'])
        if score_diff < 0.3:
            return True
        
        return False
    
    def get_collections_to_query(self, query: str, multi_collection: bool = False) -> List[str]:
        """
        Get list of collections to query.
        
        Args:
            query: User's search query
            multi_collection: If True, may return multiple collections
            
        Returns:
            List of collection names to query
        """
        if multi_collection and self.should_query_both(query):
            logger.info("Querying both collections (low confidence/ambiguous)")
            return [self.COMPANY_COLLECTION, self.PROJECT_COLLECTION]
        
        primary_collection = self.route(query)
        return [primary_collection]
    
    def extract_project_name(self, query: str) -> Optional[str]:
        """
        Extract project name from query if present.
        
        Args:
            query: User's search query
            
        Returns:
            Project name if found, None otherwise
        """
        match = self.project_name_regex.search(query.lower())
        if match:
            # Capitalize each word
            project_name = ' '.join(word.capitalize() for word in match.group().split())
            return project_name
        return None

    def _load_project_name_patterns(self) -> List[str]:
        """Load project name patterns from the cleaned projects dataset."""
        patterns: List[str] = []
        try:
            with open(self.PROJECTS_DATA_PATH, 'r', encoding='utf-8') as f:
                projects = json.load(f)
            for project in projects:
                name = project.get('project_name')
                if not name:
                    continue
                escaped = re.escape(name.strip().lower())
                if escaped:
                    patterns.append(escaped)
        except FileNotFoundError:
            logger.warning("Projects data file not found at %s", self.PROJECTS_DATA_PATH)
        except json.JSONDecodeError:
            logger.warning("Projects data file is not valid JSON at %s", self.PROJECTS_DATA_PATH)
        except Exception as exc:
            logger.warning("Failed to load project names: %s", exc)
        return patterns
    
    def extract_company_name(self, query: str) -> Optional[str]:
        """
        Extract company name from query if present.
        
        Args:
            query: User's search query
            
        Returns:
            Company name if found, None otherwise
        """
        match = self.company_name_regex.search(query.lower())
        if match:
            # Capitalize each word
            company_name = ' '.join(word.capitalize() for word in match.group().split())
            return company_name
        return None


# Singleton instance for easy access
_router_instance = None

def get_router() -> CollectionRouter:
    """Get or create the singleton router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = CollectionRouter()
    return _router_instance
