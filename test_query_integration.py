"""
Integration test for query enhancement with retrieval.

Tests query processing with actual retrieval to verify filters work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from retrieval.query_processor import QueryProcessor
from retrieval.retriever import RetrieverService


def test_project_query_with_filters():
    """Test project queries with metadata filters"""
    print("=" * 80)
    print("Integration Test: Query Enhancement + Retrieval")
    print("=" * 80)
    
    processor = QueryProcessor()
    retriever = RetrieverService(persist_directory='./data/chromadb')
    
    test_queries = [
        "What upcoming projects are there?",
        "Show me running developments",
        "How many floors in Tower 1?",
        "List completed projects",
        "Tell me about Kabi Tirtha project",
    ]
    
    for query in test_queries:
        print(f"\n{'─' * 80}")
        print(f"Query: {query}")
        print(f"{'─' * 80}")
        
        # Process query
        result = processor.process(query)
        
        print(f"Query Type: {result['query_type']}")
        print(f"Filters: {result['filters']}")
        
        # Retrieve with filters
        results = retriever.retrieve_from_collection(
            query=query,
            collection_name='propintel_knowledge',
            n_results=3,
            filters=result['filters'] if result['filters'] else None
        )
        
        print(f"\nResults: {len(results)} found")
        if results:
            for i, res in enumerate(results, 1):
                print(f"\n  [{i}] Score: {res.score:.3f}")
                print(f"      Preview: {res.content[:100]}...")
                print(f"      Metadata: {res.metadata}")


def main():
    """Run integration test"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "QUERY ENHANCEMENT INTEGRATION TEST" + " " * 29 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    try:
        test_project_query_with_filters()
        
        print("\n\n" + "=" * 80)
        print("✅ INTEGRATION TEST COMPLETED")
        print("=" * 80)
        print()
    
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
