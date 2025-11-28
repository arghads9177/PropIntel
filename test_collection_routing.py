"""
Test script for collection routing functionality.

Tests:
1. Collection router keyword detection
2. Project name extraction
3. Retriever collection switching
4. End-to-end project query
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from retrieval.collection_router import get_router
from retrieval.retriever import RetrieverService
from ingestion.vector_db.chromadb_manager import ChromaDBManager


def test_collection_router():
    """Test collection router functionality"""
    print("=" * 80)
    print("TEST 1: Collection Router")
    print("=" * 80)
    
    router = get_router()
    
    test_queries = [
        "Tell me about Kabi Tirtha project",
        "How many floors in Urban Residency?",
        "What upcoming projects are there?",
        "What does Astha company specialize in?",
        "How can I contact Orbit Infra?",
        "Show me Tower 1 details",
        "Which projects are running?",
        "Tell me about company specializations"
    ]
    
    for query in test_queries:
        result = router.route_with_confidence(query)
        collection_type = "PROJECT" if "knowledge" in result['collection'] else "COMPANY"
        print(f"\nQuery: {query}")
        print(f"  → {collection_type} (confidence: {result['confidence']:.0%})")
        print(f"     Scores - Project: {result['project_score']:.2f}, Company: {result['company_score']:.2f}")


def test_entity_extraction():
    """Test entity extraction"""
    print("\n\n" + "=" * 80)
    print("TEST 2: Entity Extraction")
    print("=" * 80)
    
    router = get_router()
    
    test_queries = [
        "Tell me about Kabi Tirtha project",
        "What does Orbit Infra specialize in?",
        "How many floors in Urban Residency?",
        "Contact details for Astha"
    ]
    
    for query in test_queries:
        project_name = router.extract_project_name(query)
        company_name = router.extract_company_name(query)
        print(f"\nQuery: {query}")
        if project_name:
            print(f"  → Project: {project_name}")
        if company_name:
            print(f"  → Company: {company_name}")
        if not project_name and not company_name:
            print(f"  → No entities detected")


def test_collection_switching():
    """Test ChromaDB collection switching"""
    print("\n\n" + "=" * 80)
    print("TEST 3: Collection Switching")
    print("=" * 80)
    
    try:
        # Initialize with default collection
        db = ChromaDBManager(persist_directory='./data/chromadb')
        print(f"\nInitial collection: {db.collection_name}")
        print(f"  Document count: {db.collection.count()}")
        
        # List available collections
        collections = db.get_available_collections()
        print(f"\nAvailable collections: {collections}")
        
        # Get info for each collection
        for col_name in collections:
            info = db.get_collection_info(col_name)
            print(f"\n  {col_name}:")
            print(f"    Count: {info['count']}")
            print(f"    Has docs: {info['has_documents']}")
        
        # Test switching
        if 'propintel_knowledge' in collections:
            print(f"\nSwitching to propintel_knowledge...")
            db.switch_collection('propintel_knowledge')
            print(f"  Current collection: {db.collection_name}")
            print(f"  Document count: {db.collection.count()}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_retriever_with_collection():
    """Test retriever with collection parameter"""
    print("\n\n" + "=" * 80)
    print("TEST 4: Retriever with Collection Routing")
    print("=" * 80)
    
    try:
        # Initialize retriever
        retriever = RetrieverService(persist_directory='./data/chromadb')
        
        # Test queries
        test_cases = [
            ("Tell me about Kabi Tirtha project", "propintel_knowledge"),
            ("What does Astha specialize in?", "propintel_companies"),
        ]
        
        for query, collection in test_cases:
            print(f"\nQuery: {query}")
            print(f"Target collection: {collection}")
            
            # Retrieve with specific collection
            results = retriever.retrieve_from_collection(
                query=query,
                collection_name=collection,
                n_results=3
            )
            
            print(f"  Results found: {len(results)}")
            if results:
                print(f"  Top result score: {results[0].score:.3f}")
                print(f"  Content preview: {results[0].content[:100]}...")
                print(f"  Metadata: {results[0].metadata}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_multi_collection_retrieval():
    """Test retrieving from multiple collections"""
    print("\n\n" + "=" * 80)
    print("TEST 5: Multi-Collection Retrieval")
    print("=" * 80)
    
    try:
        retriever = RetrieverService(persist_directory='./data/chromadb')
        
        query = "What projects and companies are in Kolkata?"
        collections = ['propintel_companies', 'propintel_knowledge']
        
        print(f"\nQuery: {query}")
        print(f"Searching in: {collections}")
        
        results = retriever.retrieve_multi_collection(
            query=query,
            collection_names=collections,
            n_results_per_collection=3
        )
        
        for col_name, col_results in results.items():
            col_type = "Project" if "knowledge" in col_name else "Company"
            print(f"\n{col_type} Results ({col_name}):")
            print(f"  Found: {len(col_results)} documents")
            for i, result in enumerate(col_results[:2], 1):
                print(f"  [{i}] Score: {result.score:.3f}")
                print(f"      Preview: {result.content[:80]}...")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "COLLECTION ROUTING TEST SUITE" + " " * 29 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    try:
        test_collection_router()
        test_entity_extraction()
        test_collection_switching()
        test_retriever_with_collection()
        test_multi_collection_retrieval()
        
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
