"""
Query Processor for PropIntel

This module provides query preprocessing, optimization, and expansion
to improve retrieval quality. Includes query cleaning, expansion,
and reformulation strategies.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set


class QueryProcessor:
    """
    Process and optimize queries for better retrieval.
    
    Features:
    - Query cleaning and normalization
    - Query expansion with synonyms
    - Multi-query generation
    - Entity extraction
    - Query type detection
    """
    
    # Real estate domain-specific synonyms
    SYNONYMS = {
        'apartment': ['flat', 'condo', 'unit', 'residential unit'],
        'building': ['complex', 'tower', 'structure'],
        'commercial': ['office', 'business', 'corporate'],
        'residential': ['housing', 'living', 'home'],
        'location': ['area', 'region', 'place', 'locality'],
        'contact': ['phone', 'email', 'reach', 'connect'],
        'service': ['offering', 'facility', 'amenity'],
        'project': ['development', 'scheme', 'property'],
        'price': ['cost', 'rate', 'pricing', 'charges'],
        'amenity': ['facility', 'feature', 'service'],
    }
    
    # Common real estate query patterns
    QUERY_PATTERNS = {
        'specialization': r'(what|which).*(specializ|specialis|service|offer|do|build)',
        'location': r'(where|which area|which location|service area)',
        'contact': r'(contact|phone|email|reach|call|connect)',
        'about': r'(about|tell me|information|who|what is)',
        'timing': r'(timing|hours|when|schedule|open)',
        'social': r'(social|facebook|twitter|linkedin|instagram|youtube)',
        'price': r'(price|cost|rate|how much|pricing)',
        'project': r'(project|development|property|scheme)',
    }
    
    def __init__(self):
        """Initialize the query processor"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("QueryProcessor initialized")
    
    def process(
        self,
        query: str,
        expand: bool = True,
        clean: bool = True
    ) -> Dict[str, Any]:
        """
        Process a query and return processed versions.
        
        Args:
            query: Original query text
            expand: Whether to generate expanded queries
            clean: Whether to clean the query
            
        Returns:
            Dictionary with processed query variants
        """
        self.logger.info(f"Processing query: '{query}'")
        
        result = {
            'original': query,
            'cleaned': query,
            'query_type': None,
            'entities': [],
            'expanded_queries': [],
            'filters': {}
        }
        
        # Clean query
        if clean:
            result['cleaned'] = self.clean_query(query)
        
        # Detect query type
        result['query_type'] = self.detect_query_type(query)
        
        # Extract entities (company names, locations, etc.)
        result['entities'] = self.extract_entities(query)
        
        # Generate expanded queries
        if expand:
            result['expanded_queries'] = self.expand_query(result['cleaned'])
        
        # Generate suggested filters
        result['filters'] = self.suggest_filters(query, result['query_type'])
        
        self.logger.info(f"Query processed: type={result['query_type']}, "
                        f"expansions={len(result['expanded_queries'])}")
        
        return result
    
    def clean_query(self, query: str) -> str:
        """
        Clean and normalize query text.
        
        Args:
            query: Raw query text
            
        Returns:
            Cleaned query text
        """
        # Convert to lowercase
        cleaned = query.lower().strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove special characters (keep alphanumeric and basic punctuation)
        cleaned = re.sub(r'[^a-z0-9\s\.\,\?\-]', '', cleaned)
        
        # Remove trailing question mark (optional, for embedding)
        # cleaned = cleaned.rstrip('?')
        
        return cleaned.strip()
    
    def expand_query(self, query: str, max_expansions: int = 3) -> List[str]:
        """
        Generate expanded query variations using synonyms.
        
        Args:
            query: Query text
            max_expansions: Maximum number of expansions to generate
            
        Returns:
            List of expanded queries
        """
        expansions = []
        query_lower = query.lower()
        
        # Find matching synonyms in query
        for term, synonyms in self.SYNONYMS.items():
            if term in query_lower:
                # Generate expansions with synonyms
                for synonym in synonyms[:max_expansions]:
                    expanded = query_lower.replace(term, synonym)
                    if expanded != query_lower and expanded not in expansions:
                        expansions.append(expanded)
        
        # Limit total expansions
        return expansions[:max_expansions]
    
    def detect_query_type(self, query: str) -> Optional[str]:
        """
        Detect the type of query based on patterns.
        
        Args:
            query: Query text
            
        Returns:
            Query type string or None
        """
        query_lower = query.lower()
        
        for query_type, pattern in self.QUERY_PATTERNS.items():
            if re.search(pattern, query_lower):
                return query_type
        
        return 'general'
    
    def extract_entities(self, query: str) -> List[Dict[str, str]]:
        """
        Extract entities from query (company names, locations, etc.).
        
        Args:
            query: Query text
            
        Returns:
            List of extracted entities with types
        """
        entities = []
        
        # Simple entity extraction (can be enhanced with NER)
        # Extract capitalized words as potential company names
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        
        for word in capitalized_words:
            entities.append({
                'text': word,
                'type': 'company_name'
            })
        
        # Extract locations (Indian cities - expandable)
        indian_cities = [
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Kolkata',
            'Chennai', 'Pune', 'Ahmedabad', 'Jaipur', 'Surat',
            'Asansol', 'Bandel', 'Hooghly', 'Durgapur'
        ]
        
        for city in indian_cities:
            if city.lower() in query.lower():
                entities.append({
                    'text': city,
                    'type': 'location'
                })
        
        return entities
    
    def suggest_filters(
        self,
        query: str,
        query_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest metadata filters based on query analysis.
        
        Args:
            query: Query text
            query_type: Detected query type
            
        Returns:
            Dictionary of suggested filters
        """
        filters = {}
        
        # Section-based filters
        if query_type == 'contact':
            filters['section'] = 'contact_details'
        elif query_type == 'social':
            filters['section'] = 'social_media'
        elif query_type in ['specialization', 'location', 'about']:
            filters['section'] = 'company_info'
        
        return filters
    
    def generate_multi_queries(
        self,
        query: str,
        num_queries: int = 3
    ) -> List[str]:
        """
        Generate multiple query variations for multi-query retrieval.
        
        Args:
            query: Original query
            num_queries: Number of variations to generate
            
        Returns:
            List of query variations
        """
        queries = [query]  # Include original
        
        # Add cleaned version
        cleaned = self.clean_query(query)
        if cleaned != query:
            queries.append(cleaned)
        
        # Add expanded versions
        expanded = self.expand_query(cleaned, max_expansions=num_queries - len(queries))
        queries.extend(expanded)
        
        # Add reformulated versions based on query type
        query_type = self.detect_query_type(query)
        reformulated = self._reformulate_by_type(query, query_type)
        if reformulated and reformulated not in queries:
            queries.append(reformulated)
        
        return queries[:num_queries]
    
    def _reformulate_by_type(
        self,
        query: str,
        query_type: Optional[str]
    ) -> Optional[str]:
        """
        Reformulate query based on its type.
        
        Args:
            query: Original query
            query_type: Detected query type
            
        Returns:
            Reformulated query or None
        """
        if not query_type or query_type == 'general':
            return None
        
        # Extract the main subject from query
        # Simple extraction - can be improved
        query_lower = query.lower()
        
        if query_type == 'specialization':
            # Reformulate to focus on services
            if 'company' in query_lower or 'astha' in query_lower:
                company = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
                if company:
                    return f"services and specializations offered"
            return "property development services and specializations"
        
        elif query_type == 'contact':
            return "contact information phone email address"
        
        elif query_type == 'location':
            return "service areas operational locations regions"
        
        elif query_type == 'about':
            return "company overview description background"
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query processor statistics"""
        return {
            'num_synonyms': len(self.SYNONYMS),
            'num_patterns': len(self.QUERY_PATTERNS),
            'supported_types': list(self.QUERY_PATTERNS.keys())
        }
