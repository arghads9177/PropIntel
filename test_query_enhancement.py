"""
Test script for enhanced query processing functionality.

Tests:
1. Project-specific query type detection
2. Project entity extraction
3. Project filter suggestions
4. Query expansion with project synonyms
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from retrieval.query_processor import QueryProcessor


def test_query_type_detection():
    """Test detection of project-specific query types"""
    print("=" * 80)
    print("TEST 1: Query Type Detection")
    print("=" * 80)
    
    processor = QueryProcessor()
    
    test_queries = [
        ("Tell me about Kabi Tirtha project", "project_info"),
        ("How many floors in Urban Residency?", "floors"),
        ("What towers are in the project?", "towers"),
        ("List all upcoming projects", "project_status"),
        ("Which projects are running?", "project_status"),
        ("Tower 1 details", "tower_info"),
        ("Show me completed developments", "project_status"),
        ("What is the height of the building?", "floors"),
        ("Contact details for Astha", "contact"),
        ("Company specializations", "specialization"),
    ]
    
    for query, expected_type in test_queries:
        detected_type = processor.detect_query_type(query)
        match = "✓" if expected_type in detected_type or detected_type in expected_type else "✗"
        print(f"\n{match} Query: {query}")
        print(f"  Expected: {expected_type}")
        print(f"  Detected: {detected_type}")


def test_entity_extraction():
    """Test extraction of project-specific entities"""
    print("\n\n" + "=" * 80)
    print("TEST 2: Entity Extraction")
    print("=" * 80)
    
    processor = QueryProcessor()
    
    test_queries = [
        "Tell me about Kabi Tirtha project",
        "How many floors in Tower 1?",
        "What upcoming projects in Kolkata?",
        "Show running projects in Bandel",
        "Details of Tower 2 in Urban Residency",
        "List completed developments",
    ]
    
    for query in test_queries:
        entities = processor.extract_entities(query)
        print(f"\nQuery: {query}")
        if entities:
            for entity in entities:
                print(f"  → {entity['type']:15s}: {entity['text']}")
        else:
            print("  → No entities detected")


def test_filter_suggestions():
    """Test filter suggestions for project queries"""
    print("\n\n" + "=" * 80)
    print("TEST 3: Filter Suggestions")
    print("=" * 80)
    
    processor = QueryProcessor()
    
    test_queries = [
        "What upcoming projects are there?",
        "Show me running developments",
        "List completed projects",
        "How many floors in Tower 1?",
        "Tell me about Tower 2",
        "Which projects are in Kolkata?",
        "Contact details for company",
    ]
    
    for query in test_queries:
        result = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Type: {result['query_type']}")
        if result['filters']:
            print(f"  Filters:")
            for key, value in result['filters'].items():
                print(f"    {key}: {value}")
        else:
            print(f"  Filters: None")


def test_query_expansion():
    """Test query expansion with project synonyms"""
    print("\n\n" + "=" * 80)
    print("TEST 4: Query Expansion")
    print("=" * 80)
    
    processor = QueryProcessor()
    
    test_queries = [
        "What upcoming projects?",
        "Show me completed apartments",
        "How many floors in the tower?",
        "List running developments",
    ]
    
    for query in test_queries:
        result = processor.process(query, expand=True)
        print(f"\nQuery: {query}")
        if result['expanded_queries']:
            print(f"  Expansions:")
            for i, exp in enumerate(result['expanded_queries'], 1):
                print(f"    {i}. {exp}")
        else:
            print(f"  Expansions: None")


def test_full_processing():
    """Test complete query processing pipeline"""
    print("\n\n" + "=" * 80)
    print("TEST 5: Full Query Processing")
    print("=" * 80)
    
    processor = QueryProcessor()
    
    test_queries = [
        "Tell me about Kabi Tirtha project",
        "What upcoming projects in Kolkata?",
        "How many floors in Tower 1 of Urban Residency?",
    ]
    
    for query in test_queries:
        print(f"\n{'─' * 80}")
        print(f"Query: {query}")
        print(f"{'─' * 80}")
        
        result = processor.process(query)
        
        print(f"Original:  {result['original']}")
        print(f"Cleaned:   {result['cleaned']}")
        print(f"Type:      {result['query_type']}")
        
        if result['entities']:
            print(f"Entities:")
            for entity in result['entities']:
                print(f"  - {entity['type']:15s}: {entity['text']}")
        
        if result['filters']:
            print(f"Filters:")
            for key, value in result['filters'].items():
                print(f"  - {key}: {value}")
        
        if result['expanded_queries']:
            print(f"Expansions:")
            for i, exp in enumerate(result['expanded_queries'], 1):
                print(f"  {i}. {exp}")


def test_tower_extraction():
    """Test tower ID extraction"""
    print("\n\n" + "=" * 80)
    print("TEST 6: Tower ID Extraction")
    print("=" * 80)
    
    processor = QueryProcessor()
    
    test_queries = [
        "How many floors in Tower 1?",
        "Details of Tower 2",
        "Tower one information",
        "Show me block A",
        "What about tower_3?",
    ]
    
    for query in test_queries:
        result = processor.process(query)
        tower_id = result['filters'].get('tower_id')
        print(f"\nQuery: {query}")
        if tower_id:
            print(f"  ✓ Tower ID: {tower_id}")
        else:
            print(f"  ✗ No tower ID extracted")


def test_category_extraction():
    """Test project category extraction"""
    print("\n\n" + "=" * 80)
    print("TEST 7: Project Category Extraction")
    print("=" * 80)
    
    processor = QueryProcessor()
    
    test_queries = [
        ("What upcoming projects?", "upcoming"),
        ("Show running developments", "running"),
        ("List completed projects", "completed"),
        ("Projects under construction", "running"),
        ("Future planned properties", "upcoming"),
        ("Finished apartments", "completed"),
    ]
    
    for query, expected_category in test_queries:
        result = processor.process(query)
        category = result['filters'].get('category')
        match = "✓" if category == expected_category else "✗"
        print(f"\n{match} Query: {query}")
        print(f"  Expected: {expected_category}")
        print(f"  Extracted: {category or 'None'}")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "QUERY ENHANCEMENT TEST SUITE" + " " * 30 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    try:
        test_query_type_detection()
        test_entity_extraction()
        test_filter_suggestions()
        test_query_expansion()
        test_full_processing()
        test_tower_extraction()
        test_category_extraction()
        
        print("\n\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)
        print()
    
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
