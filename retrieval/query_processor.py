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
        # Project-specific synonyms
        'upcoming': ['future', 'planned', 'new', 'forthcoming'],
        'running': ['ongoing', 'current', 'in progress', 'active', 'under construction'],
        'completed': ['finished', 'done', 'delivered', 'ready', 'handover'],
        'tower': ['block', 'building', 'wing'],
        'floor': ['storey', 'level', 'story'],
        'developer': ['builder', 'constructor', 'company'],
    }
    
    # Common real estate query patterns
    QUERY_PATTERNS = {
        # Company-related patterns
        'contact': r'(contact|phone|email|reach|call|connect|address|office|branch)',
        'timing': r'(timing|hours|when|schedule|open|close)',
        'social': r'(social|facebook|twitter|linkedin|instagram|youtube)',
        'specialization': r'(what|which).*(specializ|specialis|service|offer|do|build)',
        'location': r'(where|which area|which location|service area|location of)',
        'about': r'(about|tell me|information|who|what is)',
        'price': r'(price|cost|rate|how much|pricing)',
        # Project-specific patterns
        'project_info': r'(project|development|property|scheme)',
        'floors': r'(floor|storey|storied|how tall|height|how many floor|number of floor)',
        'towers': r'(tower|block|building|how many towers|which tower|number of tower)',
        'project_status': r'(upcoming|running|completed|status|ongoing|under construction|finished)',
        'tower_info': r'(tower \w+|block \w+|tower information|details of tower)',
        'project_details': r'(project detail|tell me about.*project|information about.*project|describe)',
        'project_list': r'(list|show|all|what are|which are).*(project|development)',
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
        Priority: More specific patterns first.
        
        Args:
            query: Query text
            
        Returns:
            Query type string or None
        """
        query_lower = query.lower()
        
        # Check patterns in priority order (most specific first)
        priority_order = [
            'project_status',     # upcoming/running/completed (specific)
            'floors',             # floor-related queries
            'towers',             # tower-related queries
            'tower_info',         # specific tower information
            'project_list',       # list/show projects
            'project_details',    # project detail queries
            'location',           # location/area queries
            'contact',            # contact information
            'timing',             # business hours
            'social',             # social media
            'specialization',     # company specialization
            'price',              # pricing queries
            'project_info',       # general project queries
            'about',              # general about queries
        ]
        
        for query_type in priority_order:
            if query_type in self.QUERY_PATTERNS:
                pattern = self.QUERY_PATTERNS[query_type]
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
        # Extract capitalized words as potential company/project names
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        
        for word in capitalized_words:
            entities.append({
                'text': word,
                'type': 'proper_name'  # Could be company or project
            })
        
        # Extract locations (Indian cities - expandable)
        indian_cities = [
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Kolkata',
            'Chennai', 'Pune', 'Ahmedabad', 'Jaipur', 'Surat',
            'Asansol', 'Bandel', 'Hooghly', 'Durgapur', 'Lathbagan',
            'Kailash Nagar', 'Madhyamgram', 'New Town', 'Rajarhat'
        ]
        
        for city in indian_cities:
            if city.lower() in query.lower():
                entities.append({
                    'text': city,
                    'type': 'location'
                })
        
        # Extract project status
        if re.search(r'\bupcoming\b', query, re.IGNORECASE):
            entities.append({'text': 'upcoming', 'type': 'project_status'})
        if re.search(r'\brunning\b|\bongoing\b|\bunder construction\b', query, re.IGNORECASE):
            entities.append({'text': 'running', 'type': 'project_status'})
        if re.search(r'\bcompleted\b|\bfinished\b|\bready\b', query, re.IGNORECASE):
            entities.append({'text': 'completed', 'type': 'project_status'})
        
        # Extract tower identifiers
        tower_match = re.search(r'tower\s+(\d+|[a-z])', query, re.IGNORECASE)
        if tower_match:
            entities.append({
                'text': f'tower_{tower_match.group(1).lower()}',
                'type': 'tower_id'
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
        
        # Company-related filters (section-based)
        if query_type in ['contact', 'timing']:
            filters['section'] = 'contact_details'
        elif query_type == 'social':
            filters['section'] = 'social_media'
        elif query_type == 'specialization':
            filters['section'] = 'company_info'
        
        # Project-related filters
        if query_type in ['project_status', 'project_list', 'project_details', 'project_info']:
            # Extract project status from query
            category = self._extract_project_category(query)
            if category:
                filters['category'] = category
        
        if query_type in ['towers', 'tower_info']:
            # Filter for tower chunks
            filters['chunk_type'] = 'tower'
            # Try to extract specific tower ID
            tower_id = self._extract_tower_id(query)
            if tower_id:
                filters['tower_id'] = tower_id
        
        if query_type == 'floors':
            # Floor queries usually relate to towers
            filters['chunk_type'] = 'tower'
            # Try to extract tower ID for specific tower
            tower_id = self._extract_tower_id(query)
            if tower_id:
                filters['tower_id'] = tower_id
        
        if query_type == 'location':
            # Could be company service area or project location
            # Check if query mentions project keywords
            if re.search(r'\bproject\b|\bdevelopment\b|\bproperty\b', query, re.IGNORECASE):
                filters['chunk_type'] = 'location'
        
        return filters
    
    def _extract_project_category(self, query: str) -> Optional[str]:
        """
        Extract project category/status from query.
        
        Args:
            query: Query text
            
        Returns:
            Category string ('upcoming', 'running', 'completed') or None
        """
        query_lower = query.lower()
        
        if re.search(r'\bupcoming\b|\bfuture\b|\bplanned\b|\bnew\b|\bforthcoming\b', query_lower):
            return 'upcoming'
        elif re.search(r'\brunning\b|\bongoing\b|\bcurrent\b|\bactive\b|\bunder construction\b|\bin progress\b', query_lower):
            return 'running'
        elif re.search(r'\bcompleted\b|\bfinished\b|\bready\b|\bdelivered\b|\bhandover\b|\bdone\b', query_lower):
            return 'completed'
        
        return None
    
    def _extract_tower_id(self, query: str) -> Optional[str]:
        """
        Extract tower ID from query.
        
        Args:
            query: Query text
            
        Returns:
            Tower ID string or None
        """
        # Match patterns like "Tower 1", "Block A", "tower_1"
        match = re.search(r'tower\s+(\d+|[a-z]|one|two|three|four)', query, re.IGNORECASE)
        if match:
            tower_num = match.group(1).lower()
            # Convert word numbers to digits
            word_to_num = {'one': '1', 'two': '2', 'three': '3', 'four': '4'}
            tower_num = word_to_num.get(tower_num, tower_num)
            return f'tower_{tower_num}'
        
        return None
    
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
